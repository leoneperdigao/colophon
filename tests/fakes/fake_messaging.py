"""Test double — the in-app no-infra Messaging adapter, re-exported (one impl)."""

from app.adapters.outbound.messaging.memory import InMemoryMessaging as FakeMessaging

__all__ = ["FakeMessaging"]
