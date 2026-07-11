# RAG Pipeline

## Goals

1. **Precision over recall on technical facts** — wrong sample IDs or prices
   are worse than missing an answer.
2. **Citations on every factual claim** — UI shows `[source: doc-id#section]`.
3. **Cheap to refresh** — re-indexing the SOP corpus in < 5 minutes.

## Document tiers and strategies

| Doc type                    | Strategy                                   | Chunk size |
|-----------------------------|--------------------------------------------|------------|
| SOPs (procedural)           | Recursive splitter + section awareness      | 512 tok    |
| Methods (technical)         | Same as SOPs + preserve tables (llama-parse) | 512 tok    |
| Pricing                     | Front-matter summary + smaller sub-chunks   | 512 tok    |
| Regulations                 | Smaller chunks, strict citation tracking    | 512 tok    |
| Sample status               | Structured query — never RAG (use LIMS)     | n/a        |
| Past reports (PDFs)         | Page-aware + table preservation             | 512 tok    |

## Pipeline

```
Source files (corpus/)
      │
      ▼
load_documents (per-file metadata, doc_type)
      │
      ▼
chunk_markdown (RecursiveCharacterTextSplitter, 512/64)
      │
      ▼
embed (VoyageAI voyage-3-large, 1024 dims)
      │
      ▼
INSERT INTO documents  +  HNSW index (vector_cosine_ops)
      │
      ▼
RUN-TIME
   user query
      ▼
[haiku] rewrite for retrieval (optional)
      ▼
[metadata pre-filter]   (e.g. doc_type IN (sop, pricing, regulation))
      ▼
pgvector ORDER BY embedding <=> :qvec  LIMIT 50
      ▼
ENSEMBLE w/ BM25 (RRF)
      ▼
[Cohere Rerank v3.5]  top_n = 8
      ▼
Generate reply — inline citations REQUIRED
      ▼
Reflector (Haiku) — verify citations + safety floor
```

## Chunking settings (rationale)

- **512 tokens, 64 overlap** — middle ground for technical SOPs which mix
  prose and short lists.
- **Recursive splitter on `\n\n`, `\n`, `. `, ` `** — preserves sentence
  boundaries; final split is whitespace-only if a chunk can't be otherwise
  bounded (rare for lab docs).
- **Markdown-aware**: headings propagate into chunk metadata so retrievers
  can rerank by section.

## Embedding model

**Voyage-3-large** (1024 dims) — chosen because:
- Top of MTEB benchmarks on technical / scientific text.
- Async-friendly API.
- Cost: ~$0.18 / 1M tokens (~$0.65 to embed our seed corpus).

For environments where Voyage is unavailable, fall back to
`text-embedding-3-large` (1536 dims) — set `EMBED_PROVIDER=openai` in env.

## Reranker

**Cohere Rerank v3.5** ($2 per 1k queries). Re-ranked top-K=8 → answer.

Phase 1 ships without rerank — dense-only is good enough on the seed corpus.
Switch on when:
- Faithfulness < 0.90 on golden dataset, OR
- More than 1M docs indexed, OR
- Domain experts complain about retrieved chunks missing the answer.

## Metadata pre-filter

```python
where = "doc_type = :doc_type"  # e.g. doc_type = 'sop'
```

This cuts candidates ~80% before the vector scan. Critical for cost as the
corpus grows.

## Evaluation

- **Offline**: weekly `python packages/evals/run_ragas.py --offline` then
  re-run live with API keys.
- **Online**: 5% sample → Haiku grader on faithfulness + tone.
- **Human**: 5% sample → Slack thumbs-up queue.

Targets (end of Phase 4):
- RAGAS faithfulness ≥ 0.95
- RAGAS answer_relevancy ≥ 0.88
- Citation-coverage ≥ 98% (every factual claim is cited)
- p95 first-token latency < 600 ms

## Known gaps

- No PDF parsing yet (only markdown). Phase 2 adds llama-parse for PDFs while
  preserving tables.
- No image / diagram support — Phase 3 candidate.
- No automatic refresh pipeline for new SOPs — Phase 4 (ingest on S3 upload).
