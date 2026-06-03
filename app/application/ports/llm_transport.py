"""LLMTransport port — the thin model call the annotation agent depends on.

Given a system prompt, user content, and a JSON schema, return a JSON object.
Implementations (LiteLLM -> Anthropic or Ollama, plus a fake) keep the agent's
classify/extract/validate logic testable without a real model.
"""

from __future__ import annotations

from typing import Any, Protocol


class TransportError(Exception):
    """The model call failed or returned unusable output."""


class LLMTransport(Protocol):
    def generate(self, *, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Return a JSON object conforming (best-effort) to `schema`."""
        ...
