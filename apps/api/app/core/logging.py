"""
Structured logging with optional PII redaction (HIPAA).

- structlog for JSON logs.
- PII redactor using Presidio *only when enabled* (it's a 700MB spacy
  download). In dev, we run a regex-only path.
- The full Presidio pipeline runs in production only.
"""
from __future__ import annotations

import logging
import re
import sys
from typing import Any

import structlog

from app.core.config import get_settings

# ---------- regex fallback (fast, no model downloads) ----------
_REGEX_PATTERNS = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED-SSN]"),
    (re.compile(r"\b\d{16}\b"), "[REDACTED-CC]"),
    (re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"), "[REDACTED-EMAIL]"),
    (re.compile(r"\b\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}\b"), "[REDACTED-PHONE]"),
    (re.compile(r"\b(?:GL|CUST)[-_]?\d{2,4}-?\d{3,5}\b", re.I), "[REDACTED-ID]"),
    (re.compile(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b"), "[REDACTED-NAME]"),  # very rough
]

_PRESIDIO_ANALYZER = None


def _scrub_text(text: str) -> str:
    if not text:
        return text
    out = text
    for pat, repl in _REGEX_PATTERNS:
        out = pat.sub(repl, out)
    return out


def _scrub_presidio(text: str) -> str:
    """Heavy path — requires spacy model. Production only."""
    global _PRESIDIO_ANALYZER
    if _PRESIDIO_ANALYZER is None:
        from presidio_analyzer import AnalyzerEngine
        _PRESIDIO_ANALYZER = AnalyzerEngine()
    results = _PRESIDIO_ANALYZER.analyze(
        text=text, language="en",
        entities=["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS",
                  "US_SSN", "CREDIT_CARD", "MEDICAL_LICENSE",
                  "US_DRIVER_LICENSE", "DATE_TIME"],
    )
    if not results:
        return text
    from presidio_anonymizer import AnonymizerEngine
    return AnonymizerEngine().anonymize(text=text, analyzer_results=results).text


def _redact(value: Any) -> Any:
    """Scrub PHI from a value. Recurses into dicts/lists. Idempotent."""
    settings = get_settings()
    if not settings.app_pii_redaction:
        return value

    if isinstance(value, str):
        # Use presidio in production; regex-only in dev/staging.
        if settings.is_production():
            return _scrub_presidio(value)
        return _scrub_text(value)

    if isinstance(value, dict):
        return {k: _redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_redact(v) for v in value)
    return value


def _redacting_processor(_logger, _name, event_dict):
    """structlog processor: scrub PHI from every log line before emission."""
    for k, v in list(event_dict.items()):
        event_dict[k] = _redact(v)
    return event_dict


def setup_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.app_log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(message)s",
        stream=sys.stdout,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _redacting_processor,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None):
    return structlog.get_logger(name or "green_lab")