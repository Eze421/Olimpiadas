import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.api.routers import auth, cart, catalog, monitoring, operations
from app.core.database import SessionLocal, engine
from app.models import Base, RequestAudit
from app.repositories import AuditRepository

app = FastAPI(title="Olimpiadas API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(operations.router, prefix="/api/v1")
app.include_router(monitoring.router, prefix="/api/v1")
app.include_router(catalog.router, prefix="/api/v1")
app.include_router(cart.router, prefix="/api/v1")

from pathlib import Path
from fastapi.staticfiles import StaticFiles
from app.core.config import settings

Path(settings.media_dir).mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")


@app.on_event("startup")
async def startup() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        if engine.dialect.name == "postgresql":
            await connection.execute(text("ALTER TYPE role ADD VALUE IF NOT EXISTS 'CUSTOMER'"))
            await connection.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS availability_mode availabilitymode NOT NULL DEFAULT 'FINITE'"))
            await connection.execute(text("ALTER TABLE products ALTER COLUMN available_units DROP NOT NULL"))
            await connection.execute(text("UPDATE products SET available_units = NULL WHERE availability_mode = 'UNLIMITED'"))
            # Bases creadas antes de la modalidad ilimitada tenían esta regla sin admitir NULL.
            # Se la reemplaza para que el stock solo sea obligatorio en productos finitos.
            await connection.execute(text("ALTER TABLE products DROP CONSTRAINT IF EXISTS ck_product_available_units"))
            await connection.execute(text("""
                ALTER TABLE products ADD CONSTRAINT ck_product_available_units
                CHECK (available_units IS NULL OR available_units >= 0)
            """))
            await connection.execute(text("""
                DO $$ BEGIN
                    ALTER TABLE products ADD CONSTRAINT ck_product_availability
                    CHECK ((availability_mode = 'UNLIMITED' AND available_units IS NULL)
                        OR (availability_mode = 'FINITE' AND available_units IS NOT NULL));
                EXCEPTION WHEN duplicate_object THEN NULL;
                END $$
            """))


@app.middleware("http")
async def audit_requests(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    if not request.url.path.startswith("/docs") and not request.url.path.startswith("/openapi"):
        async with SessionLocal() as session:
            await AuditRepository(session).create(RequestAudit(
                method=request.method, path=request.url.path, status_code=response.status_code,
                duration_ms=(time.perf_counter() - started) * 1000,
            ))
    return response


@app.get("/health", tags=["Infraestructura"])
async def health():
    return {"status": "ok"}
