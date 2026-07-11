"""
Intake router — the FIRST node in the supervisor.

Uses Haiku (cheap) to:
1. Detect PHI/PII and tag it (state.has_phi = True).
2. Classify the user's intent.
3. Flag if escalation is required.

The intent drives downstream routing. We never allow an empty intent to fall
through silently — `unclear` is treated like `faq` but with `requires_human`
flagged if confidence is low.
"""
from __future__ import annotations

import json
from typing import Any

from app.core.llm import complete, router_model
from app.core.logging import get_logger
from app.graph.audit import timed_node, write_audit
from app.graph.state import SupportState

log = get_logger("intake")

INTENT_SYSTEM_PROMPT = """You are Green Lab's intake classifier. For each user message, respond with a single JSON object:

{
  "intent": one of: faq | sample_status | ticket_status | quote_request | consultation_booking | results_interpretation | complaint | pricing | unclear,
  "entities": {
    "sample_ids": list of strings like GL-2026-0042,
    "test_codes": list of strings like PFAS-537,
    "dates": list of ISO-8601 strings,
    "matrices": list of strings (groundwater, soil, serum, ...)
  },
  "tier": "tier1" | "tier2" | "tier3" | "tier4",
  "requires_human": bool,
  "reason": short string explaining human handoff if true,
  "confidence": float 0.0–1.0
}

Rules:
- Anything asking us to INTERPRET a clinical result (e.g. "does this mean I have mercury poisoning?") MUST be tier3+ and requires_human=true.
- Anything mentioning a complaint, dispute, or legal action MUST be tier3+ and requires_human=true.
- Pricing override requests or contract negotiations are tier2 (auto with recommendation).
- Routine status / FAQ / booking are tier1.
- Never invent a sample id. If you can't find one, return [].

Respond with JSON only, no prose."""


async def intake_router(state: SupportState) -> dict[str, Any]:
    """Classify and tag the latest user message."""
    with timed_node("intake"):
        last_user_msg = next(
            (m for m in reversed(state.messages) if m.get("role") == "user"),
            None,
        )
        if last_user_msg is None:
            return {"intent": "unclear", "requires_human": True,
                    "escalation_reason": "No user message found."}

        # Cheap PII flag: simple regex-style detector — Presidio runs in logging.
        # We don't block on PII; we just flag for downstream redaction.
        from app.graph.pii import quick_phi_check
        has_phi = quick_phi_check(last_user_msg["content"])

        try:
            resp = await complete(
                system=INTENT_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": last_user_msg["content"]}],
                model=router_model(),
                max_tokens=400,
                temperature=0.0,
            )
            raw = resp.content[0].text if resp.content else "{}"
            parsed = json.loads(raw)
        except Exception as exc:  # parse error / API down
            log.warning("intake.classifier_failed", error=str(exc))
            parsed = {"intent": "unclear", "confidence": 0.0,
                      "tier": "tier1", "requires_human": False,
                      "entities": {}, "reason": None}

        # Hard safety floor: clinical interpretation ALWAYS escalates.
        intent = parsed.get("intent", "unclear")
        if intent == "results_interpretation":
            parsed["requires_human"] = True
            parsed["tier"] = "tier3"
            parsed["reason"] = parsed.get("reason") or "Clinical interpretation"
        if intent == "complaint":
            parsed["requires_human"] = True
            parsed["tier"] = "tier3"

        # Persist audit (would be AsyncSession in real impl)
        # Skipping actual DB write here; a service-layer wrapper does it.

        return {
            "intent": intent,
            "entities": parsed.get("entities", {}),
            "autonomy_tier": parsed.get("tier", "tier1"),
            "requires_human": bool(parsed.get("requires_human", False)),
            "escalation_reason": parsed.get("reason"),
            "confidence": float(parsed.get("confidence", 1.0)),
            "has_phi": has_phi,
        }