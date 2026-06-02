"""Auth: Bearer token -> tenant resolution (pure). T014."""

from __future__ import annotations

from app.adapters.inbound.http.auth import resolve_tenant

TOKEN_MAP = {"tokenA": "tenant-a", "tokenB": "tenant-b"}


def test_known_token_resolves_to_tenant() -> None:
    assert resolve_tenant(TOKEN_MAP, "tokenA") == "tenant-a"
    assert resolve_tenant(TOKEN_MAP, "tokenB") == "tenant-b"


def test_unknown_token_is_none() -> None:
    assert resolve_tenant(TOKEN_MAP, "nope") is None


def test_missing_token_is_none() -> None:
    assert resolve_tenant(TOKEN_MAP, None) is None
    assert resolve_tenant(TOKEN_MAP, "") is None
