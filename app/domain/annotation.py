"""Annotation — the final structured metadata (the retrievable result)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.key_entity import KeyEntity


@dataclass
class Annotation:
    summary: str
    document_type: str  # invoice | report | spreadsheet | letter | other
    key_entities: list[KeyEntity]
    language: str
    source_filename: str
    page_or_sheet_count: int
    confidence: float
    extracted_at: str  # ISO-8601
    ungrounded_fields: list[str] = field(default_factory=list)
