# Olimpiadas API

Backend en FastAPI con arquitectura por capas: routers (HTTP), services (reglas), repositories (datos) y schemas (contratos Pydantic). Para desarrollo usa SQLite local por defecto, sin contenedores.

El modelo de ventas turísticas (productos, proveedores, carritos, compradores, pasajeros, ventas y pagos) está documentado en [docs/database-design.md](docs/database-design.md).

## Ejecutar

```bash
cp .env.example .env
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.seed
.venv/bin/uvicorn app.main:app --reload
```

La base se crea automáticamente en `data/olimpiadas.db`. Para usar PostgreSQL en un despliegue o entorno compartido, definí en `.env` una URL como `DATABASE_URL=postgresql+asyncpg://usuario:clave@host:5432/base`; Podman es opcional y ya no forma parte del inicio local.

La documentación interactiva queda en `http://127.0.0.1:8000/docs`.

## Frontend

La interfaz está en `../frontend`. Con el backend iniciado, ejecutá en otra terminal `cd ../frontend && python3 -m http.server 5500` y abrí `http://127.0.0.1:5500`. El backend habilita CORS para ese servidor local.

## Catálogo de productos

El catálogo público se consulta en `GET /api/v1/catalog/products`. Solo Jefe de ventas puede crear, editar, eliminar o administrar productos; las rutas de gestión requieren un token obtenido mediante login. La eliminación desactiva el producto para conservar referencias e historial de ventas. `GET /api/v1/catalog/products/manage/all` muestra también los productos desactivados, que pueden reactivarse con `PATCH` enviando `{"is_active": true}`.

Al crear un producto se envía `availability_mode` como `finite` o `unlimited`. Para `finite`, `available_units` es obligatorio; para `unlimited`, debe ser `null`. En una edición se puede cambiar el modo; pasar a finito requiere indicar la cantidad nueva. Las imágenes se cargan por separado a `POST /api/v1/catalog/products/{id}/images` como multipart (`file`, opcional `alt_text`), acepta JPEG, PNG y WebP de hasta 5 MB y devuelve una URL bajo `/media/`. Se pueden añadir varias y borrar cada una con `DELETE /api/v1/catalog/products/{id}/images/{image_id}`. El directorio `MEDIA_DIR` (por defecto `media/`) debe persistirse y respaldarse en despliegues.

## Registro de clientes y carrito

Los clientes se registran con `POST /api/v1/auth/register/customer`, enviando nombre, apellido, correo, contraseña (mínimo 10 caracteres) y teléfono opcional. La respuesta incluye un token de acceso y el ID de cliente; el alta pública siempre crea el rol cliente. La ruta `POST /api/v1/auth/register` queda reservada a Jefatura para crear cuentas internas.

Con ese token, el cliente puede consultar `GET /api/v1/cart`, agregar con `POST /api/v1/cart/items` (`product_id`, `quantity`), cambiar cantidades con `PATCH /api/v1/cart/items/{item_id}`, quitar una línea con `DELETE /api/v1/cart/items/{item_id}` o vaciarlo con `DELETE /api/v1/cart`. El carrito vence a los 15 minutos de su creación. El servidor valida que el producto siga publicado y que no se exceda el stock finito; los subtotales se devuelven separados por moneda.

`POST /api/v1/cart/checkout` realiza una compra simulada: registra una reserva confirmada, descuenta stock finito y vacía el carrito. Para evitar conversiones ficticias, cada compra debe contener una única moneda. `GET /api/v1/auth/me` devuelve los datos y reservas del cliente; una reserva confirmada puede anularse con `POST /api/v1/cart/reservations/{sale_number}/cancel`, restaurando su disponibilidad. No hay cobro ni integración de pagos real.

## Inicio y detención automáticos

En Linux/Bazzite, una vez instaladas las dependencias, ejecutá `./scripts/start.sh` para crear/cargar la base SQLite local y arrancar la API. Para detenerla: `./scripts/stop.sh`.

En Windows, usá `scripts\\start.bat` y `scripts\\stop.bat`; no requieren Podman. Los scripts guardan el PID y el registro de la API en `.run/`, y la base local persiste en `data\\olimpiadas.db`.

## Cuentas de prueba

Todas usan la contraseña `DemoSeguro2026!`:

| Rol | Cuenta | Alcance |
|---|---|---|
| Jefe de ventas | jefe.ventas@demo.example.com | Ve todas las operaciones y métricas globales. |
| Supervisor | supervisor.sur@demo.example.com | Ve y aprueba únicamente su zona; descuento máximo 30%. |
| Encargado | encargado.sur@demo.example.com | Carga y ve sus propias operaciones de equipo/zona. |
| Sistemas | sistemas@demo.example.com | Solo panel de métricas HTTP del servidor. |

`GET /api/v1/monitoring/server-metrics` muestra cantidad de solicitudes, latencia promedio y tasa de errores 5xx; `GET /api/v1/monitoring/requests` expone los llamados recientes solo a Sistemas. El middleware registra las llamadas HTTP. El acceso SSH, FTP o al host no se expone por la API: debe gestionarse por infraestructura, con cuentas separadas, MFA y auditoría.
