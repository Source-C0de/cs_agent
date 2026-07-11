# Green Lab Support — Architecture

> Phase 1 (Web Chat MVP). Add channel adapters in Phases 2–4.

## Goals

1. Resolve ≥ 70% of routine support requests without a human.
2. Always escalate clinical interpretation, complaints, and high-stakes actions.
3. Maintain a full audit trail and PII-safe logging for HIPAA compliance.
4. Keep the LLM-brain reusable across channels (web, email, WhatsApp, voice).

## Component map

```
                  ┌──────────────────────────────────┐
                  │        Web Chat Widget           │
                  │   (Next.js 15 + assistant-ui)    │
                  └────────────┬─────────────────────┘
                               │ SSE / text-event-stream
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ FastAPI Brain (apps/api)                                     │
│                                                              │
│  intake (Haiku) ──► routing ──► workers ──► reflector ──► END │
│                                          │                   │
│                                          └─► human_handoff   │
│                                                              │
│  ├── Tools   : LIMS, scheduling, ticketing (Phase 2), CRM     │
│  ├── RAG     : pgvector + Voyage + Cohere rerank + BM25      │
│  └── Memory  : LangGraph PostgresSaver (per conversation)    │
└──────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Postgres (Neon) — single DB                                  │
│ ├── business tables (customers, samples, sample_events)      │
│ ├── conversations + messages (audit-grade history)           │
│ ├── documents + embeddings (pgvector)                        │
│ └── audit_logs (HIPAA) + LangGraph checkpoints               │
└──────────────────────────────────────────────────────────────┘
```

## Routing decisions (LangGraph supervisor)

| Detected intent          | Routed to     | Autonomy tier |
|--------------------------|---------------|---------------|
| faq                      | `faq_node`    | tier 1        |
| pricing                  | `faq_node`    | tier 1        |
| sample_status            | `lims_node`   | tier 1        |
| ticket_status            | `ticket_node` | tier 1        |
| quote_request            | `quote_node`  | tier 1        |
| consultation_booking     | `scheduler`   | tier 1        |
| results_interpretation   | `human_handoff` (HARD floor) | tier 3 |
| complaint                | `human_handoff` (HARD floor) | tier 3 |
| (anything tier 3 / 4)    | `human_handoff`             | tier 3 / 4 |
| unclear + low confidence | `faq_node` then reflector    | tier 1      |

## Tiered autonomy

- **Tier 1** — Fully autonomous: account lookups, status, FAQ.
- **Tier 2** — Autonomous with recommendation (Phase 2 — quote overrides).
- **Tier 3** — Recommend only (clinical interpretation, dispute routing).
- **Tier 4** — Never autonomous (regulatory notifications, financial credit).

The reflector node runs after every worker and **forces escalation** if it
detects a clinical interpretation claim, a hallucinated sample ID without a
source, or PII leakage.

## Why these technologies

| Choice | Why |
|--------|-----|
| **LangGraph over CrewAI/AutoGen** | State machines + cycles work great for "ask follow-up" flows. Built-in checkpointing for HITL and channel resumption. |
| **Postgres + pgvector** | One DB for app data, vectors, checkpoints, and audit logs. Cuts ops surface area. |
| **Voyage-3-large embeddings** | Top of MTEB on technical/scientific text; tuned for the lab domain. |
| **Cohere Rerank v3** | Drops recall error rate by 30%+; first-stage dense retrieval is cheap, rerank is the precision lift. |
| **Claude Sonnet 4.5** | Best tool-use + longest context (200k) for loading whole lab reports. |
| **Claude Haiku 4.5** | 10× cheaper; used as the router/grader. |
| **Next.js + assistant-ui** | Full chat widget UI for free; streaming primitives built-in. |
| **an Assistant-UI** | Already designed for streaming + tool-call rendering. |

## Why NOT these

| Decision | Reason |
|----------|--------|
| **LangChain-only**   | We'd lose direct control of the state machine. |
| **Serverless-only**  | WebSocket warm-up cost would hurt first-token latency. |
| **Pinecone**         | Cost at our scale; pgvector + pgvector HNSW is enough. |
| **Custom chunker**   | RecursiveCharacterTextSplitter + markdown-aware covers 95%. |
| **MFA / SSO in Phase 1** | Clerk out of the box; tighten in Phase 4 with HIPAA BAA. |

## Open architectural questions (post Phase 1)

1. Should we add a dedicated **regulation** RAG collection (Federal Register,
   state-specific regs) and chunk-level hrefs to public sources?
2. How do we measure **deflection rate** — by conversation-closed vs.
   message-passed to human vs. an LLM-driven proxy?
3. EU AI Act: if we expand to EU customers, do we run the brain in the EU
   region with a separate Anthropic / Cohere tenant?

## Cross-references

- `RAG_PIPELINE.md` — chunking, embedding, rerank, evaluation.
- `HIPAA_CONTROLS.md` — PII, retention, BAAs, audit.
- `RUNBOOK.md` — operational procedures.
