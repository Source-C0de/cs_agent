"""
Lightweight PHI/PII quick-check used by intake before we hand off to Presidio
later. This is purely a fast flag — it does NOT replace Presidio.
"""
from __future__ import annotations

import re

# Patterns tuned for lab/support contexts. False positives are OK at this stage;
# the real PII handling happens in the structured logging layer.
_PATTERNS = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "US_SSN"),
    (re.compile(r"\b\d{16}\b"), "CREDIT_CARD"),
    (re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"), "EMAIL"),
    (re.compile(r"\b\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}\b"), "PHONE"),
    (re.compile(r"\b(?:GL|cust)[-_]?\d{2,4}-?\d{3,5}\b", re.I), "INTERNAL_ID"),
    (re.compile(r"\b(?:patient|subject|donor)\s*id[:\s]*[A-Z0-9-]{3,}\b", re.I), "PATIENT_ID"),
]


def quick_phi_check(text: str) -> bool:
    """Returns True if any obvious PHI pattern matches. Cheap, regex-only."""
    if not text:
        return False
    for pat, _kind in _PATTERNS:
        if pat.search(text):
            return True
    return False
