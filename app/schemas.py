from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models import OperationStatus, Role


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=10, max_length=128)
    role: Role
    team: str | None = Field(default=None, max_length=100)
    zone: str | None = Field(default=None, max_length=100)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: str
    role: Role
    team: str | None
    zone: str | None
    is_active: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class OperationCreate(BaseModel):
    customer_name: str = Field(min_length=2, max_length=150)
    product: str = Field(min_length=2, max_length=150)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    team: str = Field(min_length=2, max_length=100)
    zone: str = Field(min_length=2, max_length=100)


class OperationUpdate(BaseModel):
    status: OperationStatus | None = None
    discount_percent: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)


class OperationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_name: str
    product: str
    amount: Decimal
    discount_percent: Decimal
    status: OperationStatus
    team: str
    zone: str
    created_by_id: int
    created_at: datetime


class MetricsRead(BaseModel):
    total_operations: int
    total_revenue: Decimal
    average_ticket: Decimal
    conversion_rate: float | None = None


class ServerMetricsRead(BaseModel):
    request_count: int
    error_rate: float
    average_latency_ms: float


class RequestAuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    method: str
    path: str
    status_code: int
    duration_ms: Decimal
    created_at: datetime
