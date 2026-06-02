"""BlobStore port — raw, immutable original uploads (tenant-prefixed keys)."""

from __future__ import annotations

from typing import Protocol


class BlobStore(Protocol):
    def put_raw(self, tenant_id: str, job_id: str, filename: str, content: bytes) -> str:
        """Store the raw upload and return its key. Idempotent on (tenant, job, filename)."""
        ...

    def get_raw(self, tenant_id: str, job_id: str) -> bytes:
        """Fetch the raw bytes for a job within a tenant."""
        ...
