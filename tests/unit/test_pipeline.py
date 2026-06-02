"""ProcessPipeline tests (vs fakes, no infra). T021."""

from __future__ import annotations

from app.application.ports.messaging import WorkMessage
from app.application.services.process_pipeline import ProcessPipeline
from app.domain.job import Job, Stage, Status
from tests.fakes.fake_blob import FakeBlobStore
from tests.fakes.fake_llm import FakeLLM
from tests.fakes.fake_parser import FakeParser
from tests.fakes.fake_store import FakeAnnotationStore


def _seed(store: FakeAnnotationStore, blob: FakeBlobStore, *, tenant: str, job_id: str) -> None:
    blob.put_raw(tenant, job_id, "f.pdf", b"hello world")
    store.create_job(
        Job.new(
            job_id=job_id,
            tenant_id=tenant,
            source_filename="f.pdf",
            content_type="application/pdf",
            size_bytes=11,
        )
    )


def test_pipeline_completes_job_through_all_stages() -> None:
    blob, store = FakeBlobStore(), FakeAnnotationStore()
    _seed(store, blob, tenant="t1", job_id="j1")
    ProcessPipeline(blob=blob, store=store, parser=FakeParser(), llm=FakeLLM()).execute(
        WorkMessage(tenant_id="t1", job_id="j1")
    )
    job = store.get_job("t1", "j1")
    assert job is not None
    assert job.status is Status.COMPLETED
    assert job.stage is Stage.ANNOTATED
    assert store.get_curated("t1", "j1") is not None
    annotation = store.get_annotation("t1", "j1")
    assert annotation is not None
    assert annotation.source_filename == "f.pdf"


def test_pipeline_fails_naming_curated_stage_on_parse_error() -> None:
    blob, store = FakeBlobStore(), FakeAnnotationStore()
    _seed(store, blob, tenant="t1", job_id="j1")
    ProcessPipeline(blob=blob, store=store, parser=FakeParser(fail=True), llm=FakeLLM()).execute(
        WorkMessage(tenant_id="t1", job_id="j1")
    )
    job = store.get_job("t1", "j1")
    assert job is not None
    assert job.status is Status.FAILED
    assert job.error is not None
    assert job.error.stage is Stage.CURATED


def test_pipeline_fails_naming_annotated_stage_on_llm_error() -> None:
    blob, store = FakeBlobStore(), FakeAnnotationStore()
    _seed(store, blob, tenant="t1", job_id="j1")
    ProcessPipeline(blob=blob, store=store, parser=FakeParser(), llm=FakeLLM(fail=True)).execute(
        WorkMessage(tenant_id="t1", job_id="j1")
    )
    job = store.get_job("t1", "j1")
    assert job is not None
    assert job.status is Status.FAILED
    assert job.error is not None
    assert job.error.stage is Stage.ANNOTATED


def test_pipeline_is_idempotent_on_already_completed_job() -> None:
    blob, store = FakeBlobStore(), FakeAnnotationStore()
    _seed(store, blob, tenant="t1", job_id="j1")
    pipeline = ProcessPipeline(blob=blob, store=store, parser=FakeParser(), llm=FakeLLM())
    pipeline.execute(WorkMessage(tenant_id="t1", job_id="j1"))
    pipeline.execute(WorkMessage(tenant_id="t1", job_id="j1"))  # redelivery must not regress
    job = store.get_job("t1", "j1")
    assert job is not None
    assert job.status is Status.COMPLETED


def test_pipeline_ignores_unknown_job() -> None:
    blob, store = FakeBlobStore(), FakeAnnotationStore()
    ProcessPipeline(blob=blob, store=store, parser=FakeParser(), llm=FakeLLM()).execute(
        WorkMessage(tenant_id="t1", job_id="missing")
    )
    assert store.get_job("t1", "missing") is None
