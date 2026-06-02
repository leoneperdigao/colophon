"""POST /documents contract — app wired to fakes, no infra. T013."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.adapters.inbound.http.app import create_app
from app.config.container import Container


def _client() -> tuple[TestClient, Container]:
    container = Container.in_memory(token_map={"tokenA": "tenant-a"})
    return TestClient(create_app(container)), container


def test_post_returns_202_with_job_id() -> None:
    client, _ = _client()
    resp = client.post(
        "/documents",
        headers={"Authorization": "Bearer tokenA"},
        files={"file": ("f.pdf", b"hello", "application/pdf")},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "queued"
    assert body["job_id"]


def test_post_without_token_is_401_and_creates_no_job() -> None:
    client, container = _client()
    resp = client.post(
        "/documents",
        files={"file": ("f.pdf", b"hello", "application/pdf")},
    )
    assert resp.status_code == 401
    assert container.messaging.enqueued == []


def test_post_unsupported_content_type_is_415() -> None:
    client, _ = _client()
    resp = client.post(
        "/documents",
        headers={"Authorization": "Bearer tokenA"},
        files={"file": ("f.exe", b"hello", "application/x-msdownload")},
    )
    assert resp.status_code == 415


def test_post_enqueues_exactly_one_work_message() -> None:
    client, container = _client()
    client.post(
        "/documents",
        headers={"Authorization": "Bearer tokenA"},
        files={"file": ("f.pdf", b"hello", "application/pdf")},
    )
    assert len(container.messaging.enqueued) == 1
