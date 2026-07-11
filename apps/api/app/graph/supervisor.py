"""
LangGraph supervisor — the assembled state machine.

We compile with `PostgresSaver` so every conversation is checkpointed and we
can resume across channel switches and human handoffs.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver  # used for tests / dev only

from app.graph.handoff import human_handoff
from app.graph.intake import intake_router
from app.graph.reflector import compliance_reflector
from app.graph.routing import (
    NODE_FAQ,
    NODE_HUMAN,
    NODE_LIMS,
    NODE_QUOTE,
    NODE_REFLECT,
    NODE_SCHEDULER,
    NODE_TICKET,
    route_after_worker,
    route_by_intent,
)
from app.graph.state import SupportState
from app.graph.workers import faq_node
from app.graph.workers.lims import lims_node, quote_node, ticket_node
from app.graph.workers.scheduler import scheduler_node


def build_graph():
    g = StateGraph(SupportState)

    # Nodes
    g.add_node("intake", intake_router)
    g.add_node(NODE_FAQ, faq_node)
    g.add_node(NODE_LIMS, lims_node)
    g.add_node(NODE_TICKET, ticket_node)
    g.add_node(NODE_QUOTE, quote_node)
    g.add_node(NODE_SCHEDULER, scheduler_node)
    g.add_node(NODE_REFLECT, compliance_reflector)
    g.add_node(NODE_HUMAN, human_handoff)

    # Edges
    g.add_edge(START, "intake")

    g.add_conditional_edges(
        "intake",
        route_by_intent,
        {
            NODE_FAQ: NODE_FAQ,
            NODE_LIMS: NODE_LIMS,
            NODE_TICKET: NODE_TICKET,
            NODE_QUOTE: NODE_QUOTE,
            NODE_SCHEDULER: NODE_SCHEDULER,
            NODE_HUMAN: NODE_HUMAN,
        },
    )

    for worker in [NODE_FAQ, NODE_LIMS, NODE_TICKET, NODE_QUOTE, NODE_SCHEDULER]:
        g.add_conditional_edges(
            worker,
            route_after_worker,
            {NODE_REFLECT: NODE_REFLECT, NODE_HUMAN: NODE_HUMAN},
        )

    g.add_edge(NODE_REFLECT, END)
    g.add_edge(NODE_HUMAN, END)

    # Phase 1: in-memory checkpointer. Swap for PostgresSaver once we have
    # migrations deployed and the connection works in the runtime env.
    checkpointer = MemorySaver()
    return g.compile(checkpointer=checkpointer)


# Singleton instance for the FastAPI app.
_compiled = None


def get_brain():
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled
