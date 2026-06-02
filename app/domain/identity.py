"""Deterministic, tenant-scoped job identity.

job_id is a persisted idempotency key, so it MUST be stable across processes and
hosts. We use SHA-256 (not Python's salted built-in hash()) over a NUL-delimited
byte sequence for domain separation between the fields.
"""

from __future__ import annotations

import hashlib

_NUL = b"\x00"


def compute_job_id(tenant_id: str, content: bytes, filename: str) -> str:
    """Return the lowercase-hex SHA-256 of tenant_id || 0x00 || filename || 0x00 || content."""
    digest = hashlib.sha256()
    digest.update(tenant_id.encode("utf-8"))
    digest.update(_NUL)
    digest.update(filename.encode("utf-8"))
    digest.update(_NUL)
    digest.update(content)
    return digest.hexdigest()
