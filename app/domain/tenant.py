"""Tenant — the access boundary, established by the credential (never client-supplied)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Tenant:
    tenant_id: str
    scopes: frozenset[str] = field(default_factory=frozenset)
