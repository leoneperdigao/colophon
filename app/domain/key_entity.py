"""KeyEntity — a typed value extracted from a document, expected to be grounded."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KeyEntity:
    type: str  # org | person | date | amount | other
    value: str
    grounded: bool = False
