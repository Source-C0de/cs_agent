"""
LangGraph state schema for the support brain.

Every conversation produces one state instance. The Postgres checkpointer keys
on `(customer_id, conversation_id)` so we can resume across channel switches.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class RetrievedDoc(BaseModel):
    """One chunk retrieved by the RAG pipeline."""
    doc_id: str
    section: str | None = None
    snippet: str
    score: float = 1.0
    source_url: str | None = None


class ToolCall(BaseModel):
    """A single LLM-initiated tool invocation."""
    tool: str
    args: dict[str, Any]
    result: Any | None = None
    latency_ms: int | None = None


class SupportState(BaseModel):
    # Identity
    customer_id: str
    conversation_id: str
    channel: Literal["web", "email", "whatsapp", "voice", "sms"] = "web"

    # Conversation
    # IMPORTANT: `messages` uses LangGraph's reducer that *appends*.
    messages: Annotated[list[dict[str, Any]], add_messages] = Field(default_factory=list)

    # Routing
    intent: str | None = None
    autonomy_tier: Literal["tier1", "tier2", "tier3", "tier4"] = "tier1"
    requires_human: bool = False
    escalation_reason: str | None = None

    # Retrieval
    retrieved_docs: list[RetrievedDoc] = Field(default_factory=list)

    # Tool traces
    tool_calls: list[ToolCall] = Field(default_factory=list)

    # Output
    draft_reply: str | None = None
    citations: list[str] = Field(default_factory=list)
    confidence: float = 1.0

    # Operational
    pii_redacted: bool = False
    human_handoff_started: bool = False
    error: str | None = None

    # PII tagging — pre-NER tokens we drop before logging.
    has_phi: bool = False
