from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import hash_password, verify_password
from app.models import AvailabilityMode, Cart, CartItem, Customer, Operation, OperationStatus, Product, ProductImage, ProductPackageItem, ProductType, Role, Sale, SaleItem, SaleStatus, User
from app.repositories import AuditRepository, OperationRepository, ProductRepository, UserRepository
from app.schemas import CartItemCreate, CartItemUpdate, CustomerRegister, OperationCreate, OperationUpdate, ProductCreate, ProductUpdate, UserCreate


class DomainError(Exception): pass
class NotFoundError(DomainError): pass
class ForbiddenError(DomainError): pass


class AuthService:
    def __init__(self, session: AsyncSession): self.session, self.users = session, UserRepository(session)
    async def register(self, data: UserCreate) -> User:
        if data.role == Role.CUSTOMER:
            raise DomainError("Las cuentas de cliente deben registrarse en /auth/register/customer")
        email = str(data.email).lower()
        if await self.users.get_by_email(email):
            raise DomainError("El correo ya está registrado")
        values = data.model_dump(exclude={"password"})
        values["email"] = email
        user = await self.users.create(User(**values, password_hash=hash_password(data.password)))
        await self.session.commit(); await self.session.refresh(user); return user
    async def authenticate(self, email: str, password: str) -> User:
        user = await self.users.get_by_email(email.lower())
        if not user or not user.is_active or not verify_password(password, user.password_hash):
            raise ForbiddenError("Credenciales inválidas")
        return user
    async def register_customer(self, data: CustomerRegister):
        email = str(data.email).lower()
        if await self.users.get_by_email(email):
            raise DomainError("El correo ya está registrado")
        full_name = f"{data.first_name.strip()} {data.last_name.strip()}"
        user = await self.users.create(User(
            email=email,
            full_name=full_name,
            password_hash=hash_password(data.password),
            role=Role.CUSTOMER,
        ))
        customer = Customer(
            user_id=user.id,
            first_name=data.first_name.strip(),
            last_name=data.last_name.strip(),
            email=email,
            phone=data.phone,
        )
        self.session.add(customer)
        await self.session.commit()
        await self.session.refresh(customer)
        return user, customer

    async def customer_profile(self, actor: User):
        customer = await self.session.scalar(select(Customer).where(Customer.user_id == actor.id))
        if not customer:
            raise ForbiddenError("Este perfil no corresponde a una cuenta de cliente")
        sales = list((await self.session.scalars(
            select(Sale).where(Sale.customer_id == customer.id).order_by(Sale.purchased_at.desc())
        )).all())
        reservations = []
        for sale in sales:
            items = list((await self.session.scalars(
                select(SaleItem).where(SaleItem.sale_id == sale.id).order_by(SaleItem.id)
            )).all())
            reservations.append({
                "sale_number": sale.sale_number, "status": sale.status, "currency": sale.currency,
                "total": sale.total, "purchased_at": sale.purchased_at,
                "can_cancel": sale.status == SaleStatus.CONFIRMED,
                "items": [{"product_name": item.product_name, "destination": item.destination, "quantity": item.quantity, "total": item.total} for item in items],
            })
        return {"full_name": actor.full_name, "email": customer.email, "phone": customer.phone, "reservations": reservations}


def visible_operations(actor: User):
    query = select(Operation)
    if actor.role == Role.SALES_MANAGER: return query
    if actor.role == Role.SUPERVISOR: return query.where(Operation.zone == actor.zone)
    if actor.role == Role.OPERATOR: return query.where(Operation.created_by_id == actor.id)
    raise ForbiddenError("Este rol no consulta operaciones comerciales")


class OperationService:
    def __init__(self, session: AsyncSession): self.session, self.operations = session, OperationRepository(session)
    async def create(self, actor: User, data: OperationCreate) -> Operation:
        if actor.role != Role.OPERATOR: raise ForbiddenError("Solo un encargado puede cargar operaciones")
        if actor.team != data.team or actor.zone != data.zone: raise ForbiddenError("Solo puede registrar operaciones de su equipo y zona")
        result = await self.operations.create(Operation(**data.model_dump(), created_by_id=actor.id))
        await self.session.commit(); await self.session.refresh(result); return result
    async def list(self, actor: User): return await self.operations.list(visible_operations(actor))
    async def update(self, actor: User, operation_id: int, data: OperationUpdate) -> Operation:
        operation = await self.operations.get(operation_id)
        if not operation: raise NotFoundError("Operación inexistente")
        if actor.role != Role.SUPERVISOR or operation.zone != actor.zone: raise ForbiddenError("No puede aprobar esta operación")
        changes = data.model_dump(exclude_none=True)
        if changes.get("discount_percent", Decimal(0)) > 30: raise DomainError("El descuento máximo autorizable es 30%")
        for field, value in changes.items(): setattr(operation, field, value)
        await self.session.commit(); await self.session.refresh(operation); return operation
    async def metrics(self, actor: User):
        total, revenue, average, completed = await self.operations.aggregate(visible_operations(actor))
        rate = round((completed / total) * 100, 2) if total else 0
        return {"total_operations": total, "total_revenue": revenue, "average_ticket": average, "conversion_rate": rate}


