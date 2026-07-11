"""
LangSmith wiring.

We don't import langchain_core.callbacks in app code; just set env vars and
LangChain/LangGraph auto-trace. This module keeps it in one place so the
config is auditable.
"""
from __future__ import annotations

import os

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("observability")


def configure_langsmith() -> None:
    """Idempotently set LangSmith env vars from settings."""
    s = get_settings()
    if not s.langchain_tracing_v2:
        log.info("langsmith.disabled")
        return

    if not s.langchain_api_key:
        log.warning("langsmith.enabled_but_no_api_key")
        return

    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ["LANGCHAIN_API_KEY"] = s.langchain_api_key.get_secret_value()
    os.environ["LANGCHAIN_PROJECT"] = s.langchain_project
    os.environ["LANGCHAIN_ENDPOINT"] = s.langchain_endpoint
    log.info("langsmith.configured", project=s.langchain_project)
