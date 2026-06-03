"""FastAPI application factory."""

from fastapi import FastAPI

from app.adapters.inbound.http import annotations, documents
from app.config.container import Container


def create_app(container: Container) -> FastAPI:
    # Logging configuration is owned by the process entrypoint, not this factory.
    app = FastAPI(title="Document Annotation Service")
    app.state.container = container
    app.state.token_map = container.token_map

    @app.get("/healthz", tags=["health"])
    def healthz() -> dict[str, str]:
        # Unauthenticated liveness probe (compose/k8s): the process is up and
        # serving. Readiness — pinging Postgres/RabbitMQ/MinIO — is a noted next step.
        return {"status": "ok"}

    app.include_router(documents.router)
    app.include_router(annotations.router)
    return app
