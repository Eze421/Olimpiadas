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


settings = Settings()
