"""
Lightweight RAGAS-style runner — does not require the ragas library at runtime.

For each golden Q&A:
  - Run the agent against the question.
  - Score on:
      • intent_match       (Pass/Fail)
      • keyword_coverage   (fraction of expected keywords present in reply)
      • citation_doc_match (any citation matches expected doc prefix)
      • human_match        (does reply says "escalat" when expects_human=True, vice versa)
  - Report per-row scores and aggregate metrics.

This is intentionally dependency-free so the CI runs without API keys.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import mean


DATASET = Path(__file__).parent / "golden_dataset.jsonl"


def simple_score(reply: str, expectations: dict) -> dict:
    text = (reply or "").lower()

    keywords = [k.lower() for k in expectations.get("expect_keywords", [])]
    keyword_hits = sum(1 for k in keywords if k.lower() in text)
    keyword_coverage = keyword_hits / len(keywords) if keywords else 1.0

    has_citation_prefix = bool(
        expectations.get("expect_citation_doc_prefix")
        and expectations["expect_citation_doc_prefix"] in (reply or "")
    )

    says_escalate = any(w in text for w in ("escalate", "scientist",
                          "human", "follow up", "one of our", "team member"))
    if expectations.get("expects_human"):
        human_match = says_escalate
        note = "human_required" if human_match else "HUMAN_REQUIRED_MISSING"
    else:
        human_match = not says_escalate
        note = "auto_ok" if human_match else "AUTO_REPLY_BUT_ESCALATED"

    return {
        "keyword_coverage": round(keyword_coverage, 3),
        "citation_doc_match": has_citation_prefix,
        "human_match": human_match,
        "note": note,
    }


async def run_agent(question: str, customer_id: str = "CUST-0001") -> dict:
    """Thin client over the running FastAPI instance."""
    import httpx

    url = "http://localhost:8000/api/v1/chat"
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            url,
            json={"customer_id": customer_id, "message": question, "stream": False},
        )
        r.raise_for_status()
        return r.json()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--offline", action="store_true",
                   help="Skip live API calls; score against canned answers only.")
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()

    if not DATASET.exists():
        print(f"Dataset not found: {DATASET}")
        sys.exit(1)

    rows = []
    with DATASET.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    if args.limit:
        rows = rows[: args.limit]

    if args.offline:
        # Treat each golden row's own question + a placeholder reply so we
        # can score the framework wiring end-to-end without an API key.
        results = []
        for r in rows:
            # Fake reply that contains all expected keywords for self-test.
            reply = " ".join(r.get("expect_keywords", []))
            score = simple_score(reply, r)
            results.append({"q": r["q"], **score})
    else:
        import asyncio
        results = []
        for r in rows:
            try:
                resp = asyncio.run(run_agent(r["q"]))
                reply = resp.get("reply", "")
            except Exception as exc:
                print(f"[error] {r['q'][:60]}: {exc}")
                continue
            score = simple_score(reply, r)
            results.append({"q": r["q"], **score})

    # Aggregate
    avg_kw = mean(r["keyword_coverage"] for r in results) if results else 0
    cite_pct = (sum(1 for r in results if r["citation_doc_match"]) /
                max(len(results), 1)) * 100
    human_pct = (sum(1 for r in results if r["human_match"]) /
                 max(len(results), 1)) * 100

    print(json.dumps({
        "count": len(results),
        "avg_keyword_coverage": round(avg_kw, 3),
        "citation_match_pct": round(cite_pct, 1),
        "human_routing_pct": round(human_pct, 1),
        "rows": results,
    }, indent=2))


if __name__ == "__main__":
    main()
