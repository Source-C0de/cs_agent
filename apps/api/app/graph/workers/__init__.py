"""LangGraph worker nodes — one per route the supervisor can dispatch to."""
from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from app.core.llm import brain_model, complete
from app.core.logging import get_logger
from app.graph.audit import timed_node
from app.graph.state import SupportState
from app.rag import get_retriever
from app.db.base import session_scope

log = get_logger("workers")

FAQ_SYSTEM = """You are Green Lab Support. Answer the user's question using ONLY the
retrieved context below. Cite sources inline as [source: <doc-id>] immediately
after each fact. If the context doesn't contain the answer, say:

"I don't have that information in the current documentation. Let me escalate
this to a Green Lab scientist."

Do NOT invent sample IDs, prices, dates, or test results."""


async def faq_node(state: SupportState) -> dict[str, Any]:
    """RAG-only worker. No tool calls beyond retrieval."""
    with timed_node("faq"):
        query = next(
            (m["content"] for m in reversed(state.messages) if m["role"] == "user"),
            "",
        )

        retriever = get_retriever()
        async with session_scope() as session:
            hits = await retriever.retrieve(session, query, top_k=6)

        if not hits:
            return {
                "draft_reply": (
                    "I don't have that information in the current documentation. "
                    "Let me escalate this to a Green Lab scientist who can help. "
                    "Would you like me to open a ticket?"
                ),
                "retrieved_docs": [],
                "requires_human": True,
                "escalation_reason": "No matching documentation",
            }

        context = "\n\n---\n\n".join(
            f"[{h.doc_id}#{h.section}]\n{h.snippet}" for h in hits
        )

        prompt = (
            f"User question:\n{query}\n\n"
            f"Retrieved context:\n{context}\n\n"
            "Answer succinctly. Cite [source: <doc-id>] after each fact."
        )

        resp = await complete(
            system=FAQ_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.1,
        )
        answer = resp.content[0].text if resp.content else "(no answer)"

        return {
            "draft_reply": answer,
            "retrieved_docs": [
                {"doc_id": h.doc_id, "section": h.section, "snippet": h.snippet,
                 "score": h.score}
                for h in hits
            ],
            "citations": [f"{h.doc_id}#{h.section}" for h in hits],
            "confidence": 0.8,
        }
