"""GetAnnotation service tests (vs fakes, no infra). T022."""

from __future__ import annotations

from app.application.ports.messaging import WorkMessage
from app.application.services.get_annotation import GetAnnotation
from app.application.services.process_pipeline import ProcessPipeline
from app.domain.job import Job
from tests.fakes.fake_blob import FakeBlobStore
from tests.fakes.fake_llm import FakeLLM
from tests.fakes.fake_parser import FakeParser
from tests.fakes.fake_store import FakeAnnotationStore


def test_get_returns_none_for_unknown_job() -> None:
    store = FakeAnnotationStore()
    assert GetAnnotation(store=store).execute(tenant_id="t1", job_id="nope") is None


def test_get_returns_queued_view_before_processing() -> None:
    store, blob = FakeAnnotationStore(), FakeBlobStore()
    blob.put_raw("t1", "j1", "f.pdf", b"hello")
    store.create_job(
        Job.new(
            job_id="j1",
            tenant_id="t1",
            source_filename="f.pdf",
            content_type="application/pdf",
            size_bytes=5,
        )
    )
    view = GetAnnotation(store=store).execute(tenant_id="t1", job_id="j1")
    assert view is not None
    assert view.status == "queued"
    assert view.result is None


def test_get_returns_completed_view_with_result() -> None:
    store, blob = FakeAnnotationStore(), FakeBlobStore()
    blob.put_raw("t1", "j1", "f.pdf", b"hello world")
    store.create_job(
        Job.new(
            job_id="j1",
            tenant_id="t1",
            source_filename="f.pdf",
            content_type="application/pdf",
            size_bytes=11,
        )
    )
    ProcessPipeline(blob=blob, store=store, parser=FakeParser(), llm=FakeLLM()).execute(
        WorkMessage(tenant_id="t1", job_id="j1")
    )
    view = GetAnnotation(store=store).execute(tenant_id="t1", job_id="j1")
    assert view is not None
    assert view.status == "completed"
    assert view.result is not None
    assert view.result.source_filename == "f.pdf"


def test_get_is_tenant_scoped() -> None:
    store = FakeAnnotationStore()
    store.create_job(
        Job.new(
            job_id="j1",
            tenant_id="t1",
            source_filename="f.pdf",
            content_type="application/pdf",
            size_bytes=5,
        )
    )
    # Another tenant's id is indistinguishable from unknown.
    assert GetAnnotation(store=store).execute(tenant_id="t2", job_id="j1") is None
