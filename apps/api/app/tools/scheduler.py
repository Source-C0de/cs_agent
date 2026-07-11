"""
Scheduling tools — Phase 1 uses a fake Cal.com stub. Phase 3 will swap in
the real Cal.com client behind the same interfaces.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from langchain_core.tools import tool

# In-memory fake calendar so the agent can demonstrate booking without
# a real Cal.com account. Replace with `CalComClient` in Phase 3.
_FAKE_EVENTS: list[dict] = []


@tool
async def propose_consultation(
    topic: str,
    preferred_window: str,
) -> dict:
    """Propose three 30-min slots with a SME for a customer consultation.

    Args:
        topic: Brief topic (e.g. "PFAS method selection").
        preferred_window: Free-text preferred time (e.g. "next Tuesday morning").

    Returns a dict with `options`: list of 3 slots with `slot_id`, `start`, `end`.
    """
    base = datetime.now(timezone.utc) + timedelta(days=1)
    options = []
    for n in range(3):
        start = base + timedelta(days=n * 2, hours=random.randint(9, 15))
        end = start + timedelta(minutes=30)
        slot = {
            "slot_id": f"slot-{start.strftime('%Y%m%d%H%M')}",
            "topic": topic,
            "start": start.isoformat(),
            "end": end.isoformat(),
        }
        _FAKE_EVENTS.append(slot)
        options.append(slot)
    return {"awaiting_confirmation": True, "options": options}


@tool
async def book_consultation(slot_id: str, customer_id: str) -> dict:
    """Actually books a previously proposed slot.

    Args:
        slot_id: The slot id returned by `propose_consultation`.
        customer_id: Green Lab customer id.

    Returns confirmation, or an error if slot already taken.
    """
    slot = next((s for s in _FAKE_EVENTS if s["slot_id"] == slot_id), None)
    if slot is None:
        return {"error": f"slot {slot_id} not found"}
    if slot.get("booked_by"):
        return {"error": "slot already booked", "booked_by": slot["booked_by"]}
    slot["booked_by"] = customer_id
    slot["booked_at"] = datetime.now(timezone.utc).isoformat()
    return {"confirmed": True, "slot": slot}


ALL_SCHEDULER_TOOLS = [propose_consultation, book_consultation]
