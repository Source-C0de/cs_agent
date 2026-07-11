# Build order & status

> Living checklist — update as you ship phases.

## Phase 1 — Web Chat MVP (Weeks 1–4) ✅ foundation shipped

| Item | Status |
|------|--------|
| Monorepo scaffolding | ✅ |
| FastAPI skeleton (config, logging, lifespan) | ✅ |
| Pydantic settings (fails-closed on missing HIPAA flags) | ✅ |
| Postgres LIMS-lite schema (Customer, Sample, Test, Event) | ✅ |
| Alembic migrations (initial + pgvector) | ✅ |
| Seed script | ✅ |
| LangGraph state + supervisor + 4 workers | ✅ |
| LIMS tools (status, recent reports, escalate-to-scientist) | ✅ |
| Scheduler tools (propose + book slots) | ✅ |
| RAG retriever (Voyage + pgvector) | ✅ |
| Document ingestion script + seed corpus | ✅ |
| Compliance reflector | ✅ |
| Human handoff node | ✅ |
| `/api/v1/chat` (sync) | ✅ |
| `/api/v1/chat/stream` (SSE) | ✅ |
| LangSmith wiring via env | ✅ |
| Audit log helpers | ✅ |
| Presidio PII scrubber on logs | ✅ |
| RAGAS-style eval runner + golden dataset (15 Qs) | ✅ |
| Next.js 15 widget (assistant-ui-style streaming) | ✅ |
| Next.js admin HITL queue (skeleton) | ✅ |
| Docs: ARCHITECTURE, RAG, HIPAA, RUNBOOK | ✅ |

## Phase 2 — Email + Zendesk + HubSpot (Weeks 5–6)

- [ ] Postmark inbound webhook adapter
- [ ] Email renderer (subject + HTML/plain body)
- [ ] Zendesk client (create ticket, fetch, append notes)
- [ ] HubSpot client (contact lookup, log interaction)
- [ ] Tier-2 action policy: quote override with human approval

## Phase 3 — WhatsApp + Cal.com (Weeks 7–8)

- [ ] Meta Cloud API webhook adapter
- [ ] 4096-char slicing + interactive buttons
- [ ] Cal.com integration (replace fake scheduler)
- [ ] Plan-and-Execute node for multi-step workflows
- [ ] Notification on slot booking

## Phase 4 — Voice + Hardening (Weeks 9–12)

- [ ] Vapi voice integration (sub-500ms turn-around)
- [ ] Twilio SMS for after-hours + confirmations
- [ ] Rate limiting + circuit breakers
- [ ] Golden dataset grows to 200+ Qs
- [ ] Soak test with 5 friendly customers

## Phase 5 — Optimisation + EU (Weeks 13+)

- [ ] Semantic cache (Redis) — -30% LLM cost
- [ ] Prompt distillation for top-100 FAQs
- [ ] EU region (Frankfurt) + GDPR/EU AI Act hardening
- [ ] SOC 2 Type 1 prep

