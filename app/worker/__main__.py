"""Worker process entrypoint (`python -m app.worker`).

Builds the container from the environment and runs the consume loop. In the
`local` profile this blocks on RabbitMQ, processing each job through the pipeline.
"""

from __future__ import annotations

from app.config.container import Container
from app.worker.main import run

if __name__ == "__main__":
    run(Container.from_env())
