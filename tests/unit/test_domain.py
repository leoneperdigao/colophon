"""Domain entity + state-machine tests (pure, no infra). T006."""

import pytest

from app.domain.annotation import Annotation
from app.domain.job import Job, Stage, StageError, Status
from app.domain.key_entity import KeyEntity
from app.domain.tenant import Tenant


def _job() -> Job:
    return Job.new(
        job_id="j1",
        tenant_id="t1",
        source_filename="f.pdf",
        content_type="application/pdf",
        size_bytes=10,
    )


def test_new_job_starts_queued_at_raw() -> None:
    job = _job()
    assert job.status is Status.QUEUED
    assert job.stage is Stage.RAW
    assert job.error is None
    assert job.attempts == 0


def test_forward_stage_transitions_allowed() -> None:
    job = _job()
    job.start()
    assert job.status is Status.PROCESSING
    job.advance_to(Stage.CURATED)
    assert job.stage is Stage.CURATED
    job.advance_to(Stage.ANNOTATED)
    assert job.stage is Stage.ANNOTATED
    job.complete()
    assert job.status is Status.COMPLETED


def test_backward_stage_transition_rejected() -> None:
    job = _job()
    job.start()
    job.advance_to(Stage.CURATED)
    with pytest.raises(ValueError):
        job.advance_to(Stage.RAW)


def test_same_stage_transition_is_noop_not_backward() -> None:
    # Redelivery of the same stage must not raise (idempotent forward-only write).
    job = _job()
    job.start()
    job.advance_to(Stage.CURATED)
    job.advance_to(Stage.CURATED)
    assert job.stage is Stage.CURATED


def test_completed_job_is_terminal() -> None:
    job = _job()
    job.start()
    job.advance_to(Stage.CURATED)
    job.advance_to(Stage.ANNOTATED)
    job.complete()
    with pytest.raises(ValueError):
        job.advance_to(Stage.CURATED)


def test_failed_job_records_stage_and_error() -> None:
    job = _job()
    job.start()
    job.fail(stage=Stage.CURATED, message="parse boom")
    assert job.status is Status.FAILED
    assert job.error == StageError(stage=Stage.CURATED, message="parse boom")
    # job.stage must agree with the failing stage (no stage vs error.stage mismatch).
    assert job.stage is Stage.CURATED


def test_tenant_and_entities_shape() -> None:
    tenant = Tenant(tenant_id="t1", scopes=frozenset({"documents:write"}))
    assert "documents:write" in tenant.scopes

    entity = KeyEntity(type="org", value="ACME", grounded=True)
    annotation = Annotation(
        summary="An invoice from ACME.",
        document_type="invoice",
        key_entities=[entity],
        language="en",
        source_filename="f.pdf",
        page_or_sheet_count=1,
        confidence=0.9,
        extracted_at="2026-06-02T00:00:00Z",
        ungrounded_fields=[],
    )
    assert annotation.key_entities[0].value == "ACME"
    assert annotation.ungrounded_fields == []
