# Olimpiadas API

Backend en FastAPI + PostgreSQL con arquitectura por capas: routers (HTTP), services (reglas), repositories (datos) y schemas (contratos Pydantic).

El modelo de ventas turísticas (productos, proveedores, carritos, compradores, pasajeros, ventas y pagos) está documentado en [docs/database-design.md](docs/database-design.md).

## Ejecutar

```bash
cp .env.example .env
# Bazzite/Fedora Atomic: PostgreSQL aislado, solo accesible desde localhost
podman run -d --name olimpiadas-postgres --replace --label app=olimpiadas \
  -e POSTGRES_DB=olimpiadas -e POSTGRES_USER=olimpiadas -e POSTGRES_PASSWORD=olimpiadas \
  -p 127.0.0.1:5432:5432 -v olimpiadas_postgres_data:/var/lib/postgresql/data:Z \
  docker.io/library/postgres:16-alpine
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.seed
.venv/bin/uvicorn app.main:app --reload
```

La documentación interactiva queda en `http://127.0.0.1:8000/docs`.

## Inicio y detención automáticos

En Linux/Bazzite, una vez instaladas las dependencias, ejecutá `./scripts/start.sh` para levantar PostgreSQL aislado, cargar las cuentas y arrancar la API. Para detener ambos servicios: `./scripts/stop.sh`.

En Windows con Podman instalado, usá `scripts\\start.bat` y `scripts\\stop.bat`. Los scripts guardan el PID y el registro de la API en `.run/`; la base conserva sus datos en el volumen de Podman.

## Cuentas de prueba

Todas usan la contraseña `DemoSeguro2026!`:

| Rol | Cuenta | Alcance |
|---|---|---|
| Jefe de ventas | jefe.ventas@demo.example.com | Ve todas las operaciones y métricas globales. |
| Supervisor | supervisor.sur@demo.example.com | Ve y aprueba únicamente su zona; descuento máximo 30%. |
| Encargado | encargado.sur@demo.example.com | Carga y ve sus propias operaciones de equipo/zona. |
| Sistemas | sistemas@demo.example.com | Solo panel de métricas HTTP del servidor. |

`GET /api/v1/monitoring/server-metrics` muestra cantidad de solicitudes, latencia promedio y tasa de errores 5xx; `GET /api/v1/monitoring/requests` expone los llamados recientes solo a Sistemas. El middleware registra las llamadas HTTP. El acceso SSH, FTP o al host no se expone por la API: debe gestionarse por infraestructura, con cuentas separadas, MFA y auditoría.
