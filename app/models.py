import enum
from datetime import date, datetime
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Role(str, enum.Enum):
    SALES_MANAGER = "sales_manager"
    SUPERVISOR = "supervisor"
    OPERATOR = "operator"
    SYSTEMS = "systems"


class OperationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProductType(str, enum.Enum):
    ACCOMMODATION = "accommodation"
    FLIGHT = "flight"
    CAR_RENTAL = "car_rental"
    PACKAGE = "package"


class Currency(str, enum.Enum):
    ARS = "ARS"
    USD = "USD"


class SaleStatus(str, enum.Enum):
    PENDING_PAYMENT = "pending_payment"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    REFUND_PENDING = "refund_pending"
    REFUNDED = "refunded"


class PaymentMethod(str, enum.Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    DIGITAL_WALLET = "digital_wallet"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REFUNDED = "refunded"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role), index=True)
    team: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    zone: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Operation(Base):
    __tablename__ = "operations"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(150))
    product: Mapped[str] = mapped_column(String(150))
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    discount_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    status: Mapped[OperationStatus] = mapped_column(Enum(OperationStatus), default=OperationStatus.PENDING)
    team: Mapped[str] = mapped_column(String(100), index=True)
    zone: Mapped[str] = mapped_column(String(100), index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RequestAudit(Base):
    __tablename__ = "request_audits"
    id: Mapped[int] = mapped_column(primary_key=True)
    method: Mapped[str] = mapped_column(String(10))
    path: Mapped[str] = mapped_column(String(500))
    status_code: Mapped[int] = mapped_column(Integer)
    duration_ms: Mapped[float] = mapped_column(Numeric(10, 2))
    user_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


# Catálogo y abastecimiento: cada servicio puede tener uno o más proveedores.
class Provider(Base):
    __tablename__ = "providers"
    id: Mapped[int] = mapped_column(primary_key=True)
    legal_name: Mapped[str] = mapped_column(String(180), unique=True)
    tax_id: Mapped[str | None] = mapped_column(String(30), unique=True)
    contact_name: Mapped[str | None] = mapped_column(String(150))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    external_reference: Mapped[str | None] = mapped_column(String(100), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    product_type: Mapped[ProductType] = mapped_column(Enum(ProductType), index=True)
    destination: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # itinerario, categoría, incluye/no incluye
    cancellation_policy: Mapped[str | None] = mapped_column(Text)
    base_price: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[Currency] = mapped_column(Enum(Currency), default=Currency.ARS)
    available_units: Mapped[int] = mapped_column(Integer, default=0)
    starts_on: Mapped[date | None] = mapped_column(Date, index=True)
    ends_on: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (CheckConstraint("base_price >= 0", name="ck_product_base_price"), CheckConstraint("available_units >= 0", name="ck_product_available_units"))


class ProductProvider(Base):
    __tablename__ = "product_providers"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id", ondelete="RESTRICT"), index=True)
    provider_product_code: Mapped[str | None] = mapped_column(String(100))
    cost_price: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[Currency] = mapped_column(Enum(Currency), default=Currency.ARS)
    valid_from: Mapped[date] = mapped_column(Date, default=date.today)
    valid_until: Mapped[date | None] = mapped_column(Date)
    __table_args__ = (UniqueConstraint("product_id", "provider_id", "valid_from", name="uq_product_provider_rate"), CheckConstraint("cost_price >= 0", name="ck_product_provider_cost"))


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    document_number: Mapped[str | None] = mapped_column(String(40), unique=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Cart(Base):
    __tablename__ = "carts"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), index=True)
    guest_email: Mapped[str | None] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CartItem(Base):
    __tablename__ = "cart_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    quoted_unit_price: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[Currency] = mapped_column(Enum(Currency))
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_cart_item_quantity"),)


# Venta conserva los importes y proveedor usados al confirmar: no depende de precios futuros.
class Sale(Base):
    __tablename__ = "sales"
    id: Mapped[int] = mapped_column(primary_key=True)
    sale_number: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), index=True)
    status: Mapped[SaleStatus] = mapped_column(Enum(SaleStatus), default=SaleStatus.PENDING_PAYMENT, index=True)
    currency: Mapped[Currency] = mapped_column(Enum(Currency))
    exchange_rate: Mapped[float | None] = mapped_column(Numeric(12, 4))
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2))
    discount_total: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2))
    coupon_code: Mapped[str | None] = mapped_column(String(50))
    purchased_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("subtotal >= 0 AND discount_total >= 0 AND total >= 0", name="ck_sale_amounts"),)


class SaleItem(Base):
    __tablename__ = "sale_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    provider_id: Mapped[int | None] = mapped_column(ForeignKey("providers.id", ondelete="SET NULL"), index=True)
    product_name: Mapped[str] = mapped_column(String(180))  # copia histórica para facturas/reportes
    destination: Mapped[str] = mapped_column(String(120), index=True)
    service_starts_on: Mapped[date | None] = mapped_column(Date)
    service_ends_on: Mapped[date | None] = mapped_column(Date)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2))
    discount_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2))
    __table_args__ = (CheckConstraint("quantity > 0 AND unit_price >= 0 AND total >= 0", name="ck_sale_item_amounts"),)


class Passenger(Base):
    __tablename__ = "passengers"
    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id", ondelete="CASCADE"), index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    document_number: Mapped[str] = mapped_column(String(40))
    birth_date: Mapped[date] = mapped_column(Date)
    nationality: Mapped[str] = mapped_column(String(80))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    passport_number: Mapped[str | None] = mapped_column(String(40))
    passport_expires_on: Mapped[date | None] = mapped_column(Date)


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id", ondelete="CASCADE"), index=True)
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), index=True)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.PENDING, index=True)
    installments: Mapped[int] = mapped_column(Integer, default=1)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    currency: Mapped[Currency] = mapped_column(Enum(Currency))
    gateway: Mapped[str | None] = mapped_column(String(80))
    gateway_transaction_id: Mapped[str | None] = mapped_column(String(160), unique=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (CheckConstraint("installments > 0 AND amount > 0", name="ck_payment_amount"),)
