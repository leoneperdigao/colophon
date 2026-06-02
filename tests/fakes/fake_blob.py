"""Test double — the in-app no-infra BlobStore adapter, re-exported (one impl)."""

from app.adapters.outbound.blob.memory import InMemoryBlobStore as FakeBlobStore

__all__ = ["FakeBlobStore"]
