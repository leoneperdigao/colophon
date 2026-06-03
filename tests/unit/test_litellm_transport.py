"""JSON-object parsing for the LiteLLM transport (pure; no model call)."""

from __future__ import annotations

import pytest

from app.adapters.llm.litellm_transport import parse_json_object
from app.application.ports.llm_transport import TransportError


def test_parses_plain_json_object() -> None:
    assert parse_json_object('{"a": 1, "b": "x"}') == {"a": 1, "b": "x"}


def test_extracts_object_from_surrounding_prose() -> None:
    assert parse_json_object('Sure! Here you go: {"a": 1} — hope that helps') == {"a": 1}


def test_extracts_object_from_code_fence() -> None:
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}


def test_rejects_non_object_json() -> None:
    with pytest.raises(TransportError):
        parse_json_object("[1, 2, 3]")


def test_rejects_unparseable_or_empty() -> None:
    with pytest.raises(TransportError):
        parse_json_object("not json at all")
    with pytest.raises(TransportError):
        parse_json_object("")
