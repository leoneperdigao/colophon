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
