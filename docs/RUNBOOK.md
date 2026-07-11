# Operations Runbook

## Service overview

| Service | URL | Owner | Health |
|---------|-----|-------|--------|
| FastAPI brain (Fly.io) | https://api.greenlab.example | Platform | `/health` |
| Postgres (Neon) | internal | Platform | Neon console |
| Redis (Upstash) | internal | Platform | Upstash console |
| R2 (Cloudflare) | internal | Platform | CF dashboard |
| LangSmith | internal | Platform | smith.langchain.com |
| Zendesk (Phase 2) | internal | Support | Help Center |

## Common procedures

### Re-ingest the corpus

```bash
cd apps/api
uv run python scripts/ingest.py --corpus ./corpus/
```

Re-ingestion deletes and rebuilds the `documents` table. Stagger this
during low-traffic hours.

### Replay a failed conversation

```bash
# Export the conversation to a JSONL file via the conversation_id.
psql $DATABASE_URL -c "COPY (SELECT ... FROM messages WHERE conversation_id='X') TO '/tmp/c.json'"
# Then in Python:
uv run python scripts/replay.py --input /tmp/c.json
```

### Rotate the Anthropic API key

1. Provision new key in Anthropic console.
2. Update Fly.io secret: `fly secrets set ANTHROPIC_API_KEY=...`
3. Update Neon migration: rolling update starts serving new value.
4. Old key remains valid for 24h, then revoke in console.

### Look up a customer by phone

```sql
SELECT id, name, tier FROM customers WHERE phone = '+15555550102';
```

If multiple customers share the contact (e.g. PI + lab manager + finance),
the agent disambiguates by asking for a sample ID or PO before revealing
data — this prevents cross-tenant leakage.

### Escalate a stuck human-handoff

If a `human_handoff_started=true` conversation has been silent for > 24h:

```bash
psql $DATABASE_URL -c "
  SELECT id, customer_id, started_at
  FROM conversations
  WHERE escalated_to_human = TRUE
    AND last_message_at < now() - INTERVAL '24 hours'
    AND closed = FALSE
  ORDER BY last_message_at;
"
```

Triage in Zendesk → tag the scientist queue → close the loop.

## PHI leak response

If we discover PHI in a Slack thread, GitHub issue, or external message:

1. **Freeze writes** — set `app.audit.pause_writes=true` in Fly.io env. This
   stops new audit rows (best-effort) so we don't compound the leak.
2. **Capture evidence** — screenshot, exact URL, timestamp, conversation id.
3. **Pull from DB**:
   ```sql
   SELECT id, ts, customer_id, decision, summary
   FROM audit_logs
   WHERE ts >= NOW() - INTERVAL '24 hours'
     AND summary ILIKE '%<red flag>%';
   ```
4. **Notify** Privacy Officer and CTO within 24h.
5. **Notify** affected customers per §164.404 within 60 days if required.
6. **HHS notification** if breach affects > 500 individuals in a state.

## Scaling

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| p95 first-token latency > 1s on web | LLM cold start or rate limit | Check Anthropic status; consider Haiku for routing |
| Postgres CPU > 80% | Vector scan large due to missing metadata filter | Audit retriever call sites; tighten pre-filters |
| Fly.io 503s | Concurrent reconnect storms | Add rate-limit middleware in `app/main.py` |
| LangSmith quotas | Eval sweeps too frequent | Reduce sampling rate in `score_online.py` |

## Backups

- **Neon**: PITR up to 7 days, daily logical backups to 35 days.
- **R2**: versioning enabled on the lab-reports bucket. 90-day soft delete.
- **Audit logs**: 7-year retention per HIPAA, exported quarterly to S3 Glacier
  for cold storage.

## Disaster recovery

RTO / RPO targets:

| Tier | RTO | RPO |
|------|-----|-----|
| Tier 1 — chat end-to-end | 30 min | 5 min (PITR) |
| Tier 2 — historical conversations | 4 hrs | 1 hr (logical backups) |
| Tier 3 — audit logs | 24 hrs | 24 hrs (export job) |

Recovery drill quarterly. Last drill:
