from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="HCA_",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    log_level: str = "info"
    api_v1_prefix: str = "/api/v1"
    max_upload_bytes: int = 10 * 1024 * 1024

    database_url: str = "postgresql://exam_app:change_me@localhost:5432/exam_assessment"
    database_pool_size: int = Field(default=10, ge=1)
    database_max_overflow: int = Field(default=20, ge=0)

    jwt_secret_key: str = "development-only-secret-key-change-before-production"
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_issuer: str = "handwriting-criteria-assessment-api"
    jwt_audience: str = "handwriting-criteria-assessment-mobile"
    access_token_expire_minutes: int = Field(default=15, ge=1, le=1440)
    refresh_token_expire_days: int = Field(default=30, ge=1, le=365)

    cors_allowed_origins: str = "http://localhost:3000,http://localhost:8080"

    @property
    def host(self) -> str:
        return self.api_host

    @property
    def port(self) -> int:
        return self.api_port

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url

    @model_validator(mode="after")
    def reject_insecure_production_secret(self) -> "Settings":
        if self.app_env == "production" and (
            len(self.jwt_secret_key) < 32 or "change" in self.jwt_secret_key.lower()
        ):
            raise ValueError("HCA_JWT_SECRET_KEY must be a strong production secret")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
