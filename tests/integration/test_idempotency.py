"""Idempotent re-upload — app wired to fakes, no infra. T031 (US4)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.adapters.inbound.http.app import create_app
from app.config.container import Container

PDF = ("f.pdf", b"hello world", "application/pdf")


def _client(token_map: dict[str, str]) -> tuple[TestClient, Container]:
    container = Container.in_memory(token_map=token_map)
    return TestClient(create_app(container)), container


def test_duplicate_upload_returns_same_id_and_enqueues_once() -> None:
    client, container = _client({"tokenA": "tenant-a"})
    headers = {"Authorization": "Bearer tokenA"}
    first = client.post("/documents", headers=headers, files={"file": PDF}).json()["job_id"]
    second = client.post("/documents", headers=headers, files={"file": PDF}).json()["job_id"]
    assert first == second
    assert len(container.messaging.enqueued) == 1


def test_same_content_two_tenants_get_distinct_ids() -> None:
    client, _ = _client({"tokenA": "tenant-a", "tokenB": "tenant-b"})
    id_a = client.post(
        "/documents", headers={"Authorization": "Bearer tokenA"}, files={"file": PDF}
    ).json()["job_id"]
    id_b = client.post(
        "/documents", headers={"Authorization": "Bearer tokenB"}, files={"file": PDF}
    ).json()["job_id"]
    assert id_a != id_b
