"""FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.db.base import dispose_engine, get_engine
from app.routes import chat, health, webhooks_router

log = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    log.info(
        "app.start",
        version=__version__,
        env=get_settings().app_env,
        zero_retention=get_settings().anthropic_zero_retention,
    )
    # Eagerly touch the DB so failures show up at boot.
    engine = get_engine()
    try:
        async with engine.connect() as conn:
            await conn.run_sync(lambda s: None)
        log.info("app.db_ok")
    except Exception as exc:
        log.warning("app.db_unavailable_at_boot", error=str(exc))

    yield

    await dispose_engine()
    log.info("app.shutdown")


app = FastAPI(
    title="Green Lab Support",
    description="Customer support agent for Green Lab (lab/research services).",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(webhooks_router, prefix="/api/v1")