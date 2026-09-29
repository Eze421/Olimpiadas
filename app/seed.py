"""Carga las cuatro cuentas de prueba: python -m app.seed"""
import asyncio
from app.core.database import SessionLocal, engine
from app.models import Base, Role
from app.schemas import UserCreate
from app.services import AuthService, DomainError

USERS = [
    ("jefe.ventas@demo.example.com", "Jefe de Ventas", Role.SALES_MANAGER, None, None),
    ("supervisor.sur@demo.example.com", "Supervisor Zona Sur", Role.SUPERVISOR, "ventas-sur", "sur"),
    ("encargado.sur@demo.example.com", "Encargado Zona Sur", Role.OPERATOR, "ventas-sur", "sur"),
    ("sistemas@demo.example.com", "Personal de Sistemas", Role.SYSTEMS, None, None),
]


async def seed():
    async with engine.begin() as connection: await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        service = AuthService(session)
        for email, name, role, team, zone in USERS:
            try:
                await service.register(UserCreate(email=email, full_name=name, password="DemoSeguro2026!", role=role, team=team, zone=zone))
            except DomainError:
                pass


if __name__ == "__main__": asyncio.run(seed())
