"""AnnotationAgent — classify -> extract -> validate/repair -> ground. T044."""

from __future__ import annotations

from typing import Any

import pytest

from app.adapters.llm.agent import AnnotationAgent
from app.application.ports.llm_client import LLMError
from app.application.ports.llm_transport import TransportError
from app.domain.stage_result import Curated
from tests.fakes.fake_transport import FakeTransport

CURATED = Curated(
    text="Invoice from ACME Corp. Total due: $4,200. Date: 2026-01-02.",
    page_or_sheet_count=1,
)


def _agent(transport: Any) -> AnnotationAgent:
    return AnnotationAgent(transport, now=lambda: "2026-06-03T00:00:00Z")


def test_produces_grounded_annotation_happy_path() -> None:
    transport = FakeTransport(
        classify={"document_type": "invoice"},
        extract={
            "summary": "Invoice from ACME Corp for $4,200.",
            "key_entities": [
                {"type": "org", "value": "ACME Corp"},
                {"type": "amount", "value": "$4,200"},
            ],
            "language": "en",
        },
    )
    ann = _agent(transport).annotate(CURATED, "invoice.pdf")
    assert ann.document_type == "invoice"
    assert ann.source_filename == "invoice.pdf"
    assert ann.page_or_sheet_count == 1
    grounded = {e.value: e.grounded for e in ann.key_entities}
    assert grounded["ACME Corp"] is True
    assert grounded["$4,200"] is True
    assert ann.ungrounded_fields == []
    assert ann.extracted_at == "2026-06-03T00:00:00Z"


def test_flags_ungrounded_extracted_values_and_lowers_confidence() -> None:
    transport = FakeTransport(
        classify={"document_type": "invoice"},
        extract={
            "summary": "x",
            "key_entities": [{"type": "org", "value": "GHOST INC"}],
            "language": "en",
        },
    )
    ann = _agent(transport).annotate(CURATED, "f.pdf")
    assert ann.key_entities[0].grounded is False
    assert ann.ungrounded_fields == ["GHOST INC"]
    assert ann.confidence < 0.9


def test_unknown_classification_falls_back_to_other() -> None:
    transport = FakeTransport(
        classify={"document_type": "banana"},
        extract={"summary": "x", "key_entities": [], "language": "en"},
    )
    assert _agent(transport).annotate(CURATED, "f.pdf").document_type == "other"


def test_content_is_delimited_and_labelled_untrusted() -> None:
    transport = FakeTransport(
        classify={"document_type": "report"},
        extract={"summary": "x", "key_entities": [], "language": "en"},
    )
    _agent(transport).annotate(CURATED, "f.pdf")
    extract_call = next(
        c for c in transport.calls if "key_entities" in c["schema"].get("properties", {})
    )
    assert "<document>" in extract_call["user"]  # content delimited
    assert "not instructions" in extract_call["system"].lower()  # injection framing


def test_invalid_output_after_repair_raises_llm_error() -> None:
    transport = FakeTransport(
        classify={"document_type": "invoice"},
        extract=[{"summary": "x"}, {"summary": "y"}],  # missing required key_entities, twice
    )
    with pytest.raises(LLMError):
        _agent(transport).annotate(CURATED, "f.pdf")


def test_transport_failure_raises_llm_error() -> None:
    class _Boom:
        def generate(self, *, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
            raise TransportError("model down")

    with pytest.raises(LLMError):
        _agent(_Boom()).annotate(CURATED, "f.pdf")
