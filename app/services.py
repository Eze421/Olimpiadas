from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import hash_password, verify_password
from app.models import AvailabilityMode, Operation, OperationStatus, Product, ProductImage, Role, User
from app.repositories import AuditRepository, OperationRepository, ProductRepository, UserRepository
from app.schemas import OperationCreate, OperationUpdate, ProductCreate, ProductUpdate, UserCreate


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


class ProductService:
    def __init__(self, session: AsyncSession): self.session, self.products = session, ProductRepository(session)
    @staticmethod
    def _require_manager(actor: User):
        if actor.role != Role.SALES_MANAGER: raise ForbiddenError("Solo Jefatura de ventas puede administrar el catálogo")
    async def list(self, include_inactive: bool = False):
        return await self.products.list(include_inactive=include_inactive)
    async def admin_list(self, actor: User):
        self._require_manager(actor)
        return await self.products.list(include_inactive=True)
    async def get(self, product_id: int):
        product = await self.products.get(product_id)
        if not product or not product.is_active: raise NotFoundError("Producto inexistente")
        return product
    async def create(self, actor: User, data: ProductCreate):
        self._require_manager(actor)
        return await self.products.create(Product(**data.model_dump()))
    async def update(self, actor: User, product_id: int, data: ProductUpdate):
        self._require_manager(actor)
        product = await self.products.get(product_id)
        if not product: raise NotFoundError("Producto inexistente")
        changes = data.model_dump(exclude_unset=True)
        mode = changes.get("availability_mode", product.availability_mode)
        if mode == AvailabilityMode.UNLIMITED:
            changes["available_units"] = None
        elif mode == AvailabilityMode.FINITE:
            units = changes.get("available_units", product.available_units)
            if units is None: raise DomainError("Al cambiar a disponibilidad finita debe indicar available_units")
        for field, value in changes.items(): setattr(product, field, value)
        if product.starts_on and product.ends_on and product.ends_on < product.starts_on:
            raise DomainError("ends_on no puede ser anterior a starts_on")
        return await self.products.save(product)
    async def delete(self, actor: User, product_id: int):
        self._require_manager(actor)
        product = await self.products.get(product_id)
        if not product: raise NotFoundError("Producto inexistente")
        product.is_active = False
        await self.products.save(product)
    async def add_image(self, actor: User, product_id: int, url: str, alt_text: str | None):
        self._require_manager(actor)
        product = await self.products.get(product_id)
        if not product: raise NotFoundError("Producto inexistente")
        image = ProductImage(product_id=product.id, url=url, alt_text=alt_text, position=len(product.images))
        await self.products.add_image(image)
        return image
    async def remove_image(self, actor: User, product_id: int, image_id: int):
        self._require_manager(actor)
        product = await self.products.get(product_id)
        if not product: raise NotFoundError("Producto inexistente")
        image = next((image for image in product.images if image.id == image_id), None)
        if image is None: raise NotFoundError("Imagen inexistente")
        await self.products.remove_image(image)
        return image.url
