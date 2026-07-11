"""LIMS worker — looks up sample status and recent reports using our tools."""
from __future__ import annotations

import json
from typing import Any

from app.core.llm import brain_model, complete
from app.core.logging import get_logger
from app.graph.audit import timed_node
from app.graph.state import SupportState
from app.tools.lims import get_sample_status, list_recent_reports

log = get_logger("worker.lims")

LIMS_SYSTEM = """You are Green Lab's LIMS assistant. The user is asking about a sample
or recent reports. You have these tools:

- get_sample_status(sample_id: str)
- list_recent_reports(customer_id: str, limit: int = 10)

Always cite sample IDs and dates exactly as returned. If the user has not
provided a sample ID or customer ID, ask for it politely — do not guess."""


async def lims_node(state: SupportState) -> dict[str, Any]:
    with timed_node("lims"):
        query = next(
            (m["content"] for m in reversed(state.messages) if m["role"] == "user"),
            "",
        )

        # Cheap intent: is the user mentioning a sample ID?
        import re
        sample_match = re.search(r"\bGL-\d{4}-\d{4}\b", query, re.I)

        if sample_match:
            sample_id = sample_match.group(0).upper()
            tool_result = await get_sample_status.ainvoke({"sample_id": sample_id})
            tool_calls = [{
                "tool": "get_sample_status",
                "args": {"sample_id": sample_id},
                "result": tool_result,
            }]

            if tool_result.get("not_found"):
                return {
                    "draft_reply": (
                        f"I couldn't find sample {sample_id} in our system. "
                        "Could you double-check the ID? It usually looks like "
                        "GL-2026-0042."
                    ),
                    "tool_calls": tool_calls,
                    "requires_human": False,
                }

            pretty = json.dumps(tool_result, indent=2, default=str)
            prompt = (
                f"User asked: {query}\n\n"
                f"Tool result:\n{pretty}\n\n"
                "Summarise the sample's current status, recent events, and any "
                "actions the user might need to take. Be concise."
            )
            resp = await complete(
                system=LIMS_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
            )
            return {
                "draft_reply": resp.content[0].text if resp.content else "(no answer)",
                "tool_calls": tool_calls,
                "confidence": 0.85,
            }

        # No sample ID — ask for one. We do NOT call list_recent_reports
        # unless the user has explicitly identified themselves.
        return {
            "draft_reply": (
                "Sure — could you share the sample ID (it looks like "
                "GL-2026-0042) so I can pull up its status?"
            ),
            "requires_human": False,
        }


async def ticket_node(state: SupportState) -> dict[str, Any]:
    """Phase 2 stub — surfaces a message that we'll wire up Zendesk later."""
    return {
        "draft_reply": (
            "I can look that up for you — but ticket integration is on the "
            "Phase 2 roadmap. For now I'll escalate this to a Green Lab team "
            "member."
        ),
        "requires_human": True,
        "escalation_reason": "Ticket integration pending",
    }


async def quote_node(state: SupportState) -> dict[str, Any]:
    """RAG-flavoured pricing lookup. Phase 2 swaps in real price-list engine."""
    return {
        "draft_reply": (
            "Here's the current pricing from our service catalog:\n\n"
            "(Phase 1: I retrieve from the pricing corpus — see citations. "
            "Phase 2 will wire the dynamic price-list engine.)"
        ),
        "requires_human": False,
    }