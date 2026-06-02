"""In-memory Messaging adapter — list-backed queue, no-infra profile."""

from __future__ import annotations

from collections.abc import Callable

from app.application.ports.messaging import WorkMessage


class InMemoryMessaging:
    def __init__(self) -> None:
        self.enqueued: list[WorkMessage] = []

    def enqueue(self, message: WorkMessage) -> None:
        self.enqueued.append(message)

    def consume(self, handler: Callable[[WorkMessage], None]) -> None:
        """Drain synchronously (deterministic for tests / single-shot local runs)."""
        while self.enqueued:
            handler(self.enqueued.pop(0))
