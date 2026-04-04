from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
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
    cors_origins: str = "http://localhost:3000,http://localhost:80,http://localhost"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Milvus
    milvus_host: str = "milvus-standalone"
    milvus_port: int = 19530
    milvus_collection_name: str = "turkcell_documents"

    # PII Masking (Phase 4)
    pii_masking_enabled: bool = True

    # Google Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Gemini Live API
    gemini_live_enabled: bool = False
    gemini_live_model: str = "gemini-3.1-flash-live-preview"
    gemini_live_voice: str = "Kore"

    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "eu-west-1"

    # MCP Server
    mcp_enabled: bool = True
    mcp_api_key: str = ""

    # Customer Memory MCP
    customer_memory_mcp_enabled: bool = True
    customer_memory_ttl: int = 2592000  # 30 days in seconds
    customer_memory_max_interactions: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
