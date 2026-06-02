"""In-memory BlobStore adapter — the no-infra profile (also reused as a test double)."""

from __future__ import annotations

from app.application.ports.blob_store import BlobNotFound


class InMemoryBlobStore:
    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}
        self._index: dict[tuple[str, str], str] = {}

    @staticmethod
    def _key(tenant_id: str, job_id: str, filename: str) -> str:
        return f"{tenant_id}/raw/{job_id}/{filename}"

    def put_raw(self, tenant_id: str, job_id: str, filename: str, content: bytes) -> str:
        key = self._key(tenant_id, job_id, filename)
        self._objects.setdefault(key, content)  # immutable: first write wins
        self._index[(tenant_id, job_id)] = key
        return key

    def get_raw(self, tenant_id: str, job_id: str) -> bytes:
        try:
            return self._objects[self._index[(tenant_id, job_id)]]
        except KeyError as exc:
            raise BlobNotFound(f"no raw blob for {tenant_id}/{job_id}") from exc
