"""Stub DocumentParser — decodes bytes to text (no-infra profile / walking skeleton).

The real pdf/spreadsheet adapters replace this in the parsing phase.
"""

from __future__ import annotations

from app.application.ports.document_parser import ParseError
from app.domain.stage_result import Curated


class StubParser:
    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail

    def parse(self, content: bytes, content_type: str, filename: str) -> Curated:
        if self._fail or content == b"":
            raise ParseError("could not parse the document")
        return Curated(text=content.decode("utf-8", errors="replace"), page_or_sheet_count=1)
