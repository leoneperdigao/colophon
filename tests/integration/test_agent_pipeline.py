"""AnnotationAgent through the full pipeline — app wired to fakes, no infra/model.

Proves the real agent (classify -> extract -> validate -> ground) drops into the
pipeline behind the LLMClient port and produces a grounded annotation end-to-end.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.adapters.inbound.http.app import create_app
from app.adapters.llm.agent import AnnotationAgent
from app.adapters.outbound.blob.memory import InMemoryBlobStore
from app.adapters.outbound.messaging.memory import InMemoryMessaging
from app.adapters.outbound.store.memory import InMemoryAnnotationStore
from app.adapters.parsing.stub import StubParser
from app.config.container import Container
from app.worker.main import run as run_worker
from tests.fakes.fake_transport import FakeTransport

AUTH = {"Authorization": "Bearer tokenA"}


def test_agent_annotation_flows_through_pipeline() -> None:
    transport = FakeTransport(
        classify={"document_type": "invoice"},
        extract={
            "summary": "Invoice from ACME Corp.",
            "key_entities": [
                {"type": "org", "value": "ACME Corp"},
                {"type": "amount", "value": "GHOST"},  # not in the document -> ungrounded
            ],
            "language": "en",
        },
    )
    container = Container(
        token_map={"tokenA": "tenant-a"},
        blob=InMemoryBlobStore(),
        store=InMemoryAnnotationStore(),
        messaging=InMemoryMessaging(),
        parser=StubParser(),
        llm=AnnotationAgent(transport),
    )
    client = TestClient(create_app(container))

    job_id = client.post(
        "/documents",
        headers=AUTH,
        files={"file": ("invoice.pdf", b"Invoice from ACME Corp total due", "application/pdf")},
    ).json()["job_id"]
    run_worker(container)

    result = client.get(f"/annotations/{job_id}", headers=AUTH).json()["result"]
    assert result["document_type"] == "invoice"
    grounded = {e["value"]: e["grounded"] for e in result["key_entities"]}
    assert grounded["ACME Corp"] is True
    assert grounded["GHOST"] is False
    assert result["ungrounded_fields"] == ["GHOST"]
