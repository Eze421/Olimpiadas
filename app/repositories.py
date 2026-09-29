from sqlalchemy import Select, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Operation, RequestAudit, User


class UserRepository:
    def __init__(self, session: AsyncSession): self.session = session
    async def get_by_email(self, email: str): return await self.session.scalar(select(User).where(User.email == email))
    async def get_by_id(self, user_id: int): return await self.session.get(User, user_id)
    async def create(self, user: User) -> User:
        self.session.add(user); await self.session.flush(); return user


class OperationRepository:
    def __init__(self, session: AsyncSession): self.session = session
    async def create(self, operation: Operation) -> Operation:
        self.session.add(operation); await self.session.flush(); return operation
    async def get(self, operation_id: int): return await self.session.get(Operation, operation_id)
    async def list(self, query: Select): return list((await self.session.scalars(query.order_by(Operation.created_at.desc()))).all())
    async def aggregate(self, query: Select):
        scoped = query.subquery()
        row = (await self.session.execute(select(
            func.count(), func.coalesce(func.sum(scoped.c.amount), 0), func.coalesce(func.avg(scoped.c.amount), 0),
            func.coalesce(func.sum(case((scoped.c.status == "COMPLETED", 1), else_=0)), 0),
        ))).one()
        return row


class AuditRepository:
    def __init__(self, session: AsyncSession): self.session = session
    async def server_metrics(self):
        row = (await self.session.execute(select(func.count(RequestAudit.id), func.coalesce(func.avg(RequestAudit.duration_ms), 0), func.coalesce(func.avg(RequestAudit.status_code >= 500), 0)))).one()
        return row
    async def create(self, audit: RequestAudit):
        self.session.add(audit)
        await self.session.commit()
    async def recent(self, limit: int):
        statement = select(RequestAudit).order_by(RequestAudit.created_at.desc()).limit(limit)
        return list((await self.session.scalars(statement)).all())
