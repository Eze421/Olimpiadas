from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # SQLite es la opción local sin contenedores. PostgreSQL sigue siendo compatible
    # definiendo DATABASE_URL=postgresql+asyncpg://... en .env.
    database_url: str = "sqlite+aiosqlite:///./data/olimpiadas.db"
    jwt_secret: str = "change-this-in-production-to-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    media_dir: str = "media"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url", mode="before")
    @classmethod
    def use_async_postgres_driver(cls, value: str) -> str:
        """Render entrega postgresql://; SQLAlchemy async requiere asyncpg explícito."""
        if value.startswith("postgres://"):
            return "postgresql+asyncpg://" + value.removeprefix("postgres://")
        if value.startswith("postgresql://"):
            return "postgresql+asyncpg://" + value.removeprefix("postgresql://")
        return value


settings = Settings()
