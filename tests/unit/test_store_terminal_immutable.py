"""Terminal jobs are immutable at the store (ADR-0013).

Guards the concurrent-redelivery case: once a job is completed/failed, a second
worker that slipped past the in-memory `is_terminal` check cannot clobber the
finished result. The Postgres adapter enforces the same with a conditional UPDATE
(covered by tests/e2e/test_postgres_store.py).
"""

from __future__ import annotations

import pytest

from app.adapters.outbound.store.memory import InMemoryAnnotationStore
from app.domain.job import Job, Stage, Status


def _queued() -> Job:
    return Job.new(
        job_id="j1",
        tenant_id="t1",
        source_filename="f.pdf",
        content_type="application/pdf",
        size_bytes=10,
    )


def _complete(job: Job) -> None:
    job.start()
    job.advance_to(Stage.CURATED)
    job.advance_to(Stage.ANNOTATED)
    job.complete()


@pytest.mark.parametrize("terminal", ["completed", "failed"])
def test_terminal_job_cannot_be_overwritten(terminal: str) -> None:
    store = InMemoryAnnotationStore()
    job = _queued()
    store.create_job(job)

    if terminal == "completed":
        _complete(job)
    else:
        job.start()
        job.fail(stage=Stage.CURATED, message="boom")
    store.update_job(job)

    # A second/redelivered worker tries to write a non-terminal state for the same id.
    intruder = _queued()
    intruder.start()  # processing
    store.update_job(intruder)

    persisted = store.get_job("t1", "j1")
    assert persisted is not None
    assert persisted.status is (Status.COMPLETED if terminal == "completed" else Status.FAILED)


def test_forward_transitions_still_persist() -> None:
    store = InMemoryAnnotationStore()
    job = _queued()
    store.create_job(job)
    job.start()
    store.update_job(job)
    job.advance_to(Stage.CURATED)
    store.update_job(job)

    persisted = store.get_job("t1", "j1")
    assert persisted is not None
    assert persisted.status is Status.PROCESSING
    assert persisted.stage is Stage.CURATED
