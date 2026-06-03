"""Canonical entity-type mapping for gold-set scoring (ADR-0014).

The gold set labels entities with a small controlled vocabulary (`org`, `date`,
`amount`); a real model names the same things many ways ("organization", "vendor",
"invoice_date", "reporting_period_end", "amount_due", "net_revenue"). Exact
`(type, value)` scoring would penalise a *correct value* under a synonymous *type*
as both a false positive and a false negative — punishing vocabulary, not quality.

This maps known synonyms onto the canonical type before scoring. The mapping is
**explicit, not fuzzy** (ADR-0014): an unknown type is only normalised and compared
as-is, never force-fit to a bucket — so a genuinely mistyped entity is still a miss
and the gate cannot be gamed by over-broad matching.
"""

from __future__ import annotations

import re

# canonical type -> the synonymous names a model might emit for it.
_CANONICAL_SYNONYMS: dict[str, set[str]] = {
    "org": {
        "organization",
        "organisation",
        "company",
        "vendor",
        "supplier",
        "client",
        "customer",
        "issuer",
        "recipient",
        "payee",
        "payer",
        "sender",
        "business",
        "entity",
        "party",
        "counterparty",
        "firm",
        "institution",
        "employer",
        "manufacturer",
        "seller",
        "buyer",
        "beneficiary",
    },
    "date": {
        "invoice_date",
        "due_date",
        "issue_date",
        "issued_date",
        "report_date",
        "reporting_date",
        "reporting_period",
        "reporting_period_end",
        "period_end",
        "period_ending",
        "period",
        "fiscal_year_end",
        "fiscal_year_ending",
        "fiscal_year",
        "statement_date",
        "transaction_date",
        "payment_date",
        "effective_date",
        "expiry_date",
        "expiration_date",
        "start_date",
        "end_date",
        "datetime",
        "deadline",
    },
    "amount": {
        "amount_due",
        "total",
        "total_due",
        "total_amount",
        "grand_total",
        "sum",
        "subtotal",
        "net_amount",
        "net_revenue",
        "revenue",
        "gross_amount",
        "balance",
        "balance_due",
        "price",
        "unit_price",
        "total_price",
        "cost",
        "payment",
        "payment_amount",
        "fee",
        "charge",
    },
}

# Inverted lookup (synonym -> canonical). Each canonical also maps to itself.
_SYNONYM_TO_CANONICAL: dict[str, str] = {canonical: canonical for canonical in _CANONICAL_SYNONYMS}
for _canonical, _synonyms in _CANONICAL_SYNONYMS.items():
    for _synonym in _synonyms:
        _SYNONYM_TO_CANONICAL[_synonym] = _canonical

_SEP = re.compile(r"[^a-z0-9]+")


def _normalize(raw: str) -> str:
    """Casefold and fold separators (spaces, hyphens) to underscores: 'Invoice Date'
    and 'invoice-date' both become 'invoice_date'."""
    return _SEP.sub("_", raw.strip().casefold()).strip("_")


def canonical_entity_type(raw: str) -> str:
    """Map an entity type to its canonical form, or the normalised name if unknown."""
    normalized = _normalize(raw)
    return _SYNONYM_TO_CANONICAL.get(normalized, normalized)
