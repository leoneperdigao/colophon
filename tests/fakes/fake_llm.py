"""Test double — the in-app stub LLMClient, re-exported (one impl)."""

from app.adapters.llm.stub import StubLLM as FakeLLM

__all__ = ["FakeLLM"]
