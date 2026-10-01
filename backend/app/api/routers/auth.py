from fastapi import APIRouter, HTTPException, status
from app.api.dependencies import CurrentUser, SessionDep
from app.core.security import create_access_token
from app.models import Role
from app.schemas import CustomerProfileRead, CustomerRegister, CustomerRegistrationResponse, LoginRequest, TokenResponse, UserCreate, UserRead
from app.services import AuthService, DomainError, ForbiddenError

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, user: CurrentUser, session: SessionDep):
    if user.role != Role.SALES_MANAGER:
        raise HTTPException(status_code=403, detail="Solo Jefatura de ventas puede crear cuentas internas")
    try: return await AuthService(session).register(data)
    except DomainError as error: raise HTTPException(status_code=409, detail=str(error))


@router.post("/register/customer", response_model=CustomerRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_customer(data: CustomerRegister, session: SessionDep):
    try:
        user, customer = await AuthService(session).register_customer(data)
        token = create_access_token(str(user.id), user.role.value)
        return CustomerRegistrationResponse(access_token=token, customer_id=customer.id)
    except DomainError as error:
        raise HTTPException(status_code=409, detail=str(error))


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, session: SessionDep):
    try:
        user = await AuthService(session).authenticate(str(data.email), data.password)
        return TokenResponse(access_token=create_access_token(str(user.id), user.role.value))
    except ForbiddenError as error: raise HTTPException(status_code=401, detail=str(error))


@router.get("/me", response_model=CustomerProfileRead)
async def current_customer_profile(user: CurrentUser, session: SessionDep):
    try: return await AuthService(session).customer_profile(user)
    except ForbiddenError as error: raise HTTPException(status_code=403, detail=str(error))
