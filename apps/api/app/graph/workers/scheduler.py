"""Scheduler worker — proposes slots, books after user confirmation."""
from __future__ import annotations

from typing import Any

from app.core.llm import brain_model, complete
from app.graph.audit import timed_node
from app.graph.state import SupportState
from app.tools.scheduler import book_consultation, propose_consultation


async def scheduler_node(state: SupportState) -> dict[str, Any]:
    with timed_node("scheduler"):
        last = state.messages[-1]["content"] if state.messages else ""

        # If the user has just confirmed one of the proposed slots, book it.
        # Otherwise, propose slots.
        if not any("slot-" in (m.get("content") or "") for m in state.messages):
            proposed = await propose_consultation.ainvoke({
                "topic": "Consultation (topic detected by LLM in production)",
                "preferred_window": "this week",
            })
            options = proposed.get("options", [])
            return {
                "draft_reply": (
                    "Here are 3 times that work for our team:\n\n"
                    + "\n".join(
                        f"- {o['start']}  ({o['slot_id']})"
                        for o in options
                    )
                    + "\n\nReply with the slot ID to confirm."
                ),
                "tool_calls": [{"tool": "propose_consultation",
                                "args": {"topic": "consultation",
                                         "preferred_window": "this week"},
                                "result": proposed}],
                "confidence": 0.95,
            }

        # Look for a slot ID in the latest user message.
        import re
        match = re.search(r"\bslot-\d{14}\b", last)
        if not match:
            return {
                "draft_reply": (
                    "I couldn't find a slot ID in your reply. Please copy the "
                    "exact slot ID from the previous message."
                ),
                "requires_human": False,
            }

        booked = await book_consultation.ainvoke({
            "slot_id": match.group(0),
            "customer_id": state.customer_id,
        })
        if booked.get("error"):
            return {
                "draft_reply": f"Sorry — {booked['error']}. Want me to propose new slots?",
                "tool_calls": [{"tool": "book_consultation",
                                "args": {"slot_id": match.group(0)},
                                "result": booked}],
            }
        return {
            "draft_reply": (
                f"All booked! Confirmation: {booked['slot']['slot_id']} at "
                f"{booked['slot']['start']}. You'll receive an email with the "
                f"calendar invite shortly."
            ),
            "tool_calls": [{"tool": "book_consultation",
                            "args": {"slot_id": match.group(0),
                                     "customer_id": state.customer_id},
                            "result": booked}],
            "confidence": 0.99,
        }
