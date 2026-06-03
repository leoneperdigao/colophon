"""PDF DocumentParser adapter (pypdf). Untrusted input: bounded + fail-soft."""

from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

from app.application.ports.document_parser import ParseError
from app.domain.stage_result import Curated


class PdfParser:
    def __init__(self, *, max_pages: int = 50) -> None:
        self._max_pages = max_pages

    def parse(self, content: bytes, content_type: str, filename: str) -> Curated:
        try:
            reader = PdfReader(BytesIO(content))
            page_count = len(reader.pages)
            if page_count > self._max_pages:
                raise ParseError(f"PDF {filename} has {page_count} pages (cap {self._max_pages})")
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        except ParseError:
            raise
        except Exception as exc:  # any malformed/abusive input -> graceful parse failure
            raise ParseError(f"cannot read PDF {filename}: {exc}") from exc
        return Curated(text=text, page_or_sheet_count=page_count, structure={"pages": page_count})
