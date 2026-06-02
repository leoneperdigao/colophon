"""GET /annotations/{job_id} contract + full loop — app wired to fakes. T020."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.adapters.inbound.http.app import create_app
from app.config.container import Container
from app.worker.main import run as run_worker

AUTH = {"Authorization": "Bearer tokenA"}


def _setup() -> tuple[TestClient, Container]:
    container = Container.in_memory(token_map={"tokenA": "tenant-a"})
    return TestClient(create_app(container)), container


def test_get_unknown_job_is_404() -> None:
    client, _ = _setup()
    assert client.get("/annotations/nope", headers=AUTH).status_code == 404


def test_get_requires_credential() -> None:
    client, _ = _setup()
    assert client.get("/annotations/anything").status_code == 401


def test_full_loop_upload_process_retrieve() -> None:
    client, container = _setup()
    job_id = client.post(
        "/documents",
        headers=AUTH,
        files={"file": ("f.pdf", b"hello world", "application/pdf")},
    ).json()["job_id"]

    before = client.get(f"/annotations/{job_id}", headers=AUTH).json()
    assert before["status"] == "queued"
    assert before["result"] is None

    run_worker(container)  # drains the in-memory queue synchronously

    after = client.get(f"/annotations/{job_id}", headers=AUTH).json()
    assert after["status"] == "completed"
    assert after["stage"] == "annotated"
    assert after["result"]["source_filename"] == "f.pdf"
    assert after["result"]["document_type"]
    assert after["error"] is None
