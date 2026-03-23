"""Configuration: SK_API_URL is the only required setting."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_api_base(url: str) -> str:
    u = url.rstrip("/")
    if u.endswith("/api"):
        return u
    return f"{u}/api"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    sk_api_url: str = Field(validation_alias="SK_API_URL")

    reference_cache_ttl_seconds: int = Field(
        default=3600,
        validation_alias="REFERENCE_CACHE_TTL_SECONDS",
    )
    http_timeout_s: float = Field(default=30.0, validation_alias="HTTP_TIMEOUT_S")
    http_max_retries: int = Field(default=2, validation_alias="HTTP_MAX_RETRIES")

    host: str = Field(default="0.0.0.0", validation_alias="MCP_HOST")
    port: int = Field(default=8083, validation_alias="MCP_PORT")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    # When false (default), mcp + uvicorn access logs are WARNING to avoid spam from Cursor polling ListTools/ListPrompts/ListResources.
    mcp_verbose_logs: bool = Field(default=False, validation_alias="MCP_VERBOSE_LOGS")

    @property
    def api_base(self) -> str:
        return _normalize_api_base(self.sk_api_url)
