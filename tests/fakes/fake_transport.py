"""Scripted LLMTransport fake — routes by schema (classify vs extract)."""

from __future__ import annotations

from typing import Any


class FakeTransport:
    def __init__(
        self,
        *,
        classify: dict[str, Any],
        extract: dict[str, Any] | list[dict[str, Any]],
    ) -> None:
        self._classify = classify
        self._extract = extract if isinstance(extract, list) else [extract]
        self._extract_calls = 0
        self.calls: list[dict[str, Any]] = []

    def generate(self, *, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        self.calls.append({"system": system, "user": user, "schema": schema})
        if "key_entities" in schema.get("properties", {}):
            response = self._extract[min(self._extract_calls, len(self._extract) - 1)]
            self._extract_calls += 1
            return response
        return self._classify
