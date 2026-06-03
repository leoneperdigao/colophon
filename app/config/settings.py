"""Environment-driven configuration (no secrets in code)."""

from __future__ import annotations

import os

from app.adapters.parsing.content_types import SUPPORTED

# Upload limits (untrusted input — Constitution IV).
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MiB

# Accept only what the parser supports (single source of truth).
ALLOWED_CONTENT_TYPES = SUPPORTED


def llm_model() -> str:
    """LiteLLM model id. Defaults to a local Ollama model for infra-free testing;
    set e.g. `anthropic/claude-3-5-haiku-latest` (+ ANTHROPIC_API_KEY) for cloud."""
    return os.getenv("LLM_MODEL", "ollama/llama3.1")


def llm_api_base() -> str | None:
    """Optional provider base URL (e.g. a non-default Ollama host)."""
    return os.getenv("LLM_API_BASE") or os.getenv("OLLAMA_API_BASE") or None


def load_token_map(raw: str | None = None) -> dict[str, str]:
    """Parse `TENANT_TOKENS` of the form 'tokenA:tenant-a,tokenB:tenant-b'."""
    raw = raw if raw is not None else os.getenv("TENANT_TOKENS", "")
    token_map: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair:
            continue
        token, _, tenant = pair.partition(":")
        token, tenant = token.strip(), tenant.strip()
        if token and tenant:
            token_map[token] = tenant
    return token_map
