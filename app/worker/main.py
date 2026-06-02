"""Background worker entrypoint — consumes work and runs the pipeline."""

from __future__ import annotations

from app.config.container import Container


def run(container: Container) -> None:
    """Consume work messages, processing each through the pipeline."""
    container.messaging.consume(container.process.execute)
