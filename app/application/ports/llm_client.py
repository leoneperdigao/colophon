"""LLMClient port — bounded annotation (classify -> extract -> validate/repair).

Document content is untrusted data; implementations MUST constrain output to the
strict annotation schema and MUST NOT expose tools or side effects.
"""

from __future__ import annotations

from typing import Protocol

from app.domain.annotation import Annotation
from app.domain.stage_result import Curated


class LLMError(Exception):
    """Raised when annotation cannot produce a schema-valid result."""


class LLMClient(Protocol):
    def annotate(self, curated: Curated, source_filename: str) -> Annotation:
        """Produce a schema-valid Annotation grounded in the curated content."""
        ...
