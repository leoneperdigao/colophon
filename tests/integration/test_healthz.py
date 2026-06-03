"""Liveness endpoint — unauthenticated GET /healthz (app wired to fakes, no infra)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.adapters.inbound.http.app import create_app
from app.config.container import Container


def _client() -> TestClient:
    return TestClient(create_app(Container.in_memory(token_map={"tokenA": "tenant-a"})))


def test_healthz_returns_200_ok() -> None:
    resp = _client().get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_healthz_needs_no_auth() -> None:
    # Health probes must not require a bearer token (k8s/compose liveness).
    resp = _client().get("/healthz")  # no Authorization header
    assert resp.status_code == 200