class MonitoringService:
    def __init__(self, session: AsyncSession): self.audits = AuditRepository(session)
    async def metrics(self, actor: User):
        if actor.role != Role.SYSTEMS: raise ForbiddenError("Solo Sistemas accede a métricas del servidor")
        count, latency, errors = await self.audits.server_metrics()
        return {"request_count": count, "average_latency_ms": float(latency), "error_rate": round(float(errors) * 100, 2)}
    async def recent_requests(self, actor: User, limit: int):
        if actor.role != Role.SYSTEMS: raise ForbiddenError("Solo Sistemas accede a los registros del servidor")
        return await self.audits.recent(limit)


class ProductService:
    def __init__(self, session: AsyncSession): self.session, self.products = session, ProductRepository(session)
    @staticmethod
    def _require_manager(actor: User):
        if actor.role != Role.SALES_MANAGER: raise ForbiddenError("Solo Jefatura de ventas puede administrar el catálogo")
    async def list(self, include_inactive: bool = False):
        return await self.products.list(include_inactive=include_inactive)
    async def admin_list(self, actor: User):
        self._require_manager(actor)
        return await self.products.list(include_inactive=True)
    async def get(self, product_id: int):
        product = await self.products.get(product_id)
        if not product or not product.is_active: raise NotFoundError("Producto inexistente")
        return product
    async def create(self, actor: User, data: ProductCreate):
        self._require_manager(actor)
        values = data.model_dump(exclude={"package_components"})
        components = data.package_components
        await self._validate_components(components)
        product = Product(**values)
        self.session.add(product)
        await self.session.flush()
        self.session.add_all([ProductPackageItem(package_id=product.id, included_product_id=item.product_id, quantity=item.quantity) for item in components])
        await self.session.commit()
        return await self.products.get(product.id)
    async def update(self, actor: User, product_id: int, data: ProductUpdate):
        self._require_manager(actor)
        product = await self.products.get(product_id)
        if not product: raise NotFoundError("Producto inexistente")
        changes = data.model_dump(exclude_unset=True)
        components = changes.pop("package_components", None)
        mode = changes.get("availability_mode", product.availability_mode)
        if mode == AvailabilityMode.UNLIMITED:
            changes["available_units"] = None
        elif mode == AvailabilityMode.FINITE:
            units = changes.get("available_units", product.available_units)
            if units is None: raise DomainError("Al cambiar a disponibilidad finita debe indicar available_units")
        for field, value in changes.items(): setattr(product, field, value)
        if product.starts_on and product.ends_on and product.ends_on < product.starts_on:
            raise DomainError("ends_on no puede ser anterior a starts_on")
        if product.product_type != ProductType.PACKAGE:
            if components:
                raise DomainError("Solo los paquetes pueden incluir servicios")
            await self.session.execute(delete(ProductPackageItem).where(ProductPackageItem.package_id == product.id))
        elif components is not None:
            if not components: raise DomainError("Un paquete debe incluir al menos un servicio")
            await self._validate_components(components, excluded_product_id=product.id)
            await self.session.execute(delete(ProductPackageItem).where(ProductPackageItem.package_id == product.id))
            self.session.add_all([ProductPackageItem(package_id=product.id, included_product_id=item["product_id"] if isinstance(item, dict) else item.product_id, quantity=item["quantity"] if isinstance(item, dict) else item.quantity) for item in components])
        elif not product.package_components:
            raise DomainError("Un paquete debe incluir al menos un servicio")
        return await self.products.save(product)

    async def _validate_components(self, components, excluded_product_id: int | None = None):
        ids = [item["product_id"] if isinstance(item, dict) else item.product_id for item in components]
        if len(ids) != len(set(ids)):
            raise DomainError("No se puede incluir el mismo servicio más de una vez")
        if excluded_product_id and excluded_product_id in ids:
            raise DomainError("Un paquete no puede incluirse a sí mismo")
        if not ids: return
        products = list((await self.session.scalars(select(Product).where(Product.id.in_(ids), Product.is_active.is_(True)))).all())
        if len(products) != len(ids): raise DomainError("Uno de los servicios incluidos no está disponible")
        if any(product.product_type == ProductType.PACKAGE for product in products):
            raise DomainError("Un paquete no puede contener otro paquete")
    async def delete(self, actor: User, product_id: int):
        self._require_manager(actor)
        product = await self.products.get(product_id)
        if not product: raise NotFoundError("Producto inexistente")
        product.is_active = False
        await self.products.save(product)
    async def add_image(self, actor: User, product_id: int, url: str, alt_text: str | None):
        self._require_manager(actor)
        product = await self.products.get(product_id)
        if not product: raise NotFoundError("Producto inexistente")
        image = ProductImage(product_id=product.id, url=url, alt_text=alt_text, position=len(product.images))
        await self.products.add_image(image)
        return image
    async def remove_image(self, actor: User, product_id: int, image_id: int):
        self._require_manager(actor)
        product = await self.products.get(product_id)
        if not product: raise NotFoundError("Producto inexistente")
        image = next((image for image in product.images if image.id == image_id), None)
        if image is None: raise NotFoundError("Imagen inexistente")
        await self.products.remove_image(image)
        return image.url


