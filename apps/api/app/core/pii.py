"""
Domain enums and shared types.

These are referenced across the graph, tools, and channel adapters. Keeping
them in one place avoids circular imports.
"""
from __future__ import annotations

from enum import Enum


class Channel(str, Enum):
    """Supported inbound channels."""
    WEB = "web"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    VOICE = "voice"
    SMS = "sms"


class Intent(str, Enum):
    """Classified intents that drive routing in the LangGraph supervisor."""
    FAQ = "faq"
    SAMPLE_STATUS = "sample_status"
    TICKET_STATUS = "ticket_status"
    QUOTE_REQUEST = "quote_request"
    CONSULTATION_BOOKING = "consultation_booking"
    RESULTS_INTERPRETATION = "results_interpretation"
    COMPLAINT = "complaint"
    PRICING = "pricing"
    # Catch-all
    UNCLEAR = "unclear"


class AutonomyTier(str, Enum):
    """
    Tiered autonomy:
      T1 — fully autonomous (FAQ lookups, sample status, ticket creation).
      T2 — autonomous with recommendation (quote drafts, TAT suggestions).
      T3 — recommend only (result interpretation, dispute handling).
      T4 — never autonomous (formal complaints, regulatory notifications, financial credit).
    """
    T1 = "tier1"
    T2 = "tier2"
    T3 = "tier3"
    T4 = "tier4"


class SampleStatus(str, Enum):
    RECEIVED = "received"
    LOGGED = "logged"
    IN_PROCESS = "in_process"
    ON_INSTRUMENT = "on_instrument"
    REVIEW = "review"
    REPORTED = "reported"
    REJECTED = "rejected"


# Actions that ALWAYS route to a human (tier 3 / 4).
ALWAYS_ESCALATE_INTENTS = {
    Intent.RESULTS_INTERPRETATION,
    Intent.COMPLAINT,
}
