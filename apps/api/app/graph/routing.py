"""
Routing table — maps intake classification to LangGraph worker nodes.
"""
from __future__ import annotations

from app.core.pii import ALWAYS_ESCALATE_INTENTS, Intent
from app.graph.state import SupportState

# Node name constants — referenced by graph.supervisor too.
NODE_INTAKE = "intake"
NODE_FAQ = "faq"
NODE_LIMS = "lims"
NODE_TICKET = "ticket"
NODE_QUOTE = "quote"
NODE_SCHEDULER = "scheduler"
NODE_REFLECT = "reflect"
NODE_HUMAN = "human_handoff"
NODE_END = "__end__"

# Intent -> worker node
INTENT_TO_WORKER: dict[str, str] = {
    Intent.FAQ.value: NODE_FAQ,
    Intent.PRICING.value: NODE_FAQ,  # pricing uses RAG + price-list lookup
    Intent.SAMPLE_STATUS.value: NODE_LIMS,
    Intent.TICKET_STATUS.value: NODE_TICKET,
    Intent.QUOTE_REQUEST.value: NODE_QUOTE,
    Intent.CONSULTATION_BOOKING.value: NODE_SCHEDULER,
    Intent.RESULTS_INTERPRETATION.value: NODE_HUMAN,
    Intent.COMPLAINT.value: NODE_HUMAN,
    Intent.UNCLEAR.value: NODE_FAQ,  # default to RAG; reflector will catch low confidence
}


def route_by_intent(state: SupportState) -> str:
    """Conditional edge: pick the next node."""
    # Hard safety floor
    if state.requires_human or state.intent in {i.value for i in ALWAYS_ESCALATE_INTENTS}:
        return NODE_HUMAN
    if state.autonomy_tier in ("tier3", "tier4"):
        return NODE_HUMAN

    return INTENT_TO_WORKER.get(state.intent or "unclear", NODE_FAQ)


def route_after_worker(state: SupportState) -> str:
    """All workers go through the compliance reflector before finalising."""
    if state.requires_human:
        return NODE_HUMAN
    return NODE_REFLECT