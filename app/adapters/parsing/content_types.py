"""Supported document content types (single source of truth)."""

from __future__ import annotations

PDF = "application/pdf"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

SUPPORTED: frozenset[str] = frozenset({PDF, XLSX})
