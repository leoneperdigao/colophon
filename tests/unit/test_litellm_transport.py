"""JSON-object parsing for the LiteLLM transport (pure; no model call)."""

from __future__ import annotations

import sys
import types

import pytest

from app.adapters.llm.litellm_transport import LiteLLMTransport, parse_json_object
from app.application.ports.llm_transport import TransportError


def _fake_litellm(monkeypatch: pytest.MonkeyPatch, completion: object) -> None:
    """Inject a stand-in `litellm` module so the transport is testable without the
    optional 'llm' extra installed (the real module is imported lazily)."""
    fake = types.ModuleType("litellm")
    fake.completion = completion  # type: ignore[attr-defined]
    fake.get_supported_openai_params = lambda model: []  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "litellm", fake)


def test_provider_error_detail_is_surfaced_in_the_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A bad model id / auth / billing failure must not collapse to a bare
    # "LLM call failed" — the provider's message has to reach the logs so the
    # cause is diagnosable (the client-facing message stays generic upstream).
    def boom(**kwargs: object) -> object:
        raise ValueError("model 'gpt-nope' not found: invalid model id")

    _fake_litellm(monkeypatch, boom)
    transport = LiteLLMTransport(model="gpt-nope")
    with pytest.raises(TransportError) as excinfo:
        transport.generate(system="s", user="u", schema={})
    message = str(excinfo.value)
    assert "invalid model id" in message  # provider detail preserved
    assert "ValueError" in message  # and its type, for triage
    assert excinfo.value.__cause__ is not None  # original exception chained


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
