"""Deterministic groundedness check. T051 (also reused by the annotation agent)."""

from __future__ import annotations

from app.application.groundedness import ground_annotation
from app.domain.annotation import Annotation
from app.domain.key_entity import KeyEntity


def _annotation(entities: list[KeyEntity], confidence: float = 0.9) -> Annotation:
    return Annotation(
        summary="s",
        document_type="invoice",
        key_entities=entities,
        language="en",
        source_filename="f.pdf",
        page_or_sheet_count=1,
        confidence=confidence,
        extracted_at="2026-06-03T00:00:00Z",
        ungrounded_fields=[],
    )


def test_flags_present_and_absent_values() -> None:
    ann = _annotation([KeyEntity("org", "ACME"), KeyEntity("amount", "$999")])
    out = ground_annotation(ann, "Invoice from ACME for consulting services")
    grounded = {e.value: e.grounded for e in out.key_entities}
    assert grounded["ACME"] is True
    assert grounded["$999"] is False
    assert out.ungrounded_fields == ["$999"]


def test_lowers_confidence_when_ungrounded() -> None:
    ann = _annotation([KeyEntity("org", "ACME"), KeyEntity("amount", "$999")], confidence=0.9)
    out = ground_annotation(ann, "Invoice from ACME")
    assert out.confidence < 0.9  # one of two entities ungrounded


def test_all_grounded_keeps_confidence_and_empty_flags() -> None:
    ann = _annotation([KeyEntity("org", "ACME")], confidence=0.8)
    out = ground_annotation(ann, "ACME report")
    assert out.confidence == 0.8
    assert out.ungrounded_fields == []
    assert out.key_entities[0].grounded is True


def test_matching_is_case_insensitive() -> None:
    ann = _annotation([KeyEntity("org", "acme")])
    out = ground_annotation(ann, "Invoice from ACME")
    assert out.key_entities[0].grounded is True


def _grounded(value: str, text: str) -> bool:
    out = ground_annotation(_annotation([KeyEntity("x", value)]), text)
    return out.key_entities[0].grounded


# --- short values must match on a boundary, not as a spurious substring -------


def test_short_value_does_not_match_inside_a_word() -> None:
    assert _grounded("IT", "the internal audit committee met") is False
    assert _grounded("IT", "the IT department met") is True


def test_short_number_does_not_match_inside_a_longer_number() -> None:
    assert _grounded("1", "10 invoices were issued") is False
    assert _grounded("1", "page 1 of 4") is True


# --- numeric formatting differences should still ground -----------------------


def test_thousands_separator_and_currency_decimals_are_normalized() -> None:
    assert _grounded("USD 1,500.00", "Total due: USD 1500") is True
    assert _grounded("1000", "Amount: 1,000 units") is True
    assert _grounded("$4,200", "amount due 4200") is True


def test_slash_dates_match_dash_dates() -> None:
    assert _grounded("2026-01-15", "invoice dated 2026/01/15") is True
    assert _grounded("2026/01/15", "reporting period 2026-01-15") is True


# --- documented residual limitation: textual-month dates flag ungrounded ------


def test_textual_month_dates_are_a_known_gap() -> None:
    # Not reconciled by the cheap normaliser; flags ungrounded by design (documented).
    assert _grounded("2024-01-01", "dated January 1, 2024") is False
