"""Messaging port — work handoff (queue) and stage events.

Carries tenant_id + job_id in metadata so the worker stays tenant-scoped.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class WorkMessage:
    tenant_id: str
    job_id: str


class Messaging(Protocol):
    def enqueue(self, message: WorkMessage) -> None:
        """Enqueue a unit of work for the pipeline."""
        ...

    def consume(self, handler: Callable[[WorkMessage], None]) -> None:
        """Consume work messages, invoking handler for each (blocking in real adapters)."""
        ...
