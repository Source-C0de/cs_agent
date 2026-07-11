"""Stub — channel-specific webhooks (email, WhatsApp, voice). Phase 2 will fill these in."""
from fastapi import APIRouter

router = APIRouter(prefix="/webhooks")


@router.post("/postmark/inbound")
async def postmark_inbound():
    """Phase 2 will accept inbound emails and dispatch them to the agent."""
    return {"status": "not_implemented", "channel": "email"}


@router.post("/whatsapp/inbound")
async def whatsapp_inbound():
    return {"status": "not_implemented", "channel": "whatsapp"}


@router.post("/vapi/inbound")
async def vapi_inbound():
    return {"status": "not_implemented", "channel": "voice"}