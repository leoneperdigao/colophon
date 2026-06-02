"""IngestDocument service tests (vs fakes, no infra). T015."""

from __future__ import annotations

from app.application.ports.messaging import WorkMessage
from app.application.services.ingest_document import IngestDocument
from app.domain.identity import compute_job_id
from app.domain.job import Stage, Status
from tests.fakes.fake_blob import FakeBlobStore
from tests.fakes.fake_messaging import FakeMessaging
from tests.fakes.fake_store import FakeAnnotationStore


def _svc() -> tuple[IngestDocument, FakeBlobStore, FakeAnnotationStore, FakeMessaging]:
    blob, store, messaging = FakeBlobStore(), FakeAnnotationStore(), FakeMessaging()
    return IngestDocument(blob=blob, store=store, messaging=messaging), blob, store, messaging


def test_ingest_returns_content_hash_job_id() -> None:
    svc, _, _, _ = _svc()
    job_id = svc.execute(
        tenant_id="t1", filename="f.pdf", content_type="application/pdf", content=b"hello"
    )
    assert job_id == compute_job_id("t1", b"hello", "f.pdf")


def test_ingest_creates_queued_job_writes_raw_and_enqueues_once() -> None:
    svc, blob, store, messaging = _svc()
    job_id = svc.execute(
        tenant_id="t1", filename="f.pdf", content_type="application/pdf", content=b"hello"
    )
    job = store.get_job("t1", job_id)
    assert job is not None
    assert job.status is Status.QUEUED
    assert job.stage is Stage.RAW
    assert job.size_bytes == 5
    assert blob.get_raw("t1", job_id) == b"hello"
    assert messaging.enqueued == [WorkMessage(tenant_id="t1", job_id=job_id)]
