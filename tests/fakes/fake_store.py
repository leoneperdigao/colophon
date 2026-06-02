"""Test double — the in-app no-infra AnnotationStore adapter, re-exported (one impl)."""

from app.adapters.outbound.store.memory import InMemoryAnnotationStore as FakeAnnotationStore

__all__ = ["FakeAnnotationStore"]
