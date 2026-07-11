"""
Audit log helper — invoked by every LangGraph node so we have a per-decision
audit trail for HIPAA / SOC 2.

We hash inputs (SHA-256) so audits can verify reproducibility without ever
storing PHI in the audit table itself.
"""
from __future__ import annotations

import hashlib
import json
import time
from contextlib import contextmanager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import AuditLog

log = get_logger("audit")


def hash_input(payload: Any) -> str:
    """SHA-256 of a JSON-serialised payload. Stable, fast, PHI-free."""
    s = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


@contextmanager
def timed_node(node_name: str):
    """Lightweight timing context for the latency_ms column."""
    start = time.perf_counter()
    yield
    duration_ms = int((time.perf_counter() - start) * 1000)
    log.info("node.complete", node=node_name, latency_ms=duration_ms)


async def write_audit(
    session: AsyncSession,
    *,
    node: str,
    decision: str,
    input_payload: Any,
    summary: str | None = None,
    customer_id: str | None = None,
    conversation_id: str | None = None,
    model: str | None = None,
    latency_ms: int | None = None,
) -> None:
    """Persist one audit row. Caller is responsible for the session transaction."""
    session.add(
        AuditLog(
            node=node,
            decision=decision,
            input_hash=hash_input(input_payload),
            summary=summary,
            customer_id=customer_id,
            conversation_id=conversation_id,
            model=model,
            latency_ms=latency_ms,
        )
    )