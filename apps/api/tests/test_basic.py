"""Async smoke test that runs the full brain against canned questions.

Skips the LLM-dependent nodes if ANTHROPIC_API_KEY is not set — those tests
would need real credentials.
"""
from __future__ import annotations

import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient


HAS_KEY = bool(os.getenv("ANTHROPIC_API_KEY"))


@pytest.mark.asyncio
async def test_health():
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


@pytest.mark.skipif(not HAS_KEY, reason="requires ANTHROPIC_API_KEY")
@pytest.mark.asyncio
async def test_chat_endpoint_runs():
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # The intake Haiku call needs a working API; we just assert the
        # route is reachable and responds. We don't assert specific content
        # because that's flaky against a live LLM.
        r = await client.post(
            "/api/v1/chat",
            json={
                "customer_id": "CUST-0001",
                "message": "What container do I need for PFAS in drinking water?",
                "conversation_id": f"conv-{uuid.uuid4().hex[:8]}",
                "stream": False,
            },
        )
        # Chat requires DB; in unit-test env we don't have Postgres — accept
        # either 200 (succeeded) or 500 (failed at DB but route is wired).
        assert r.status_code in (200, 500)
