"""Postgres AnnotationStore adapter — real infra (opt-in). Skipped without Postgres.

Run: `make up` (or a Postgres container), then `pytest tests/e2e/test_postgres_store.py`.
"""

from __future__ import annotations

import os
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")  # skip when the 'infra' extra isn't installed (CI)

from app.adapters.outbound.store.postgres_store import PostgresAnnotationStore  # noqa: E402
from app.domain.annotation import Annotation  # noqa: E402
from app.domain.job import Job, Stage, Status  # noqa: E402
from app.domain.key_entity import KeyEntity  # noqa: E402
from app.domain.stage_result import Curated  # noqa: E402

_DSN = os.getenv("POSTGRES_DSN", "postgresql://colophon:colophon@localhost:5432/colophon")


@pytest.fixture
def store() -> PostgresAnnotationStore:
    try:
        return PostgresAnnotationStore(dsn=_DSN)
    except psycopg.OperationalError as exc:  # only "can't connect" -> opt-in skip
        pytest.skip(f"Postgres not reachable: {exc}")


def _job(tenant: str, job_id: str) -> Job:
    return Job.new(
        job_id=job_id,
        tenant_id=tenant,
        source_filename="f.pdf",
        content_type="application/pdf",
        size_bytes=10,
    )


def test_job_create_get_update_roundtrip(store: PostgresAnnotationStore) -> None:
    job_id = uuid.uuid4().hex
    store.create_job(_job("t1", job_id))
    got = store.get_job("t1", job_id)
    assert got is not None and got.status is Status.QUEUED and got.stage is Stage.RAW

    got.start()
    got.advance_to(Stage.CURATED)
    store.update_job(got)
    reloaded = store.get_job("t1", job_id)
    assert reloaded is not None
    assert reloaded.status is Status.PROCESSING
    assert reloaded.stage is Stage.CURATED


def test_create_job_is_idempotent(store: PostgresAnnotationStore) -> None:
    job_id = uuid.uuid4().hex
    store.create_job(_job("t1", job_id))
    store.create_job(_job("t1", job_id))  # ON CONFLICT DO NOTHING
    assert store.get_job("t1", job_id) is not None


def test_failed_job_persists_stage_and_error(store: PostgresAnnotationStore) -> None:
    job_id = uuid.uuid4().hex
    job = _job("t1", job_id)
    store.create_job(job)
    job.start()
    job.fail(stage=Stage.CURATED, message="could not read the PDF document")
    store.update_job(job)
    reloaded = store.get_job("t1", job_id)
    assert reloaded is not None and reloaded.status is Status.FAILED
    assert reloaded.error is not None and reloaded.error.stage is Stage.CURATED


def test_get_job_is_tenant_scoped(store: PostgresAnnotationStore) -> None:
    job_id = uuid.uuid4().hex
    store.create_job(_job("tenant-a", job_id))
    assert store.get_job("tenant-b", job_id) is None  # another tenant's id is unknown


def test_curated_and_annotation_roundtrip(store: PostgresAnnotationStore) -> None:
    job_id = uuid.uuid4().hex
    store.create_job(_job("t1", job_id))
    store.put_curated("t1", job_id, Curated(text="ACME invoice", page_or_sheet_count=1))
    assert store.get_curated("t1", job_id) is not None

    annotation = Annotation(
        summary="Invoice from ACME",
        document_type="invoice",
        key_entities=[KeyEntity(type="org", value="ACME", grounded=True)],
        language="en",
        source_filename="f.pdf",
        page_or_sheet_count=1,
        confidence=0.9,
        extracted_at="2026-06-03T00:00:00Z",
        ungrounded_fields=[],
    )
    store.put_annotation("t1", job_id, annotation)
    got = store.get_annotation("t1", job_id)
    assert got is not None
    assert got.document_type == "invoice"
    assert got.key_entities[0].value == "ACME"
    assert got.key_entities[0].grounded is True
