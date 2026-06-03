"""Background worker entrypoint — consumes work and runs the pipeline."""

from __future__ import annotations

from app.config.container import Container
from app.observability import configure_logging


def run(container: Container) -> None:
    """Consume work messages, processing each through the pipeline."""
    configure_logging()
    container.messaging.consume(container.process.execute)
