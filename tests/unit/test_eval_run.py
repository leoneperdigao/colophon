"""Eval harness end-to-end (real parser over the generated gold set, injected LLM)."""

from __future__ import annotations

from app.domain.annotation import Annotation
from app.domain.key_entity import KeyEntity
from app.domain.stage_result import Curated
from eval.metrics import Thresholds
from eval.run import evaluate
from samples.generate import build_gold_set


class _OracleLLM:
    """Returns the gold answer for each document — a perfect annotator."""

    def __init__(self) -> None:
        self._gold = {s.filename: s for s in build_gold_set()}

    def annotate(self, curated: Curated, source_filename: str) -> Annotation:
        sample = self._gold[source_filename]
        entities = [KeyEntity(type=t, value=v, grounded=True) for t, v in sample.key_entities]
        return Annotation(
            summary="",
            document_type=sample.document_type,
            key_entities=entities,
            language="en",
            source_filename=source_filename,
            page_or_sheet_count=curated.page_or_sheet_count,
            confidence=1.0,
            extracted_at="2026-06-03T00:00:00Z",
            ungrounded_fields=[],
        )


class _BadLLM:
    def annotate(self, curated: Curated, source_filename: str) -> Annotation:
        return Annotation(
            summary="",
            document_type="other",  # wrong type
            key_entities=[KeyEntity(type="org", value="WRONG")],  # fabricated
            language="en",
            source_filename=source_filename,
            page_or_sheet_count=1,
            confidence=0.5,
            extracted_at="2026-06-03T00:00:00Z",
            ungrounded_fields=["WRONG"],
        )


def test_oracle_passes_all_thresholds() -> None:
    report = evaluate(_OracleLLM())
    assert report.count == len(build_gold_set())
    assert report.passes(Thresholds())


def test_bad_predictions_fail_thresholds() -> None:
    report = evaluate(_BadLLM())
    assert not report.passes(Thresholds())
