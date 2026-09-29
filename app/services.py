from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import hash_password, verify_password
from app.models import Operation, OperationStatus, Role, User
from app.repositories import AuditRepository, OperationRepository, UserRepository
from app.schemas import OperationCreate, OperationUpdate, UserCreate


class DomainError(Exception): pass
class NotFoundError(DomainError): pass
class ForbiddenError(DomainError): pass


class AuthService:
    def __init__(self, session: AsyncSession): self.session, self.users = session, UserRepository(session)
    async def register(self, data: UserCreate) -> User:
        if await self.users.get_by_email(str(data.email)):
            raise DomainError("El correo ya está registrado")
        user = await self.users.create(User(**data.model_dump(exclude={"password"}), password_hash=hash_password(data.password)))
        await self.session.commit(); await self.session.refresh(user); return user
    async def authenticate(self, email: str, password: str) -> User:
        user = await self.users.get_by_email(email)
        if not user or not user.is_active or not verify_password(password, user.password_hash):
            raise ForbiddenError("Credenciales inválidas")
        return user


def visible_operations(actor: User):
    query = select(Operation)
    if actor.role == Role.SALES_MANAGER: return query
    if actor.role == Role.SUPERVISOR: return query.where(Operation.zone == actor.zone)
    if actor.role == Role.OPERATOR: return query.where(Operation.created_by_id == actor.id)
    raise ForbiddenError("Este rol no consulta operaciones comerciales")


class OperationService:
    def __init__(self, session: AsyncSession): self.session, self.operations = session, OperationRepository(session)
    async def create(self, actor: User, data: OperationCreate) -> Operation:
        if actor.role != Role.OPERATOR: raise ForbiddenError("Solo un encargado puede cargar operaciones")
        if actor.team != data.team or actor.zone != data.zone: raise ForbiddenError("Solo puede registrar operaciones de su equipo y zona")
        result = await self.operations.create(Operation(**data.model_dump(), created_by_id=actor.id))
        await self.session.commit(); await self.session.refresh(result); return result
    async def list(self, actor: User): return await self.operations.list(visible_operations(actor))
    async def update(self, actor: User, operation_id: int, data: OperationUpdate) -> Operation:
        operation = await self.operations.get(operation_id)
        if not operation: raise NotFoundError("Operación inexistente")
        if actor.role != Role.SUPERVISOR or operation.zone != actor.zone: raise ForbiddenError("No puede aprobar esta operación")
        changes = data.model_dump(exclude_none=True)
        if changes.get("discount_percent", Decimal(0)) > 30: raise DomainError("El descuento máximo autorizable es 30%")
        for field, value in changes.items(): setattr(operation, field, value)
        await self.session.commit(); await self.session.refresh(operation); return operation
    async def metrics(self, actor: User):
        total, revenue, average, completed = await self.operations.aggregate(visible_operations(actor))
        rate = round((completed / total) * 100, 2) if total else 0
        return {"total_operations": total, "total_revenue": revenue, "average_ticket": average, "conversion_rate": rate}


class MonitoringService:
    def __init__(self, session: AsyncSession): self.audits = AuditRepository(session)
    async def metrics(self, actor: User):
        if actor.role != Role.SYSTEMS: raise ForbiddenError("Solo Sistemas accede a métricas del servidor")
        count, latency, errors = await self.audits.server_metrics()
        return {"request_count": count, "average_latency_ms": float(latency), "error_rate": round(float(errors) * 100, 2)}
    async def recent_requests(self, actor: User, limit: int):
        if actor.role != Role.SYSTEMS: raise ForbiddenError("Solo Sistemas accede a los registros del servidor")
        return await self.audits.recent(limit)
