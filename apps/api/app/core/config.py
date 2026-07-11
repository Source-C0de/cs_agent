"""
Application configuration (env-driven, fails closed).

All secrets come from env. The app refuses to start in production if critical
HIPAA-grade flags are missing.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised, typed application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- App ----
    app_env: Literal["development", "staging", "production"] = "development"
    app_log_level: str = "INFO"
    app_pii_redaction: bool = True
    app_audit_retention_days: int = 2555  # 7 years (HIPAA §164.530(j)(2))

    # ---- Database ----
    database_url: str = Field(
        default="postgresql+asyncpg://greenlab:greenlab@localhost:5432/greenlab",
        description="Async SQLAlchemy URL.",
    )
    redis_url: str = "redis://localhost:6379/0"

    # ---- LLM providers ----
    anthropic_api_key: SecretStr | None = None
    anthropic_brain_model: str = "claude-sonnet-4-5"
    anthropic_router_model: str = "claude-haiku-4-5"
    anthropic_zero_retention: bool = True

    openai_api_key: SecretStr | None = None
    openai_fallback_model: str = "gpt-4.1-mini"

    voyage_api_key: SecretStr | None = None
    cohere_api_key: SecretStr | None = None

    # ---- Observability ----
    langchain_tracing_v2: bool = False
    langchain_api_key: SecretStr | None = None
    langchain_project: str = "green-lab-support"
    langchain_endpoint: str = "https://api.smith.langchain.com"

    # ---- Vector store ----
    docs_collection: str = "green_lab_docs"

    # ---- HIPAA posture ----
    require_human_tiers: list[str] = Field(
        default_factory=lambda: ["tier3", "tier4"],
        description="Autonomy tiers that ALWAYS escalate to a human.",
    )

    @field_validator("anthropic_zero_retention")
    @classmethod
    def _check_hipaa_flags_in_production(cls, v: bool, info) -> bool:  # type: ignore[no-untyped-def]
        """Block production deploy if zero-retention is off."""
        env = info.data.get("app_env", "development")
        if env == "production" and not v:
            raise ValueError(
                "ANTHROPIC_ZERO_RETENTION=false in production is not allowed. "
                "Green Lab processes clinical data and must use zero-retention tier."
            )
        return v

    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor (overridable in tests)."""
    return Settings()  # type: ignore[call-arg]
