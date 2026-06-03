"""PdfParser adapter tests — real pypdf, generated PDFs. T042."""

from __future__ import annotations

import pytest
from fpdf import FPDF

from app.adapters.parsing.pdf import PdfParser
from app.application.ports.document_parser import ParseError

PDF = "application/pdf"


def _make_pdf(pages: list[str]) -> bytes:
    pdf = FPDF()
    for text in pages:
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.cell(0, 10, text)
    return bytes(pdf.output())


def test_extracts_text_and_page_count() -> None:
    curated = PdfParser().parse(_make_pdf(["Invoice from ACME", "second page"]), PDF, "f.pdf")
    assert "ACME" in curated.text
    assert curated.page_or_sheet_count == 2


def test_rejects_documents_over_the_page_cap() -> None:
    with pytest.raises(ParseError):
        PdfParser(max_pages=2).parse(_make_pdf(["a", "b", "c"]), PDF, "big.pdf")


def test_corrupt_pdf_raises_user_safe_parse_error() -> None:
    with pytest.raises(ParseError) as exc_info:
        PdfParser().parse(b"this is not a pdf", PDF, "SECRET-NAME.pdf")
    message = str(exc_info.value)
    assert message == "could not read the PDF document"  # stable, no internals
    assert "SECRET-NAME" not in message  # client-supplied filename not echoed
    assert exc_info.value.__cause__ is not None  # detail preserved as chained cause (logs only)
