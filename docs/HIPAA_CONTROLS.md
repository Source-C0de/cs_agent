# HIPAA Controls

> **Scope:** This document tracks the technical and administrative safeguards
> implemented across Green Lab Support for HIPAA compliance. Coordinate with
> counsel before any GA deployment.

## §164.308 — Administrative safeguards

| Item | Owner | Status |
|------|-------|--------|
| Workforce training on PHI handling | HR | Pending (post-launch) |
| Access management (Clerk + RBAC) | CTO | Phase 1 (Clerk); RBAC in Phase 4 |
| Workforce clearance | HR | Pending |
| Incident response plan | SRE | See `RUNBOOK.md` §"PHI leak" |
| Contingency plan (backups) | SRE | Neon PITR; runbook to follow |
| Evaluation (annual review) | Compliance | Calendar task |

## §164.310 — Physical safeguards

| Item | Provider | Status |
|------|----------|--------|
| Datacenter access | Neon / Fly.io / Vercel / Anthropic / Cloudflare | All have SOC 2 + HIPAA BAAs |
| Workstation security | Apple IT | MDM, FileVault, screen lock |
| Device disposal | Apple IT | Standard |

## §164.312 — Technical safeguards

| Item | Implementation | Location |
|------|----------------|----------|
| **Access control (a)(1)** | Clerk auth + RBAC. No PHI in logs. | `apps/web`, Clerk |
| **Audit controls (b)** | Every agent decision → `audit_logs` row | `app/graph/audit.py` |
| **Integrity (c)(1)** | Postgres TDE (Neon), TLS in transit (Vercel/Anthropic) | Neon, Anthropic |
| **Person authentication (d)** | Web: Clerk; API: customer token + Clerk | `apps/web`, `app/routes/chat.py` |
| **Transmission security (e)(1)** | TLS 1.3, Anthropic zero-retention tier | App-wide |

## BAAs in force

| Vendor   | BAA status | Notes |
|----------|-----------|-------|
| Anthropic | Required — sign before any prod traffic | Zero-retention header on every call |
| Neon      | Required — sign before any prod traffic | HIPAA-eligible plan |
| Vercel    | Required — sign before any prod traffic | Enterprise plan required |
| Cloudflare | Required — sign before any prod traffic | R2 + Workers |
| Cohere    | Optional — covered by zero-retention | Default off in Phase 1 |
| Voyage AI | Optional — covered by zero-retention | Default off in Phase 1 |

## PHI flow

```
Customer
   │  (chat in)
   ▼
[Web Widget]   ──►►►  (TLS)  ──►►►  FastAPI
                                        │
                                        │  (PHI may exist here,
                                        │   but never leaves encrypted)
                                        ▼
                                  [LangGraph brain]
                                  ┌─────────────────┐
                                  │ Intake classifier│  (PII quick-check tag)
                                  │ Tools (LIMS)      │  (PHI stays in DB)
                                  │ RAG retriever     │  (sees doc chunks, not PHI)
                                  │ Reflector         │  (re-checks safety)
                                  └─────────────────┘
                                        │
                                        ▼
                                  [response] (PHI only if user already sent it)
                                        │
                                        ▼
                              [Audit log row]  (SHA-256 hashed input)
```

## PII / PHI handling

### At intake
- `presidio_analyzer` runs on every user message; matches are tagged,
  not removed (we still need to look up the sample they referenced).
- A flag is set on `SupportState.has_phi`. Downstream workers can act on it.

### At logging (HIPAA)
- `app/core/logging.py` runs `_redacting_processor` on every structlog event
  before emission.
- Presidio entity types scrubbed: PERSON, PHONE_NUMBER, EMAIL_ADDRESS,
  US_SSN, CREDIT_CARD, MEDICAL_LICENSE, US_DRIVER_LICENSE, DATE_TIME.

### At model call (zero-retention)
- Every Anthropic call carries `anthropic-beta: zero-retention-2024-12`.
- We refuse to start in production if `ANTHROPIC_ZERO_RETENTION` is unset.

### At storage
- Conversation history is encrypted at rest via Postgres TDE (Neon).
- Files in R2 are encrypted with SSE-S3.
- 7-year retention per §164.530(j)(2).

### Backup / disaster recovery
- Neon PITR up to 7 days, daily logical backups up to 35 days.
- Runbook to restore from Neon fork into a clean region if PHI is suspected
  in a backup.

## Audit log schema

```sql
CREATE TABLE audit_logs (
    id              BIGSERIAL PRIMARY KEY,
    ts              TIMESTAMPTZ NOT NULL DEFAULT now(),
    customer_id     TEXT,
    conversation_id TEXT,
    node            TEXT NOT NULL,        -- LangGraph node name
    decision        TEXT NOT NULL,        -- reply, escalate, tool_call, ...
    input_hash      VARCHAR(64) NOT NULL, -- SHA-256 of input
    summary         TEXT,                 -- redacted summary, may be null
    model           TEXT,
    latency_ms      INTEGER
);
```

`input_hash` is the key forensic primitive: it lets a compliance officer
verify reproducibility by re-running the same input against the recorded
`model` + `decision`, without ever storing PHI in the audit table.

## Breach response

If a PHI leak is suspected:

1. Freeze writes (post-deploy: enable `app.audit.pause_writes` flag).
2. Pull affected rows from `audit_logs` by `customer_id` or `conversation_id`.
3. Pull session detail from `messages` and `conversations`.
4. Triage with Privacy Officer within 24h per §164.408.
5. Notify HHS / affected individuals per §164.404, §164.406.

Full runbook in `RUNBOOK.md`.

## Open items (must close before GA)

- [ ] Sign BAAs with all vendors.
- [ ] Annual penetration test.
- [ ] Risk assessment per §164.308(a)(1)(ii)(A).
- [ ] Workforce training docs + quiz.
- [ ] Document retention policy in HR system.
- [ ] PHI handling section in customer DPA.
