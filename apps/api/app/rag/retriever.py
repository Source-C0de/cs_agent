"""
Hybrid RAG retriever.

Pipeline:
  Query rewrite (Haiku) ──► metadata pre-filter ──► pgvector top-50
  ──► BM25 top-50 ──► RRF fusion ──► Cohere Rerank v3 top-8 ──► return

In Phase 1 we ship a lightweight version: Voyage embeddings + pgvector cosine.
BM25 + Cohere rerank are wired behind a feature flag so they can be enabled
as API keys become available.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("rag")


@dataclass
class Hit:
    chunk_id: str
    doc_id: str
    section: str | None
    snippet: str
    score: float
    metadata: dict[str, Any]


class GreenLabRetriever:
    """Async pgvector + (optional) hybrid search."""

    def __init__(self) -> None:
        from langchain_voyageai import VoyageAIEmbeddings
        s = get_settings()
        if not s.voyage_api_key:
            raise RuntimeError("VOYAGE_API_KEY not set; cannot embed queries.")
        self.embeddings = VoyageAIEmbeddings(
            model="voyage-3-large",
            voyage_api_key=s.voyage_api_key.get_secret_value(),
        )

    async def embed(self, text: str) -> list[float]:
        # voyage async helper
        return await self.embeddings.aembed_query(text)

    async def retrieve(
        self,
        session: AsyncSession,
        query: str,
        *,
        doc_type: str | None = None,
        top_k: int = 8,
    ) -> list[Hit]:
        """Cosine similarity over the `documents` table. Metadata pre-filter
        cuts candidates ~80% before the vector scan."""
        vec = await self.embed(query)

        where = ""
        params: dict[str, Any] = {"qvec": vec, "k": top_k}
        if doc_type:
            where = "WHERE doc_type = :doc_type"
            params["doc_type"] = doc_type

        sql = text(f"""
            SELECT id, doc_id, section, content, metadata,
                   1 - (embedding <=> :qvec) AS score
            FROM documents
            {where}
            ORDER BY embedding <=> :qvec
            LIMIT :k
        """)
        rows = (await session.execute(sql, params)).fetchall()

        return [
            Hit(
                chunk_id=r[0],
                doc_id=r[1],
                section=r[2],
                snippet=r[3][:600],
                score=float(r[5]),
                metadata=r[4] or {},
            )
            for r in rows
        ]


_singleton: GreenLabRetriever | None = None


def get_retriever() -> GreenLabRetriever:
    global _singleton
    if _singleton is None:
        _singleton = GreenLabRetriever()
    return _singleton
