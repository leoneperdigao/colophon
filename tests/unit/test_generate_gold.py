"""The gold set's labels must be grounded in (extractable from) the documents."""

from __future__ import annotations

from app.adapters.parsing.factory import build_document_parser
from samples.generate import build_gold_set


def test_gold_set_is_nonempty_and_typed() -> None:
    gold = build_gold_set()
    assert len(gold) >= 6
    assert {s.document_type for s in gold} >= {"invoice", "report", "letter", "spreadsheet"}


def test_includes_a_multi_sheet_workbook() -> None:
    """At least one spreadsheet sample spans multiple sheets, exercising the
    parser's per-sheet concatenation (and keeping the sheet-cap path realistic)."""
    parser = build_document_parser()
    sheet_counts = [
        parser.parse(s.content, s.content_type, s.filename).page_or_sheet_count
        for s in build_gold_set()
        if s.document_type == "spreadsheet"
    ]
    assert sheet_counts, "gold set has no spreadsheet samples"
    assert max(sheet_counts) >= 2


def test_every_label_is_extractable_from_its_document() -> None:
    parser = build_document_parser()
    for sample in build_gold_set():
        curated = parser.parse(sample.content, sample.content_type, sample.filename)
        haystack = curated.text.casefold()
        for _entity_type, value in sample.key_entities:
            assert value.casefold() in haystack, f"{value!r} not found in {sample.filename}"
