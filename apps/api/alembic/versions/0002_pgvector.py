"""pgvector docs table

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-10
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documents",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", Vector(1024), nullable=False),  # voyage-3-large = 1024 dims
        sa.Column("doc_id", sa.String, nullable=False, index=True),
        sa.Column("doc_type", sa.String, nullable=True, index=True),
        sa.Column("effective_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner", sa.String, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    # HNSW index for fast ANN search (better than IVFFlat for small datasets too).
    op.execute(
        "CREATE INDEX ix_documents_embedding ON documents USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_table("documents")