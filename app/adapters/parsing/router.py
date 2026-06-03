"""DocumentParserRouter — dispatch to the format-specific parser by content type."""

from __future__ import annotations

from app.adapters.parsing.content_types import PDF, XLSX
from app.application.ports.document_parser import DocumentParser, ParseError
from app.domain.stage_result import Curated


class DocumentParserRouter:
    def __init__(self, *, pdf: DocumentParser, spreadsheet: DocumentParser) -> None:
        self._pdf = pdf
        self._spreadsheet = spreadsheet

    def parse(self, content: bytes, content_type: str, filename: str) -> Curated:
        if content_type == PDF:
            return self._pdf.parse(content, content_type, filename)
        if content_type == XLSX:
            return self._spreadsheet.parse(content, content_type, filename)
        raise ParseError(f"unsupported content-type: {content_type}")
