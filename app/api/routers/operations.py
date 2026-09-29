from fastapi import APIRouter, HTTPException, status
from app.api.dependencies import CurrentUser, SessionDep
from app.schemas import MetricsRead, OperationCreate, OperationRead, OperationUpdate
from app.services import DomainError, ForbiddenError, NotFoundError, OperationService

router = APIRouter(prefix="/operations", tags=["Operaciones"])


@router.post("", response_model=OperationRead, status_code=status.HTTP_201_CREATED)
async def create_operation(data: OperationCreate, user: CurrentUser, session: SessionDep):
    try: return await OperationService(session).create(user, data)
    except ForbiddenError as error: raise HTTPException(status_code=403, detail=str(error))


@router.get("", response_model=list[OperationRead])
async def list_operations(user: CurrentUser, session: SessionDep):
    try: return await OperationService(session).list(user)
    except ForbiddenError as error: raise HTTPException(status_code=403, detail=str(error))


@router.patch("/{operation_id}", response_model=OperationRead)
async def update_operation(operation_id: int, data: OperationUpdate, user: CurrentUser, session: SessionDep):
    try: return await OperationService(session).update(user, operation_id, data)
    except NotFoundError as error: raise HTTPException(status_code=404, detail=str(error))
    except ForbiddenError as error: raise HTTPException(status_code=403, detail=str(error))
    except DomainError as error: raise HTTPException(status_code=422, detail=str(error))


@router.get("/metrics/summary", response_model=MetricsRead)
async def commercial_metrics(user: CurrentUser, session: SessionDep):
    try: return await OperationService(session).metrics(user)
    except ForbiddenError as error: raise HTTPException(status_code=403, detail=str(error))
