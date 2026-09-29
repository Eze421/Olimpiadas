import time
from fastapi import FastAPI, Request
from app.api.routers import auth, monitoring, operations
from app.core.database import SessionLocal, engine
from app.models import Base, RequestAudit
from app.repositories import AuditRepository

app = FastAPI(title="Olimpiadas API", version="1.0.0")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(operations.router, prefix="/api/v1")
app.include_router(monitoring.router, prefix="/api/v1")


@app.on_event("startup")
async def startup() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


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
