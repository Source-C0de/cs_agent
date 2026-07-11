"""
Human handoff — pauses the LangGraph run for a human reviewer.

In Phase 1 this writes a hard-coded response + an internal "handoff" message
log so we can integrate with Zendesk in Phase 2. Real production would use
LangGraph `interrupt()` to block and a separate "/human/review" endpoint to
resume.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.graph.audit import timed_node
from app.graph.state import SupportState


async def human_handoff(state: SupportState) -> dict[str, Any]:
    with timed_node("human_handoff"):
        reason = state.escalation_reason or "unspecified"

        # Phase 2 will:
        #  - Create a Zendesk ticket
        #  - Send an internal Slack alert
        #  - PagerDuty if after-hours
        message = (
            f"Thanks — I've flagged this for a Green Lab scientist to follow up on. "
            f"They'll reach out within one business day. (Reason: {reason})"
        )
        return {
            "draft_reply": message,
            "human_handoff_started": True,
            "requires_human": True,
            "tool_calls": list(state.tool_calls) + [{
                "tool": "human_handoff",
                "args": {"reason": reason},
                "result": {"queued_at": datetime.now(timezone.utc).isoformat()},
            }],
        }
