"""Deterministic groundedness: extracted values must appear in the curated text.

A pure function (no IO, no LLM) reused by the annotation agent (to flag/penalise
fabricated values) and by the eval harness. Ungrounded values are flagged and
lower the reported confidence proportionally — fail loud, not silent.

Matching is **normalization-aware** to cut the two failure modes of naive
case-insensitive substring containment:

  * *false positives on short values* — a 1-3 character value like "IT" or "5"
    would otherwise match inside an unrelated word/number ("aud**it**", "**1**0");
    short values require a word/number boundary.
  * *false negatives on numeric formatting* — "USD 1,000.00" vs "1000", "1,500"
    vs "1500" — numbers are also compared in a canonical digits-only form, and
    `/` date separators are folded to `-` (2026/01/15 ≡ 2026-01-15).

Residual, deliberately-out-of-scope limitations (documented, not silently wrong):
textual-month dates ("January 1, 2024" vs "2024-01-01") and locale decimal commas
("1.000,00") are not reconciled and will flag ungrounded. The cheap next step is a
per-locale date/number canonicaliser; see README (Evaluation).
"""

from __future__ import annotations

import re
from dataclasses import replace

from app.domain.annotation import Annotation
from app.domain.key_entity import KeyEntity

_THOUSANDS = re.compile(r"(?<=\d),(?=\d)")  # comma between digits: 1,000 -> 1000
_DATE_SLASH = re.compile(r"(?<=\d)/(?=\d)")  # slash between digits: 2026/01/15 -> 2026-01-15
_LOCALE_DECIMAL = re.compile(r",\d{1,2}(?!\d)")  # decimal comma: 1500,00 / 1.000,00 / 12,5
_SHORT = 4  # values shorter than this must match on a boundary, not a raw substring


def _normalize(text: str) -> str:
    """Casefold and fold numeric formatting that carries no meaning for grounding."""
    folded = text.casefold()
    folded = _THOUSANDS.sub("", folded)
    return _DATE_SLASH.sub("-", folded)


def _canonical_number(value: str) -> str | None:
    """Digits-only canonical form of a value (currency/separators stripped, trailing
    decimal zeros removed), or None if the value carries no number."""
    digits = re.sub(r"[^\d.]", "", value.replace(",", ""))
    if not any(ch.isdigit() for ch in digits):
        return None
    if "." in digits:
        digits = digits.rstrip("0").rstrip(".")
    return digits or None


def _contains(needle: str, haystack: str) -> bool:
    if not needle:
        return False
    if len(needle) >= _SHORT:
        return needle in haystack
    # Short value: require a boundary so "it" doesn't match inside "audit",
    # nor "1" inside "10". \b is unreliable around symbols, so guard explicitly.
    return re.search(rf"(?<![0-9a-z]){re.escape(needle)}(?![0-9a-z])", haystack) is not None


def _is_grounded(value: str, haystack: str, raw: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return False
    if _LOCALE_DECIMAL.search(stripped):
        # Locale decimal-comma ("1500,00", "1.000,00") is ambiguous against US
        # thousands grouping — numeric normalization would mangle it (1500,00 ->
        # 150000) and could falsely ground. Documented non-goal: only a *verbatim*
        # case-insensitive match grounds it (checked against the raw text), so a
        # different number can never match.
        return stripped.casefold() in raw
    if _contains(_normalize(stripped), haystack):
        return True
    number = _canonical_number(stripped)
    return number is not None and _contains(number, haystack)


def ground_annotation(annotation: Annotation, curated_text: str) -> Annotation:
    """Return a copy with entity `grounded` flags, `ungrounded_fields`, and an
    adjusted `confidence` (lowered by the fraction of ungrounded entities)."""
    haystack = _normalize(curated_text)
    raw = curated_text.casefold()

    checked: list[KeyEntity] = []
    ungrounded: list[str] = []
    for entity in annotation.key_entities:
        is_grounded = _is_grounded(entity.value, haystack, raw)
        checked.append(replace(entity, grounded=is_grounded))
        if not is_grounded:
            ungrounded.append(entity.value)

    total = len(checked)
    ungrounded_ratio = (len(ungrounded) / total) if total else 0.0
    confidence = round(annotation.confidence * (1.0 - ungrounded_ratio), 4)

    return replace(
        annotation,
        key_entities=checked,
        ungrounded_fields=ungrounded,
        confidence=confidence,
    )
