"""In-memory BlobStore adapter — the no-infra profile (also reused as a test double)."""

from __future__ import annotations

from app.application.ports.blob_store import BlobNotFound


class InMemoryBlobStore:
    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    @staticmethod
    def _key(tenant_id: str, job_id: str) -> str:
        return f"{tenant_id}/raw/{job_id}"  # addressed by (tenant, job); matches the MinIO adapter

    def put_raw(self, tenant_id: str, job_id: str, filename: str, content: bytes) -> str:
        key = self._key(tenant_id, job_id)
        self._objects[key] = content  # content-addressed -> idempotent (same key ⇒ same bytes)
        return key

    def get_raw(self, tenant_id: str, job_id: str) -> bytes:
        try:
            return self._objects[self._key(tenant_id, job_id)]
        except KeyError as exc:
            raise BlobNotFound(f"no raw blob for {tenant_id}/{job_id}") from exc
