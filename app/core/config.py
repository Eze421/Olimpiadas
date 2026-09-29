from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://olimpiadas:olimpiadas@localhost:5432/olimpiadas"
    jwt_secret: str = "change-this-in-production-to-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
