"""FastAPI application factory."""

from fastapi import FastAPI

from app.adapters.inbound.http import annotations, documents
from app.config.container import Container


def create_app(container: Container) -> FastAPI:
    app = FastAPI(title="Document Annotation Service")
    app.state.container = container
    app.state.token_map = container.token_map
    app.include_router(documents.router)
    app.include_router(annotations.router)
    return app
