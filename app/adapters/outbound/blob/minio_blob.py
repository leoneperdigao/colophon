"""MinIO (S3 API) BlobStore adapter — raw, immutable, tenant-prefixed keys.

Swaps the cloud target to S3 with no code change (the SDK speaks the same API).
`minio` is an optional `infra` extra, so this module is imported only by the
composition root's local profile, never in the in-memory/CI path.
"""

from __future__ import annotations

from io import BytesIO

from minio import Minio
from minio.error import S3Error

from app.application.ports.blob_store import BlobNotFound

_MISSING_CODES = frozenset({"NoSuchKey", "NoSuchObject"})


class MinioBlobStore:
    def __init__(
        self,
        *,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
    ) -> None:
        self._client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
        self._bucket = bucket
        if not self._client.bucket_exists(bucket):
            self._client.make_bucket(bucket)

    @staticmethod
    def _key(tenant_id: str, job_id: str) -> str:
        return f"{tenant_id}/raw/{job_id}"

    def put_raw(self, tenant_id: str, job_id: str, filename: str, content: bytes) -> str:
        key = self._key(tenant_id, job_id)
        # job_id is content-addressed (SHA-256 of tenant+filename+content), so any two
        # writes to the same key carry identical bytes. A single PUT is atomic and
        # idempotent — "first write wins" without a racy check-then-put.
        self._client.put_object(self._bucket, key, BytesIO(content), length=len(content))
        return key

    def get_raw(self, tenant_id: str, job_id: str) -> bytes:
        key = self._key(tenant_id, job_id)
        try:
            response = self._client.get_object(self._bucket, key)
        except S3Error as exc:
            if exc.code in _MISSING_CODES:
                raise BlobNotFound(f"no raw blob for {tenant_id}/{job_id}") from exc
            raise  # permission / bucket / network — surface it, don't mask as "missing"
        try:
            data: bytes = response.read()
            return data
        finally:
            response.close()
            response.release_conn()
