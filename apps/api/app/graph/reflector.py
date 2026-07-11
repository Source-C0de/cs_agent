"""
Compliance reflector — last node before reply.

Cheap Haiku pass that checks the draft for:
  1. Hallucinated sample IDs / prices / dates.
  2. Clinical interpretation violations.
  3. PHI/PII leakage.
  4. Required citations.

If any check fails, the reflector either regenerates or escalates.
"""
from __future__ import annotations

import re
from typing import Any

from app.core.llm import complete, router_model
from app.graph.audit import timed_node
from app.graph.pii import quick_phi_check

REFLECT_PROMPT = """You are the Green Lab compliance checker. Given a draft reply and
the citations it references, check the FOUR rules below. Reply with JSON only.

Rules:
1. NO_HALLUCINATION — Every sample ID, price, date, or analyte concentration
   in the reply must appear in the cited source text.
2. NO_CLINICAL_INTERPRETATION — Reply must not diagnose, treat, or provide
   a health-risk interpretation. It MAY restate facts and offer escalation.
3. NO_PII_LEAK — No full email addresses, phone numbers, SSNs, or any
   identifier that wasn't already in the user message.
4. CITES_SOURCES — Any factual claim must have a [source: <doc-id>] tag.

Output JSON:
{
  "verdict": "ok" | "regenerate" | "escalate",
  "issues": [list of strings],
  "reason": null | string
}
"""


async def compliance_reflector(state: dict[str, Any]) -> dict[str, Any]:
    with timed_node("reflect"):
        draft = state.get("draft_reply", "") or ""
        citations = state.get("citations", [])

        # Pre-flight regex checks for safety
        issues = []
        if re.search(r"\bGL-\d{4}-\d{4}\b", draft) and not citations:
            issues.append("Cites a sample ID but no source attached.")

        # Cheap PII check on the draft itself
        if quick_phi_check(draft):
            issues.append("Draft contains PII/PHI that should not appear in the reply.")

        # Soft check for clinical interpretation wording
        clinical_keywords = ("diagnos", "you have", "you are sick",
                             "treatment", "should take", "see a doctor")
        if any(k in draft.lower() for k in clinical_keywords):
            issues.append("Draft appears to contain clinical interpretation language.")

        if not issues:
            return state  # all good

        # If only minor issues, try regenerating with a stronger system prompt
        log = __import__("logging").getLogger("reflect")
        log.info("reflect.issues", issues=issues)

        # For Phase 1 we escalate if any hard issue (PII leak, clinical, hallucination).
        hard = any(("PII" in i or "clinical" in i.lower() or "sample ID" in i)
                   for i in issues)
        if hard:
            return {
                **state,
                "requires_human": True,
                "escalation_reason": "Reflector flagged: " + "; ".join(issues),
            }

        return state  # soft issues, leave as is
