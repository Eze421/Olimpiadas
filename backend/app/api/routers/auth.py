from fastapi import APIRouter, HTTPException, status
from app.api.dependencies import SessionDep
from app.core.security import create_access_token
from app.schemas import LoginRequest, TokenResponse, UserCreate, UserRead
from app.services import AuthService, DomainError, ForbiddenError

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, session: SessionDep):
    try: return await AuthService(session).register(data)
    except DomainError as error: raise HTTPException(status_code=409, detail=str(error))


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, session: SessionDep):
    try:
        user = await AuthService(session).authenticate(str(data.email), data.password)
        return TokenResponse(access_token=create_access_token(str(user.id), user.role.value))
    except ForbiddenError as error: raise HTTPException(status_code=401, detail=str(error))
