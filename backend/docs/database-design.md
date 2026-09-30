# Diseño de base de datos — Portal de viajes

El modelo cubre la venta de estadías, vuelos, alquileres y paquetes, incluso cuando el cliente combina servicios en una compra.

```text
Customer ──< Cart ──< CartItem >── Product ──< ProductProvider >── Provider
Customer ──< Sale ──< SaleItem >── Product
                  ├──< Passenger
                  └──< Payment
SaleItem ────────────────────────────────> Provider
```

| Necesidad relevada | Tablas y criterio |
|---|---|
| Catálogo, destino, fechas y disponibilidad | `products`, con tipo, destino, inicio/fin, cupos, moneda y detalle JSON. |
| Con quién se compra el servicio | `providers` y `product_providers`; registra código externo, costo y vigencia de la tarifa. `sale_items.provider_id` conserva el proveedor elegido. |
| Carrito y reserva temporal | `carts.expires_at` y `cart_items.quoted_unit_price`; la aplicación asigna 15 minutos al crearlo. |
| Comprador, familia y grupos | `customers` identifica al titular; `passengers` guarda cada viajero de la venta. |
| Fecha e historial de venta | `sales.purchased_at`, `confirmed_at`, `cancelled_at`; los ítems guardan precio, nombre y destino como fotografía histórica. |
| Pagos | `payments` soporta tarjeta, transferencia y billetera, cuotas, estado, importe, moneda y referencia de la pasarela. Nunca almacena número ni CVV de tarjeta. |
| Pesos/dólares | `currency` en producto, venta y pago; `sales.exchange_rate` fija el tipo de cambio aplicado. |

Las restricciones de base de datos impiden cantidades o importes negativos y evitan duplicar una tarifa de proveedor para el mismo producto y fecha de vigencia.
