"""Magic-byte detection for the sample downloader (pure; no network)."""

from __future__ import annotations

from samples.download_samples import MANIFEST, detect_kind


def test_detects_pdf() -> None:
    assert detect_kind(b"%PDF-1.7\n...") == "pdf"


def test_detects_xlsx_zip_magic() -> None:
    assert detect_kind(b"PK\x03\x04rest-of-zip") == "xlsx"


def test_rejects_html_error_page() -> None:
    assert detect_kind(b"<!DOCTYPE html><html>404 Not Found</html>") is None


def test_rejects_empty() -> None:
    assert detect_kind(b"") is None


def test_manifest_kinds_are_supported() -> None:
    assert {s.kind for s in MANIFEST} <= {"pdf", "xlsx"}
    assert all(s.url.startswith("https://") for s in MANIFEST)
