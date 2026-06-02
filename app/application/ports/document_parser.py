"""DocumentParser port — raw bytes to curated content (values, never formulas)."""

from __future__ import annotations

from typing import Protocol

from app.domain.stage_result import Curated


class ParseError(Exception):
    """Raised when a document cannot be parsed (corrupt/unsupported/over-limit)."""


class DocumentParser(Protocol):
    def parse(self, content: bytes, content_type: str, filename: str) -> Curated:
        """Parse raw bytes into curated content, or raise ParseError."""
        ...
