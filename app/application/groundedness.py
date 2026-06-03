"""Deterministic groundedness: extracted values must appear in the curated text.

A pure function (no IO, no LLM) reused by the annotation agent (to flag/penalise
fabricated values) and by the eval harness. Ungrounded values are flagged and
lower the reported confidence proportionally — fail loud, not silent.
"""

from __future__ import annotations

from dataclasses import replace

from app.domain.annotation import Annotation
from app.domain.key_entity import KeyEntity


def ground_annotation(annotation: Annotation, curated_text: str) -> Annotation:
    """Return a copy with entity `grounded` flags, `ungrounded_fields`, and an
    adjusted `confidence` (lowered by the fraction of ungrounded entities)."""
    haystack = curated_text.casefold()

    checked: list[KeyEntity] = []
    ungrounded: list[str] = []
    for entity in annotation.key_entities:
        is_grounded = bool(entity.value) and entity.value.casefold() in haystack
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
