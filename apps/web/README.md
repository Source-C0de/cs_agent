# Green Lab Web

Next.js 15 + TypeScript chat widget and admin console for Green Lab Support.

## Run locally

```bash
cp .env.example .env  # fill in API URL + Clerk keys (optional)
npm install
npm run dev
# Visit http://localhost:3000
```

## Pages

- `/` — landing page.
- `/widget` — embeddable chat (Phase 1 demo).
- `/admin` — HITL / audit-log viewer (Phase 2 will add real data).

## How it talks to the API

The web rewrites requests from `/api/chat/*` to the FastAPI backend (see
`next.config.mjs`). The streaming client in `lib/api.ts` consumes SSE frames
and incrementally updates the assistant message.

In production behind one Fly.io origin, the rewrite is dropped and both
services share the same domain.
