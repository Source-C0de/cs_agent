"""Routes package — re-exports the sub-routers.

Webhooks live in their own submodule to avoid the package __init__.py
shadowing the import name.
"""
from app.routes import chat, health
from app.routes.webhooks import router as webhooks_router

__all__ = ["chat", "health", "webhooks_router"]