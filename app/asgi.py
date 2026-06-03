"""ASGI entrypoint for the HTTP API (`uvicorn app.asgi:app`).

Owns process-level concerns (logging) and builds the container from the
environment, then hands a fully-wired FastAPI app to the server.
"""

from __future__ import annotations

from app.adapters.inbound.http.app import create_app
from app.config.container import Container
from app.observability import configure_logging

configure_logging()
app = create_app(Container.from_env())
