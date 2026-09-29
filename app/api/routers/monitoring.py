from fastapi import APIRouter, HTTPException
from app.api.dependencies import CurrentUser, SessionDep
from app.schemas import RequestAuditRead, ServerMetricsRead
from app.services import ForbiddenError, MonitoringService

router = APIRouter(prefix="/monitoring", tags=["Sistemas"])


@router.get("/server-metrics", response_model=ServerMetricsRead)
async def server_metrics(user: CurrentUser, session: SessionDep):
    try: return await MonitoringService(session).metrics(user)
    except ForbiddenError as error: raise HTTPException(status_code=403, detail=str(error))


@router.get("/requests", response_model=list[RequestAuditRead])
async def recent_requests(user: CurrentUser, session: SessionDep, limit: int = 100):
    try: return await MonitoringService(session).recent_requests(user, min(max(limit, 1), 500))
    except ForbiddenError as error: raise HTTPException(status_code=403, detail=str(error))
