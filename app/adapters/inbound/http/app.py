"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from app.adapters.inbound.http import documents
from app.config.container import Container


def create_app(container: Container) -> FastAPI:
    app = FastAPI(title="Document Annotation Service")
    app.state.container = container
    app.state.token_map = container.token_map
    app.include_router(documents.router)
    return app
