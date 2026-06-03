"""Canonical entity-type mapping used by the gold-set scorer (ADR-0014).

Models name the same entity many ways ("organization"/"vendor" for an org,
"invoice_date"/"reporting_period_end" for a date). The gold set uses a small
controlled vocabulary (org/date/amount). Scoring canonicalises both sides so a
correct *value* under a synonymous *type* counts as a match — not a false miss.
"""

from __future__ import annotations

import pytest

from eval.entity_types import canonical_entity_type


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # org synonyms
        ("organization", "org"),
        ("Organisation", "org"),
        ("vendor", "org"),
        ("Company", "org"),
        # date synonyms
        ("invoice_date", "date"),
        ("Invoice Date", "date"),
        ("reporting_period_end", "date"),
        ("due_date", "date"),
        # amount synonyms
        ("amount_due", "amount"),
        ("Net Revenue", "amount"),
        ("total", "amount"),
    ],
)
def test_known_synonyms_map_to_canonical(raw: str, expected: str) -> None:
    assert canonical_entity_type(raw) == expected


@pytest.mark.parametrize("canonical", ["org", "date", "amount"])
def test_canonical_types_map_to_themselves(canonical: str) -> None:
    assert canonical_entity_type(canonical) == canonical


def test_unknown_type_passes_through_normalized() -> None:
    # Unmapped names are NOT force-fit to a bucket (no false credit); they are
    # only normalised (casefold + separators->underscore) and compared as-is.
    assert canonical_entity_type("Invoice Number") == "invoice_number"
    assert canonical_entity_type("other") == "other"


def test_mapping_is_case_and_separator_insensitive() -> None:
    assert canonical_entity_type("  ORGANIZATION ") == "org"
    assert canonical_entity_type("amount-due") == "amount"
