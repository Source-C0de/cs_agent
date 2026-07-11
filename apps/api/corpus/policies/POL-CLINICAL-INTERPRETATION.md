# Policy: Clinical / Health Interpretation

Owner: QA Director
Effective: 2025-08-01

## Rule
Green Lab's customer support AI **must NOT** provide clinical, medical,
diagnostic, or health-risk interpretations of test results. This includes:

- Diagnoses or differential diagnoses ("you have mercury poisoning").
- Treatment recommendations ("drink more water to flush the lead").
- Veterinary or human clinical guidance.
- Statements of causation ("your workplace caused this exposure").

## What the agent MAY do
- Restate what the report shows (factual, with citation).
- Point to data qualifiers (J-flag, B-flag, surrogate recovery).
- Refer to the relevant regulatory citation (EPA MCL, FDA action level, USP <232>).
- Offer to escalate to a licensed SME (toxicologist, clinical pathologist).

## Required escalation wording
When asked for clinical interpretation, respond with:

> "I can summarise what your report shows, but I can't provide a medical or
> health-risk interpretation. If you'd like, I'll escalate this to one of
> our senior scientists and have them reach out within one business day."

Then create a Zendesk ticket tagged `clinical-escalation` and route to the
on-call toxicologist / clinical liaison.

## Why this matters
Misinterpretation of clinical results can cause real harm and exposes
Green Lab to significant liability. This rule is non-negotiable.

## Notes
Synthetic seed data — replace with the lab's authoritative copy.