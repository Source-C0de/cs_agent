"""
HTTP routes for chat.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.graph import get_brain
from app.graph.state import SupportState
from app.models import AuditLog, Conversation, Message
from app.graph.audit import hash_input, write_audit

router = APIRouter()


class ChatRequest(BaseModel):
    customer_id: str
    message: str
    conversation_id: str | None = None
    stream: bool = True


class Citation(BaseModel):
    doc_id: str
    section: str | None = None
    snippet: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    citations: list[Citation] = Field(default_factory=list)
    requires_human: bool = False
    intent: str | None = None
    confidence: float = 1.0


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    session: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Single-shot synchronous chat endpoint (Phase 1 baseline)."""
    conversation_id = req.conversation_id or f"conv-{uuid.uuid4().hex[:12]}"
    brain = get_brain()

    # Ensure conversation row exists.
    conv = await session.get(Conversation, conversation_id)
    if conv is None:
        conv = Conversation(
            id=conversation_id,
            customer_id=req.customer_id,
            channel="web",
        )
        session.add(conv)
        await session.flush()

    state = SupportState(
        customer_id=req.customer_id,
        conversation_id=conversation_id,
        channel="web",
        messages=[{"role": "user", "content": req.message}],
    )

    config = {"configurable": {"thread_id": conversation_id}}
    final = await brain.ainvoke(state.model_dump(), config=config)

    reply = final.get("draft_reply") or "(no response)"
    citations = [
        Citation(
            doc_id=c.get("doc_id"),
            section=c.get("section"),
            snippet=c.get("snippet"),
        )
        for c in (final.get("retrieved_docs") or [])
    ]

    # Persist messages + audit log.
    session.add(Message(
        conversation_id=conversation_id,
        role="user",
        content=req.message,
        channel="web",
    ))
    session.add(Message(
        conversation_id=conversation_id,
        role="assistant",
        content=reply,
        tool_calls=final.get("tool_calls") or [],
        retrieved_docs=final.get("retrieved_docs") or [],
        confidence=final.get("confidence"),
        channel="web",
    ))
    if final.get("requires_human"):
        conv.escalated_to_human = True

    await write_audit(
        session,
        node="chat.endpoint",
        decision="reply",
        input_payload={"customer_id": req.customer_id,
                       "conversation_id": conversation_id,
                       "message_hash": hash_input(req.message)},
        summary=reply[:200],
        customer_id=req.customer_id,
        conversation_id=conversation_id,
    )
    await session.commit()

    return ChatResponse(
        conversation_id=conversation_id,
        reply=reply,
        citations=citations,
        requires_human=final.get("requires_human", False),
        intent=final.get("intent"),
        confidence=final.get("confidence", 1.0),
    )


@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Server-Sent Events stream. We simulate token streaming by yielding chunks
    of the final draft reply — LangGraph itself doesn't expose partial tokens
    without per-node streaming; Phase 1 ships a token-batched stream that gives
    the UX a 'typing' feel.
    """

    async def event_generator():
        conversation_id = req.conversation_id or f"conv-{uuid.uuid4().hex[:12]}"

        # Ensure conversation row exists.
        conv = await session.get(Conversation, conversation_id)
        if conv is None:
            conv = Conversation(
                id=conversation_id,
                customer_id=req.customer_id,
                channel="web",
            )
            session.add(conv)
            await session.flush()

        brain = get_brain()
        state = SupportState(
            customer_id=req.customer_id,
            conversation_id=conversation_id,
            channel="web",
            messages=[{"role": "user", "content": req.message}],
        )

        config = {"configurable": {"thread_id": conversation_id}}
        try:
            final = await brain.ainvoke(state.model_dump(), config=config)
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"
            return

        reply = final.get("draft_reply") or "(no response)"
        # Yield in ~5 word chunks for a typing feel.
        words = reply.split(" ")
        for i, word in enumerate(words + [""]):
            chunk = (word + " ").strip() + " "
            yield f"event: token\ndata: {json.dumps({'token': chunk})}\n\n"
            await asyncio.sleep(0.02)

        yield f"event: done\ndata: {json.dumps({
            'conversation_id': conversation_id,
            'requires_human': final.get('requires_human', False),
            'intent': final.get('intent'),
            'citations': final.get('retrieved_docs') or [],
        })}\n\n"

        # Persist (in background — fire and forget)
        try:
            session.add(Message(
                conversation_id=conversation_id,
                role="user",
                content=req.message,
                channel="web",
            ))
            session.add(Message(
                conversation_id=conversation_id,
                role="assistant",
                content=reply,
                tool_calls=final.get("tool_calls") or [],
                retrieved_docs=final.get("retrieved_docs") or [],
                confidence=final.get("confidence"),
                channel="web",
            ))
            if final.get("requires_human"):
                conv.escalated_to_human = True
            await write_audit(
                session,
                node="chat.stream",
                decision="stream_reply",
                input_payload={"customer_id": req.customer_id,
                               "conversation_id": conversation_id,
                               "message_hash": hash_input(req.message)},
                summary=reply[:200],
                customer_id=req.customer_id,
                conversation_id=conversation_id,
            )
            await session.commit()
        except Exception:
            await session.rollback()

    return StreamingResponse(event_generator(), media_type="text/event-stream")