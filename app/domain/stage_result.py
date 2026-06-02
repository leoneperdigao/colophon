"""Curated stage result — parsed/normalised content produced before annotation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Curated:
    text: str
    page_or_sheet_count: int
    structure: dict[str, Any] = field(default_factory=dict)
    detected_type_hint: str | None = None
