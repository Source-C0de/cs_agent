"""ORM models for Green Lab's LIMS-lite schema."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # CUST-0001
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    tier: Mapped[str] = mapped_column(String, default="standard")  # academic, contract, ...
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    samples: Mapped[list["Sample"]] = relationship(back_populates="customer")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="customer")


class Sample(Base):
    __tablename__ = "samples"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # GL-2026-0001
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    matrix: Mapped[str] = mapped_column(String)  # groundwater, soil, serum, ...
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, default="received", index=True)
    container: Mapped[str | None] = mapped_column(String, nullable=True)
    preservation: Mapped[str | None] = mapped_column(String, nullable=True)
    chain_of_custody_doc: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    customer: Mapped[Customer] = relationship(back_populates="samples")
    tests: Mapped[list["SampleTest"]] = relationship(
        back_populates="sample", cascade="all, delete-orphan"
    )
    events: Mapped[list["SampleEvent"]] = relationship(
        back_populates="sample",
        cascade="all, delete-orphan",
        order_by="SampleEvent.ts.desc()",
    )


class SampleTest(Base):
    __tablename__ = "sample_tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sample_id: Mapped[str] = mapped_column(ForeignKey("samples.id"), index=True)
    test_code: Mapped[str] = mapped_column(String)  # PFAS-537, METALS-ICPMS-6020B, ...
    tat_requested: Mapped[str] = mapped_column(String, default="standard")
    price_cents: Mapped[int] = mapped_column(Integer, default=0)
    analyst_id: Mapped[str | None] = mapped_column(String, nullable=True)
    result_doc: Mapped[str | None] = mapped_column(String, nullable=True)  # R2 object key
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sample: Mapped[Sample] = relationship(back_populates="tests")


class SampleEvent(Base):
    """Append-only event log per sample — drives the customer-visible timeline."""

    __tablename__ = "sample_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sample_id: Mapped[str] = mapped_column(ForeignKey("samples.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    event_type: Mapped[str] = mapped_column(String)  # received, logged, ...
    actor: Mapped[str] = mapped_column(String)  # system, user_id, agent
    data: Mapped[dict] = mapped_column(JSONB, default=dict)

    sample: Mapped[Sample] = relationship(back_populates="events")


class Conversation(Base):
    """Per-customer conversation thread (channel agnostic)."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # UUID
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    channel: Mapped[str] = mapped_column(String)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    escalated_to_human: Mapped[bool] = mapped_column(Boolean, default=False)
    closed: Mapped[bool] = mapped_column(Boolean, default=False)

    customer: Mapped[Customer] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.ts"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String)  # user, assistant, tool
    content: Mapped[str] = mapped_column(Text)
    # Tool-call metadata; JSON-encoded for portability.
    tool_calls: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    retrieved_docs: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    channel: Mapped[str] = mapped_column(String, default="web")
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class AuditLog(Base):
    """
    HIPAA-grade audit trail.

    One row per agent decision. Stores the *hashed* input so we can prove
    what the agent saw without re-exposing PHI in backups.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    customer_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    node: Mapped[str] = mapped_column(String)  # which LangGraph node ran
    decision: Mapped[str] = mapped_column(String)  # tool call, escalate, reply
    # Hash of input — lets audits verify reproducibility without storing PHI.
    input_hash: Mapped[str] = mapped_column(String(64))
    # Optional redacted summary; may be null for sensitive flows.
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


__all__ = [
    "Customer",
    "Sample",
    "SampleTest",
    "SampleEvent",
    "Conversation",
    "Message",
    "AuditLog",
]