class CartService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.products = ProductRepository(session)

    @staticmethod
    def _validate_quantity(product: Product, quantity: int):
        if product.availability_mode == AvailabilityMode.FINITE and quantity > (product.available_units or 0):
            raise DomainError("No hay suficientes unidades disponibles")
        for component in product.package_components:
            included = component.included_product
            needed = quantity * component.quantity
            if not included.is_active or (included.availability_mode == AvailabilityMode.FINITE and needed > (included.available_units or 0)):
                raise DomainError(f"El paquete no tiene disponibilidad para {included.name}")

    async def _customer(self, actor: User):
        if actor.role != Role.CUSTOMER:
            raise ForbiddenError("El carrito está disponible para cuentas de cliente")
        customer = await self.session.scalar(select(Customer).where(Customer.user_id == actor.id))
        if not customer:
            raise ForbiddenError("No se encontró el perfil de cliente")
        return customer

    async def _active_cart(self, actor: User):
        customer = await self._customer(actor)
        now = datetime.now(timezone.utc)
        await self.session.execute(
            delete(Cart).where(Cart.customer_id == customer.id, Cart.expires_at <= now)
        )
        cart = await self.session.scalar(
            select(Cart)
            .where(Cart.customer_id == customer.id, Cart.expires_at > now)
            .order_by(Cart.created_at.desc(), Cart.id.desc())
        )
        if cart is None:
            cart = Cart(customer_id=customer.id, expires_at=now + timedelta(minutes=15))
            self.session.add(cart)
            await self.session.flush()
        return cart

    async def _read(self, cart: Cart):
        rows = (await self.session.execute(
            select(CartItem, Product)
            .join(Product, Product.id == CartItem.product_id)
            .options(selectinload(Product.images))
            .where(CartItem.cart_id == cart.id)
            .order_by(CartItem.id)
        )).all()
        items = []
        totals: dict = {}
        for item, product in rows:
            line_total = Decimal(item.quoted_unit_price) * item.quantity
            currency = item.currency
            totals[currency] = totals.get(currency, Decimal("0")) + line_total
            items.append({
                "id": item.id,
                "product_id": product.id,
                "product_name": product.name,
                "destination": product.destination,
                "image_url": product.images[0].url if product.images else None,
                "quantity": item.quantity,
                "unit_price": item.quoted_unit_price,
                "currency": currency,
                "line_total": line_total,
                "availability_mode": product.availability_mode,
                "available_units": product.available_units,
            })
        return {
            "id": cart.id,
            "expires_at": cart.expires_at,
            "items": items,
            "totals": [{"currency": currency, "amount": amount} for currency, amount in totals.items()],
        }

    async def get(self, actor: User):
        cart = await self._active_cart(actor)
        await self.session.commit()
        return await self._read(cart)

    async def add(self, actor: User, data: CartItemCreate):
        cart = await self._active_cart(actor)
        product = await self.products.get(data.product_id)
        if not product or not product.is_active:
            raise NotFoundError("El producto no está disponible")
        existing = await self.session.scalar(
            select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == product.id)
        )
        new_quantity = data.quantity + (existing.quantity if existing else 0)
        self._validate_quantity(product, new_quantity)
        if existing:
            existing.quantity = new_quantity
            existing.quoted_unit_price = product.base_price
            existing.currency = product.currency
        else:
            self.session.add(CartItem(
                cart_id=cart.id,
                product_id=product.id,
                quantity=data.quantity,
                quoted_unit_price=product.base_price,
                currency=product.currency,
            ))
        await self.session.commit()
        return await self._read(cart)

    async def update(self, actor: User, item_id: int, data: CartItemUpdate):
        cart = await self._active_cart(actor)
        item = await self.session.scalar(
            select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id)
        )
        if not item:
            raise NotFoundError("El producto no está en el carrito")
        product = await self.products.get(item.product_id)
        if not product or not product.is_active:
            raise NotFoundError("El producto dejó de estar disponible")
        self._validate_quantity(product, data.quantity)
        item.quantity = data.quantity
        item.quoted_unit_price = product.base_price
        item.currency = product.currency
        await self.session.commit()
        return await self._read(cart)

    async def remove(self, actor: User, item_id: int):
        cart = await self._active_cart(actor)
        item = await self.session.scalar(
            select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id)
        )
        if not item:
            raise NotFoundError("El producto no está en el carrito")
        await self.session.delete(item)
        await self.session.commit()
        return await self._read(cart)

    async def clear(self, actor: User):
        cart = await self._active_cart(actor)
        await self.session.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
        await self.session.commit()
        return await self._read(cart)

    async def checkout(self, actor: User):
        cart = await self._active_cart(actor)
        customer = await self._customer(actor)
        items = list((await self.session.scalars(select(CartItem).where(CartItem.cart_id == cart.id).order_by(CartItem.id))).all())
        if not items:
            raise DomainError("No podés confirmar un carrito vacío")
        if len({item.currency for item in items}) > 1:
            raise DomainError("Para esta compra simulada, el carrito debe contener productos de una sola moneda")
        products = []
        for item in items:
            product = await self.products.get(item.product_id)
            if not product or not product.is_active:
                raise DomainError("Uno de los productos ya no está disponible")
            self._validate_quantity(product, item.quantity)
            products.append((item, product))
        subtotal = sum((Decimal(item.quoted_unit_price) * item.quantity for item, _ in products), Decimal("0"))
        sale = Sale(
            sale_number=f"AZ-{datetime.now(timezone.utc):%Y%m%d}-{datetime.now(timezone.utc).strftime('%f')[-6:]}",
            customer_id=customer.id, status=SaleStatus.CONFIRMED, currency=items[0].currency,
            subtotal=subtotal, total=subtotal, discount_total=Decimal("0"), confirmed_at=datetime.now(timezone.utc),
        )
        self.session.add(sale)
        await self.session.flush()
        for item, product in products:
            total = Decimal(item.quoted_unit_price) * item.quantity
            self.session.add(SaleItem(
                sale_id=sale.id, product_id=product.id, product_name=product.name, destination=product.destination,
                service_starts_on=product.starts_on, service_ends_on=product.ends_on, quantity=item.quantity,
                unit_price=item.quoted_unit_price, total=total, discount_amount=Decimal("0"),
            ))
            await self._adjust_stock(product, item.quantity, -1)
        await self.session.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
        await self.session.commit()
        return {"sale_number": sale.sale_number}

    async def cancel_reservation(self, actor: User, sale_number: str):
        customer = await self._customer(actor)
        sale = await self.session.scalar(select(Sale).where(Sale.sale_number == sale_number, Sale.customer_id == customer.id))
        if not sale:
            raise NotFoundError("Reserva inexistente")
        if sale.status != SaleStatus.CONFIRMED:
            raise DomainError("Solo se pueden cancelar reservas confirmadas")
        items = list((await self.session.scalars(select(SaleItem).where(SaleItem.sale_id == sale.id))).all())
        for item in items:
            product = await self.products.get(item.product_id)
            if product:
                await self._adjust_stock(product, item.quantity, 1)
        sale.status = SaleStatus.CANCELLED
        sale.cancelled_at = datetime.now(timezone.utc)
        await self.session.commit()

    async def _adjust_stock(self, product: Product, quantity: int, direction: int):
        if product.availability_mode == AvailabilityMode.FINITE:
            product.available_units = (product.available_units or 0) + direction * quantity
        for component in product.package_components:
            included = component.included_product
            if included.availability_mode == AvailabilityMode.FINITE:
                included.available_units = (included.available_units or 0) + direction * quantity * component.quantity
