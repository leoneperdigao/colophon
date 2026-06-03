"""build_annotator wiring — selects the offline stub or the real agent by model id.

Both paths are exercised without a model server: the stub returns immediately, and
the real path only *constructs* the agent/transport (the provider is called lazily,
on the first annotate, which these tests never trigger).
"""

from __future__ import annotations

import pytest

from app.adapters.llm.agent import AnnotationAgent
from app.adapters.llm.factory import build_annotator
from app.adapters.llm.stub import StubLLM


def test_stub_model_selects_offline_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODEL", "stub")
    assert isinstance(build_annotator(), StubLLM)


def test_real_model_builds_the_bounded_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODEL", "anthropic/claude-3-5-haiku-latest")
    monkeypatch.delenv("LLM_API_BASE", raising=False)
    assert isinstance(build_annotator(), AnnotationAgent)
