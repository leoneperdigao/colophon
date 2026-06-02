"""Environment-driven configuration (no secrets in code)."""

from __future__ import annotations

import os

# Upload limits (untrusted input — Constitution IV).
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MiB

ALLOWED_CONTENT_TYPES = frozenset(
    {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
        "application/vnd.ms-excel",  # .xls
        "text/csv",
    }
)


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
