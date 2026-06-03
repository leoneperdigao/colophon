"""Assemble the production annotator: AnnotationAgent over a LiteLLM transport."""

from __future__ import annotations

from app.adapters.llm.agent import AnnotationAgent
from app.adapters.llm.litellm_transport import LiteLLMTransport
from app.application.ports.llm_client import LLMClient
from app.config import settings


def build_annotator() -> LLMClient:
    """The real LLM stack: a bounded agent over LiteLLM (Anthropic or Ollama by env)."""
    transport = LiteLLMTransport(model=settings.llm_model(), api_base=settings.llm_api_base())
    return AnnotationAgent(transport)
