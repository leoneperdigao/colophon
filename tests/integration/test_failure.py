"""Explicit staged failure — app wired to fakes, no infra. T035 (US5).

An unprocessable document must reach a terminal `failed` state that names the
failing stage, never a silent or partial success.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.adapters.inbound.http.app import create_app
from app.adapters.llm.stub import StubLLM
from app.adapters.outbound.blob.memory import InMemoryBlobStore
from app.adapters.outbound.messaging.memory import InMemoryMessaging
from app.adapters.outbound.store.memory import InMemoryAnnotationStore
from app.adapters.parsing.stub import StubParser
from app.config.container import Container
from app.worker.main import run as run_worker

AUTH = {"Authorization": "Bearer tokenA"}


def _client_with_failing_parser() -> tuple[TestClient, Container]:
    container = Container(
        token_map={"tokenA": "tenant-a"},
        blob=InMemoryBlobStore(),
        store=InMemoryAnnotationStore(),
        messaging=InMemoryMessaging(),
        parser=StubParser(fail=True),
        llm=StubLLM(),
    )
    return TestClient(create_app(container)), container


def test_unprocessable_document_reaches_failed_naming_stage() -> None:
    client, container = _client_with_failing_parser()
    job_id = client.post(
        "/documents", headers=AUTH, files={"file": ("bad.pdf", b"junk", "application/pdf")}
    ).json()["job_id"]

    run_worker(container)

    body = client.get(f"/annotations/{job_id}", headers=AUTH).json()
    assert body["status"] == "failed"
    assert body["stage"] == "curated"
    assert body["error"]["stage"] == "curated"
    assert body["error"]["message"]
    assert body["result"] is None
