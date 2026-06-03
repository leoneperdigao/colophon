"""TimeoutParser decorator — wall-clock budget around parsing. Input hardening."""

from __future__ import annotations

import time

import pytest

from app.adapters.parsing.timeout import TimeoutParser
from app.application.ports.document_parser import ParseError
from app.domain.stage_result import Curated


class _FastParser:
    def parse(self, content: bytes, content_type: str, filename: str) -> Curated:
        return Curated(text=content.decode(), page_or_sheet_count=1)


class _SlowParser:
    def parse(self, content: bytes, content_type: str, filename: str) -> Curated:
        time.sleep(5)  # far longer than any test budget; daemon thread, never awaited fully
        return Curated(text="", page_or_sheet_count=1)


class _BoomParser:
    def parse(self, content: bytes, content_type: str, filename: str) -> Curated:
        raise ParseError("inner failure")


def test_returns_result_when_under_budget() -> None:
    curated = TimeoutParser(_FastParser(), timeout_seconds=1.0).parse(b"hello", "text/plain", "f")
    assert curated.text == "hello"


def test_raises_parse_error_when_budget_exceeded() -> None:
    with pytest.raises(ParseError) as exc_info:
        TimeoutParser(_SlowParser(), timeout_seconds=0.1).parse(b"x", "application/pdf", "f.pdf")
    assert "timed out" in str(exc_info.value)


def test_propagates_inner_parse_error() -> None:
    with pytest.raises(ParseError) as exc_info:
        TimeoutParser(_BoomParser(), timeout_seconds=1.0).parse(b"x", "application/pdf", "f.pdf")
    assert "inner failure" in str(exc_info.value)
