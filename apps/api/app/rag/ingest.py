"""
Document ingestion pipeline.

Reads PDFs/MD from a corpus dir, chunks them, embeds, and writes to the
`documents` table. Run with:
    uv run python scripts/ingest.py --corpus ./corpus/

For Phase 1 we ship a markdown-friendly fallback so you can drop .md files
into the corpus and index them without a paid llama-parse key.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import JSONB

from app.core.logging import get_logger, setup_logging
from app.core.config import get_settings
from app.db.base import dispose_engine, session_scope
from app.models import AuditLog
from app.rag.retriever import get_retriever

log = get_logger("ingest")


@dataclass
class IngestedChunk:
    doc_id: str
    section: str | None
    content: str
    metadata: dict
    embedding: list[float]


def detect_doc_type(path: Path) -> str:
    """Heuristic — folder structure matters more than filename."""
    s = str(path).lower()
    if "sop" in s or "/sops/" in s:
        return "sop"
    if "regulation" in s or "/regulations/" in s or "epa" in s or "iso" in s:
        return "regulation"
    if "price" in s or "/pricing/" in s:
        return "pricing"
    if "method" in s or "/methods/" in s:
        return "method"
    return "general"


def extract_owner(content: str) -> str | None:
    """Try to pull an 'Owner: <name>' line from the doc front-matter."""
    m = re.search(r"(?im)^\s*Owner[:\s]+(.+)$", content)
    return m.group(1).strip() if m else None


def extract_effective_date(content: str) -> datetime | None:
    m = re.search(r"(?im)^\s*Effective(?:\s+date)?[:\s]+(\d{4}-\d{2}-\d{2})", content)
    if not m:
        return None
    try:
        return datetime.fromisoformat(m.group(1)).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def chunk_markdown(text: str, chunk_size: int = 600, overlap: int = 80) -> list[str]:
    """Recursively split on paragraph / sentence / word."""
    paras = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    buf = ""
    for p in paras:
        if len(buf) + len(p) <= chunk_size:
            buf = (buf + "\n\n" + p).strip()
        else:
            if buf:
                chunks.append(buf)
            # If a single paragraph is huge, hard-split it.
            if len(p) > chunk_size:
                for i in range(0, len(p), chunk_size - overlap):
                    chunks.append(p[i : i + chunk_size])
                buf = ""
            else:
                buf = p
    if buf:
        chunks.append(buf)
    return chunks


def load_documents(corpus_dir: Path) -> list[dict]:
    """Read .md / .txt files from the corpus directory tree."""
    out = []
    for path in corpus_dir.rglob("*"):
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        doc_id = path.relative_to(corpus_dir).as_posix()
        content = path.read_text(encoding="utf-8")
        chunks = chunk_markdown(content)
        for i, chunk in enumerate(chunks):
            out.append({
                "chunk_id": f"{doc_id}::chunk-{i:03d}",
                "doc_id": doc_id,
                "section": i if len(chunks) > 1 else None,
                "content": chunk,
                "doc_type": detect_doc_type(path),
                "owner": extract_owner(chunk) or extract_owner(content),
                "effective_date": extract_effective_date(content),
                "metadata": {"source": str(path)},
            })
    log.info("ingest.loaded", count=len(out))
    return out


async def run_ingest(corpus_dir: Path) -> None:
    setup_logging()
    s = get_settings()
    if not s.voyage_api_key:
        raise RuntimeError("VOYAGE_API_KEY required for ingestion.")

    docs = load_documents(corpus_dir)
    if not docs:
        log.warning("ingest.no_docs", corpus=str(corpus_dir))
        return

    retriever = get_retriever()

    async with session_scope() as session:
        # Wipe and rebuild — Phase 1 keeps this simple; Phase 2 adds versioning.
        await session.execute(delete(AuditLog).where(AuditLog.id > 0))
        from sqlalchemy import text as sql_text
        await session.execute(sql_text("DELETE FROM documents"))

        for doc in docs:
            vec = await retriever.embed(doc["content"])
            await session.execute(
                sql_text(
                    """
                    INSERT INTO documents (id, content, embedding, doc_id, doc_type,
                                           effective_date, owner, metadata)
                    VALUES (:id, :content, :embedding, :doc_id, :doc_type,
                            :effective_date, :owner, :metadata)
                    """
                ),
                {
                    "id": doc["chunk_id"],
                    "content": doc["content"],
                    "embedding": vec,
                    "doc_id": doc["doc_id"],
                    "doc_type": doc["doc_type"],
                    "effective_date": doc["effective_date"],
                    "owner": doc["owner"],
                    "metadata": doc["metadata"],
                },
            )

    log.info("ingest.done", count=len(docs))
    await dispose_engine()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", default="./corpus", type=Path)
    args = parser.parse_args()
    asyncio.run(run_ingest(args.corpus))