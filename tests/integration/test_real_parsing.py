"""Real parser through the pipeline — app wired to the parser router, no infra.

Proves the PDF/spreadsheet adapters integrate with the pipeline end-to-end: a real
document's extracted text reaches the annotation (the stub LLM summarises curated
text, so seeing the document's words in the summary proves real parsing ran).
"""

from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
from fpdf import FPDF
from openpyxl import Workbook

from app.adapters.inbound.http.app import create_app
from app.adapters.llm.stub import StubLLM
from app.adapters.outbound.blob.memory import InMemoryBlobStore
from app.adapters.outbound.messaging.memory import InMemoryMessaging
from app.adapters.outbound.store.memory import InMemoryAnnotationStore
from app.adapters.parsing.content_types import PDF, XLSX
from app.adapters.parsing.pdf import PdfParser
from app.adapters.parsing.router import DocumentParserRouter
from app.adapters.parsing.spreadsheet import SpreadsheetParser
from app.config.container import Container
from app.worker.main import run as run_worker

AUTH = {"Authorization": "Bearer tokenA"}


def _container() -> Container:
    return Container(
        token_map={"tokenA": "tenant-a"},
        blob=InMemoryBlobStore(),
        store=InMemoryAnnotationStore(),
        messaging=InMemoryMessaging(),
        parser=DocumentParserRouter(pdf=PdfParser(), spreadsheet=SpreadsheetParser()),
        llm=StubLLM(),
    )


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


def _run(content: bytes, filename: str, content_type: str) -> dict[str, object]:
    container = _container()
    client = TestClient(create_app(container))
    job_id = client.post(
        "/documents", headers=AUTH, files={"file": (filename, content, content_type)}
    ).json()["job_id"]
    run_worker(container)
    return client.get(f"/annotations/{job_id}", headers=AUTH).json()


def test_real_pdf_flows_to_annotation() -> None:
    body = _run(_pdf_bytes("Invoice from ACME"), "invoice.pdf", PDF)
    assert body["status"] == "completed"
    assert "ACME" in body["result"]["summary"]


def test_real_spreadsheet_flows_to_annotation() -> None:
    body = _run(_xlsx_bytes("QuarterlyTotals"), "data.xlsx", XLSX)
    assert body["status"] == "completed"
    assert "QuarterlyTotals" in body["result"]["summary"]
