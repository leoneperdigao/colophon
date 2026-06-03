"""Environment-driven configuration (no secrets in code)."""

from __future__ import annotations

import os

from app.adapters.parsing.content_types import SUPPORTED


def int_env(name: str, default: int) -> int:
    """Read a positive integer from the environment, falling back on absent/invalid."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


# Upload limits (untrusted input — Constitution IV). Tunable per deployment; the
# default (10 MiB) comfortably covers PDFs/spreadsheets at this scope. See ADR-0011
# for file-size handling and the scaling path (stream-to-blob / presigned upload).
MAX_UPLOAD_BYTES = int_env("MAX_UPLOAD_BYTES", 10 * 1024 * 1024)

# Accept only what the parser supports (single source of truth).
ALLOWED_CONTENT_TYPES = SUPPORTED


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
