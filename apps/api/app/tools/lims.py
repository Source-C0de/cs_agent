"""
LIMS-lite tools — wrap our Postgres Sample Tracker as LangChain tools the
worker agents can call. Read-only by default; mutating actions require
explicit HITL.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.base import session_scope
from app.models import Sample, SampleEvent, SampleTest


def _format_event(ev: SampleEvent) -> dict[str, Any]:
    return {
        "ts": ev.ts.isoformat() if ev.ts else None,
        "event_type": ev.event_type,
        "actor": ev.actor,
        "note": (ev.data or {}).get("note"),
    }


@tool
async def get_sample_status(sample_id: str) -> dict[str, Any]:
    """Look up current status, tests, and recent events for a single sample.

    Args:
        sample_id: The Green Lab sample identifier (e.g. GL-2026-0042).

    Returns a dict with status, matrix, tests, and a timeline of events.
    Returns {} if the sample is not found.
    """
    async with session_scope() as s:
        result = await s.execute(
            select(Sample)
            .options(
                selectinload(Sample.tests),
                selectinload(Sample.events),
            )
            .where(Sample.id == sample_id)
        )
        sample = result.scalar_one_or_none()
        if sample is None:
            return {"not_found": True, "sample_id": sample_id}

        return {
            "sample_id": sample.id,
            "customer_id": sample.customer_id,
            "matrix": sample.matrix,
            "container": sample.container,
            "preservation": sample.preservation,
            "collected_at": sample.collected_at.isoformat(),
            "received_at": sample.received_at.isoformat() if sample.received_at else None,
            "status": sample.status,
            "tests": [
                {
                    "code": t.test_code,
                    "tat_requested": t.tat_requested,
                    "analyst_id": t.analyst_id,
                    "started_at": t.started_at.isoformat() if t.started_at else None,
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                }
                for t in sample.tests
            ],
            "timeline": [_format_event(e) for e in sample.events[:5]],
            "queried_at": datetime.now(timezone.utc).isoformat(),
        }


@tool
async def list_recent_reports(customer_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """Return most recently completed reports for a customer.

    Args:
        customer_id: Green Lab customer id (e.g. CUST-0001).
        limit: Max number of reports to return (default 10).
    """
    async with session_scope() as s:
        result = await s.execute(
            select(Sample)
            .join(SampleTest)
            .where(Sample.customer_id == customer_id)
            .where(SampleTest.completed_at.is_not(None))
            .order_by(SampleTest.completed_at.desc())
            .limit(limit)
        )
        samples = result.scalars().all()
        return [
            {
                "sample_id": s.id,
                "matrix": s.matrix,
                "completed_tests": [
                    {"code": t.test_code, "completed_at": t.completed_at.isoformat()
                        if t.completed_at else None}
                    for t in s.tests if t.completed_at
                ],
            }
            for s in samples
        ]


@tool
async def escalate_to_scientist(
    sample_id: str,
    message: str,
) -> dict[str, Any]:
    """Pages the assigned analyst with structured context. ALWAYS requires
    human approval (HITL interrupt) before this tool runs in production.

    In Phase 1 we only emit an audit row + return a draft so we can demonstrate
    the flow without a real LIMS write.

    Args:
        sample_id: Sample the question is about.
        message: Plain-text escalation message to the scientist.

    Returns: dict with escalation_id and routed_to.
    """
    from app.models import SampleEvent
    async with session_scope() as s:
        s.add(
            SampleEvent(
                sample_id=sample_id,
                ts=datetime.now(timezone.utc),
                event_type="escalation",
                actor="agent",
                data={"message": message, "channel": "web"},
            )
        )

    return {
        "escalated": True,
        "sample_id": sample_id,
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "draft_message": message,
    }


ALL_LIMS_TOOLS = [get_sample_status, list_recent_reports, escalate_to_scientist]
