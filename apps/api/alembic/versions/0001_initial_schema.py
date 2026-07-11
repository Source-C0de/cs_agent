"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-10
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")  # for gen_random_uuid()

    op.create_table(
        "customers",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("email", sa.String, nullable=True),
        sa.Column("phone", sa.String, nullable=True),
        sa.Column("tier", sa.String, nullable=False, server_default="standard"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_customers_email", "customers", ["email"])
    op.create_index("ix_customers_phone", "customers", ["phone"])

    op.create_table(
        "samples",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("customer_id", sa.String, sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("matrix", sa.String, nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String, nullable=False, server_default="received"),
        sa.Column("container", sa.String, nullable=True),
        sa.Column("preservation", sa.String, nullable=True),
        sa.Column("chain_of_custody_doc", sa.String, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_samples_customer_id", "samples", ["customer_id"])
    op.create_index("ix_samples_status", "samples", ["status"])

    op.create_table(
        "sample_tests",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("sample_id", sa.String, sa.ForeignKey("samples.id"), nullable=False),
        sa.Column("test_code", sa.String, nullable=False),
        sa.Column("tat_requested", sa.String, nullable=False, server_default="standard"),
        sa.Column("price_cents", sa.Integer, nullable=False, server_default=0),
        sa.Column("analyst_id", sa.String, nullable=True),
        sa.Column("result_doc", sa.String, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sample_tests_sample_id", "sample_tests", ["sample_id"])

    op.create_table(
        "sample_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("sample_id", sa.String, sa.ForeignKey("samples.id"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("event_type", sa.String, nullable=False),
        sa.Column("actor", sa.String, nullable=False),
        sa.Column("data", postgresql.JSONB, nullable=False, server_default="{}"),
    )
    op.create_index("ix_sample_events_sample_id", "sample_events", ["sample_id"])

    op.create_table(
        "conversations",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("customer_id", sa.String, sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("channel", sa.String, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_message_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("escalated_to_human", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("closed", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_conversations_customer_id", "conversations", ["customer_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("conversation_id", sa.String, sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("role", sa.String, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("tool_calls", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("retrieved_docs", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("channel", sa.String, nullable=False, server_default="web"),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("customer_id", sa.String, nullable=True),
        sa.Column("conversation_id", sa.String, nullable=True),
        sa.Column("node", sa.String, nullable=False),
        sa.Column("decision", sa.String, nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("model", sa.String, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
    )
    op.create_index("ix_audit_logs_customer_id", "audit_logs", ["customer_id"])
    op.create_index("ix_audit_logs_conversation_id", "audit_logs", ["conversation_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("sample_events")
    op.drop_table("sample_tests")
    op.drop_table("samples")
    op.drop_table("customers")
