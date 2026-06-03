"""Assemble the production DocumentParser: timeout(router(pdf, spreadsheet))."""

from __future__ import annotations

from app.adapters.parsing.pdf import PdfParser
from app.adapters.parsing.router import DocumentParserRouter
from app.adapters.parsing.spreadsheet import SpreadsheetParser
from app.adapters.parsing.timeout import TimeoutParser
from app.application.ports.document_parser import DocumentParser


def build_document_parser(*, parse_timeout_seconds: float = 30.0) -> DocumentParser:
    """The real parser stack: content-type routing, per-format caps, wall-clock timeout."""
    return TimeoutParser(
        DocumentParserRouter(pdf=PdfParser(), spreadsheet=SpreadsheetParser()),
        timeout_seconds=parse_timeout_seconds,
    )
