"""DocumentParserRouter — dispatch by content-type. T042."""

from __future__ import annotations

from io import BytesIO

import pytest
from fpdf import FPDF
from openpyxl import Workbook

from app.adapters.parsing.pdf import PdfParser
from app.adapters.parsing.router import DocumentParserRouter
from app.adapters.parsing.spreadsheet import SpreadsheetParser
from app.application.ports.document_parser import ParseError

PDF = "application/pdf"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _router() -> DocumentParserRouter:
    return DocumentParserRouter(pdf=PdfParser(), spreadsheet=SpreadsheetParser())


def _pdf_bytes(text: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, text)
    return bytes(pdf.output())


def _xlsx_bytes(value: str) -> bytes:
    wb = Workbook()
    wb.active["A1"] = value
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def test_routes_pdf_to_pdf_parser() -> None:
    curated = _router().parse(_pdf_bytes("hello pdf"), PDF, "f.pdf")
    assert "hello" in curated.text.lower()


def test_routes_spreadsheet_to_spreadsheet_parser() -> None:
    curated = _router().parse(_xlsx_bytes("hello sheet"), XLSX, "f.xlsx")
    assert "hello sheet" in curated.text


def test_unsupported_content_type_raises_parse_error() -> None:
    with pytest.raises(ParseError):
        _router().parse(b"data", "application/zip", "f.zip")
