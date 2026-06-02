"""Upload filename normalization (untrusted input). PR#3 review fix."""

from __future__ import annotations

from app.adapters.inbound.http.uploads import safe_filename


def test_strips_windows_path() -> None:
    assert safe_filename("C:\\fakepath\\report.pdf") == "report.pdf"


def test_strips_posix_path() -> None:
    assert safe_filename("/etc/passwd") == "passwd"
    assert safe_filename("a/b/c.xlsx") == "c.xlsx"


def test_strips_mixed_separators() -> None:
    assert safe_filename("foo/bar\\baz.pdf") == "baz.pdf"


def test_empty_or_pathonly_falls_back() -> None:
    assert safe_filename("") == "upload"
    assert safe_filename(None) == "upload"
    assert safe_filename("/") == "upload"
