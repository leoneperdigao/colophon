"""Stub LLMClient — deterministic, schema-valid Annotation (no-infra profile).

The real LiteLLM -> Anthropic tool-use adapter replaces this in the LLM phase.
"""

from __future__ import annotations

from app.application.ports.llm_client import LLMError
from app.domain.annotation import Annotation
from app.domain.key_entity import KeyEntity
from app.domain.stage_result import Curated


class StubLLM:
    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail

    def annotate(self, curated: Curated, source_filename: str) -> Annotation:
        if self._fail:
            raise LLMError("annotation failed")
        words = curated.text.split()
        entities = [KeyEntity(type="other", value=words[0], grounded=True)] if words else []
        return Annotation(
            summary=curated.text[:80],
            document_type="other",
            key_entities=entities,
            language="en",
            source_filename=source_filename,
            page_or_sheet_count=curated.page_or_sheet_count,
            confidence=0.9,
            extracted_at="2026-06-02T00:00:00Z",
            ungrounded_fields=[],
        )
