from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_env: str = "development"
    log_level: str = "INFO"
    debug: bool = True

    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:80"]

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Milvus
    milvus_host: str = "milvus-standalone"
    milvus_port: int = 19530

    # Future phases (optional)
    gemini_api_key: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "eu-west-1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
