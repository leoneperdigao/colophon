"""BlobStore port — raw, immutable original uploads (tenant-prefixed keys)."""

from __future__ import annotations

from typing import Protocol


class BlobNotFound(Exception):
    """Raised by get_raw when no object exists for (tenant, job)."""


class BlobStore(Protocol):
    def put_raw(self, tenant_id: str, job_id: str, filename: str, content: bytes) -> str:
        """Store the raw upload and return its key.

        The object is addressed by ``(tenant_id, job_id)`` (the key is
        ``{tenant_id}/raw/{job_id}``); ``filename`` is incidental metadata, not part
        of the key. Because ``job_id`` is content-addressed, writes for the same key
        are identical — put_raw is idempotent.
        """
        ...

    def get_raw(self, tenant_id: str, job_id: str) -> bytes:
        """Fetch the raw bytes for a job within a tenant, or raise BlobNotFound."""
        ...
