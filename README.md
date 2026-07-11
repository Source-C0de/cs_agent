# Green Lab Support

A multi-channel, HIPAA-grade customer support AI agent for **Green Lab** — a lab/research services company.

> **Status:** Phase 1 (Foundation + Web Chat MVP) under active development.

## What it does

- **Web chat** (Phase 1): answers lab-specific questions from a curated RAG corpus, looks up sample/quote/ticket status, books consultations, escalates to humans.
- **Email, WhatsApp, Voice** (Phases 2–4): same brain, more channel adapters.

## Repo layout

```
green-lab-support/
├── apps/
│   ├── api/        # FastAPI brain (Python)
│   └── web/        # Next.js 15 chat widget
├── packages/
│   ├── shared/     # Pydantic models, channel adapters, types
│   └── evals/      # Golden dataset + RAGAS runner
├── infra/          # Docker, deployment configs
└── docs/           # Architecture, RAG, HIPAA controls, ops runbook
```

## Quick start (local dev)

```bash
# 1. Backend
cd apps/api
uv sync
cp ../../.env.example .env   # fill in API keys
uv run alembic upgrade head  # create schema
uv run python scripts/seed.py  # synthetic samples + audit_logs

# 2. Corpus ingestion
uv run python scripts/ingest.py

# 3. Run API
uv run uvicorn app.main:app --reload --port 8000

# 4. Web widget (in another terminal)
cd ../web
npm install
npm run dev
```

Visit http://localhost:3000/widget for the chat, http://localhost:3000/admin for the HITL queue.

## Stack

- LLM: Claude Sonnet 4.5 (brain) + Haiku 4.5 (router) via Anthropic API (zero-retention, BAA)
- Orchestration: LangGraph + PostgresSaver checkpointer
- Backend: FastAPI + Pydantic v2 (async)
- RAG: pgvector + Voyage-3-large embeddings + Cohere Rerank v3
- PDF parsing: llama-parse (preserves tables in lab SOPs)
- Frontend: Next.js 15 + assistant-ui
- Observability: LangSmith
- Evals: RAGAS + LLM-as-judge
- PII: Microsoft Presidio

See `docs/` for architecture details, HIPAA controls, RAG settings rationale, and the ops runbook.
