from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from app.models import AvailabilityMode, Currency, OperationStatus, ProductType, Role


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


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=2, max_length=180)
    product_type: ProductType
    destination: str = Field(min_length=2, max_length=120)
    description: str | None = None
    details: dict | None = None
    cancellation_policy: str | None = None
    base_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    currency: Currency = Currency.ARS
    availability_mode: AvailabilityMode = AvailabilityMode.FINITE
    available_units: int | None = Field(default=None, ge=0)
    starts_on: date | None = None
    ends_on: date | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def validate_availability(self):
        if self.availability_mode == AvailabilityMode.UNLIMITED and self.available_units is not None:
            raise ValueError("Los productos ilimitados deben enviar available_units=null")
        if self.availability_mode == AvailabilityMode.FINITE and self.available_units is None:
            raise ValueError("Los productos finitos necesitan una cantidad disponible")
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("ends_on no puede ser anterior a starts_on")
        return self


class ProductUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=60)
    name: str | None = Field(default=None, min_length=2, max_length=180)
    product_type: ProductType | None = None
    destination: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None
    details: dict | None = None
    cancellation_policy: str | None = None
    base_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    currency: Currency | None = None
    availability_mode: AvailabilityMode | None = None
    available_units: int | None = Field(default=None, ge=0)
    starts_on: date | None = None
    ends_on: date | None = None
    is_active: bool | None = None


class ProductImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    url: str
    alt_text: str | None
    position: int


class ProductRead(BaseModel):
    id: int
    sku: str
    name: str
    product_type: ProductType
    destination: str
    description: str | None
    details: dict | None
    cancellation_policy: str | None
    base_price: Decimal
    currency: Currency
    availability_mode: AvailabilityMode
    available_units: int | None
    starts_on: date | None
    ends_on: date | None
    is_active: bool
    images: list[ProductImageRead] = []

    model_config = ConfigDict(from_attributes=True)
