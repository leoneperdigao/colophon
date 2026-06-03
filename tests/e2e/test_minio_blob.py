"""MinIO BlobStore adapter — real infra (opt-in). Skipped without MinIO + the infra extra.

Run: `make up` (or a MinIO container), then `pytest tests/e2e/test_minio_blob.py`.
"""

from __future__ import annotations

import os
import uuid

import pytest

pytest.importorskip("minio")  # skip cleanly when the 'infra' extra isn't installed (CI)

import urllib3.exceptions  # noqa: E402  (minio's HTTP layer; available once minio is)

from app.adapters.outbound.blob.minio_blob import MinioBlobStore  # noqa: E402
from app.application.ports.blob_store import BlobNotFound  # noqa: E402


@pytest.fixture
def store() -> MinioBlobStore:
    try:
        return MinioBlobStore(
            endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            bucket=os.getenv("MINIO_BUCKET", "colophon-test"),
            secure=False,
        )
    except urllib3.exceptions.MaxRetryError as exc:  # only "can't connect" -> opt-in skip
        pytest.skip(f"MinIO not reachable: {exc}")


def test_put_then_get_roundtrip(store: MinioBlobStore) -> None:
    job = uuid.uuid4().hex
    key = store.put_raw("t1", job, "f.pdf", b"hello world")
    assert key == f"t1/raw/{job}"
    assert store.get_raw("t1", job) == b"hello world"


def test_missing_raises_blob_not_found(store: MinioBlobStore) -> None:
    with pytest.raises(BlobNotFound):
        store.get_raw("t1", "does-not-exist-" + uuid.uuid4().hex)


def test_keys_are_tenant_scoped(store: MinioBlobStore) -> None:
    job = uuid.uuid4().hex  # same job id, different tenants -> isolated objects
    store.put_raw("tenant-a", job, "f", b"AAA")
    store.put_raw("tenant-b", job, "f", b"BBB")
    assert store.get_raw("tenant-a", job) == b"AAA"
    assert store.get_raw("tenant-b", job) == b"BBB"


def test_raw_is_immutable_first_write_wins(store: MinioBlobStore) -> None:
    job = uuid.uuid4().hex
    store.put_raw("t1", job, "f", b"first")
    store.put_raw("t1", job, "f", b"second")  # ignored
    assert store.get_raw("t1", job) == b"first"
