# Green Lab API

The brain of the Green Lab customer support agent. FastAPI + LangGraph +
Postgres + pgvector. HIPAA-grade: zero-retention LLM tier, PII-redacting
logger, audit log on every decision.

## Run locally

```bash
# 1. Postgres + Redis
cd ../../infra/docker && docker compose up -d

# 2. Install + migrate
cd ../../apps/api
uv sync
uv run alembic upgrade head
uv run python scripts/seed.py
uv run python scripts/ingest.py --corpus ./corpus

# 3. Run
uv run uvicorn app.main:app --reload --port 8000
```

Visit http://localhost:8000/docs for OpenAPI.

## Architecture

See [`/docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md) for the overall
diagram and design rationale.

## Tests

```bash
uv run pytest -q tests/
```

## Layout

```
app/
├── core/         # config, logging, observability, LLM client
├── db/           # SQLAlchemy base, session, engine
├── models/       # ORM tables (Customer, Sample, Conversation, ...)
├── graph/        # LangGraph supervisor, workers, intake, reflector, routing
├── rag/          # Voyage embeddings, pgvector retriever, ingestion
├── tools/        # LangChain tools (lims, scheduler, ...)
├── routes/       # FastAPI routers (chat, health, webhooks)
└── main.py       # FastAPI app + lifespan
```

## Compliance

PII redaction runs by default in dev (regex-only path). For production set
`APP_ENV=production` and the production path switches to Presidio + the
`anthropic-beta: zero-retention-2024-12` header is *required* (the app will
refuse to start otherwise).

See [`/docs/HIPAA_CONTROLS.md`](../../docs/HIPAA_CONTROLS.md) for the full
control matrix.
