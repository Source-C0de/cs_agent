"""Health + readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from app import __version__

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router.get("/ready")
async def ready() -> dict[str, str]:
    # A real impl pings Postgres / Redis / LangSmith here.
    return {"status": "ready"}