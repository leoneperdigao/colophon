"""Postgres AnnotationStore adapter — jobs + curated + annotated, tenant-scoped.

Every row carries `tenant_id` and every query filters on it. `psycopg` is an
optional `infra` extra, imported only by the composition root's local profile, so
CI stays infra-free. A single autocommit connection is used here for simplicity;
production would use a connection pool.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from app.domain.annotation import Annotation
from app.domain.job import Job, Stage, StageError, Status
from app.domain.key_entity import KeyEntity
from app.domain.stage_result import Curated

_SCHEMA: tuple[str, ...] = (
    """CREATE TABLE IF NOT EXISTS jobs (
        tenant_id text NOT NULL, job_id text NOT NULL,
        source_filename text NOT NULL, content_type text NOT NULL, size_bytes bigint NOT NULL,
        status text NOT NULL, stage text NOT NULL, attempts int NOT NULL DEFAULT 0,
        error_stage text, error_message text,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (tenant_id, job_id))""",
    """CREATE TABLE IF NOT EXISTS curated (
        tenant_id text NOT NULL, job_id text NOT NULL,
        text text NOT NULL, structure jsonb NOT NULL DEFAULT '{}',
        page_or_sheet_count int NOT NULL, detected_type_hint text,
        PRIMARY KEY (tenant_id, job_id))""",
    """CREATE TABLE IF NOT EXISTS annotated (
        tenant_id text NOT NULL, job_id text NOT NULL, payload jsonb NOT NULL,
        PRIMARY KEY (tenant_id, job_id))""",
)


class PostgresAnnotationStore:
    def __init__(self, *, dsn: str) -> None:
        self._conn = psycopg.connect(dsn, autocommit=True)
        for statement in _SCHEMA:
            self._conn.execute(statement)

    def create_job(self, job: Job) -> None:
        self._conn.execute(
            """INSERT INTO jobs (tenant_id, job_id, source_filename, content_type, size_bytes,
                   status, stage, attempts, error_stage, error_message)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (tenant_id, job_id) DO NOTHING""",
            (
                job.tenant_id,
                job.job_id,
                job.source_filename,
                job.content_type,
                job.size_bytes,
                job.status.value,
                job.stage.value,
                job.attempts,
                job.error.stage.value if job.error else None,
                job.error.message if job.error else None,
            ),
        )

    def get_job(self, tenant_id: str, job_id: str) -> Job | None:
        row = self._conn.execute(
            """SELECT source_filename, content_type, size_bytes, status, stage, attempts,
                      error_stage, error_message
               FROM jobs WHERE tenant_id=%s AND job_id=%s""",
            (tenant_id, job_id),
        ).fetchone()
        if row is None:
            return None
        filename, content_type, size_bytes, status, stage, attempts, error_stage, error_message = (
            row
        )
        error = StageError(stage=Stage(error_stage), message=error_message) if error_stage else None
        return Job(
            job_id=job_id,
            tenant_id=tenant_id,
            source_filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            status=Status(status),
            stage=Stage(stage),
            attempts=attempts,
            error=error,
        )

    def update_job(self, job: Job) -> None:
        self._conn.execute(
            """UPDATE jobs SET status=%s, stage=%s, attempts=%s, error_stage=%s, error_message=%s,
                   updated_at=now() WHERE tenant_id=%s AND job_id=%s""",
            (
                job.status.value,
                job.stage.value,
                job.attempts,
                job.error.stage.value if job.error else None,
                job.error.message if job.error else None,
                job.tenant_id,
                job.job_id,
            ),
        )

    def put_curated(self, tenant_id: str, job_id: str, curated: Curated) -> None:
        self._conn.execute(
            """INSERT INTO curated (tenant_id, job_id, text, structure, page_or_sheet_count,
                   detected_type_hint) VALUES (%s,%s,%s,%s,%s,%s)
               ON CONFLICT (tenant_id, job_id) DO UPDATE SET
                   text=EXCLUDED.text, structure=EXCLUDED.structure,
                   page_or_sheet_count=EXCLUDED.page_or_sheet_count,
                   detected_type_hint=EXCLUDED.detected_type_hint""",
            (
                tenant_id,
                job_id,
                curated.text,
                Jsonb(curated.structure),
                curated.page_or_sheet_count,
                curated.detected_type_hint,
            ),
        )

    def get_curated(self, tenant_id: str, job_id: str) -> Curated | None:
        row = self._conn.execute(
            """SELECT text, structure, page_or_sheet_count, detected_type_hint
               FROM curated WHERE tenant_id=%s AND job_id=%s""",
            (tenant_id, job_id),
        ).fetchone()
        if row is None:
            return None
        text, structure, count, hint = row
        return Curated(
            text=text, page_or_sheet_count=count, structure=structure or {}, detected_type_hint=hint
        )

    def put_annotation(self, tenant_id: str, job_id: str, annotation: Annotation) -> None:
        self._conn.execute(
            """INSERT INTO annotated (tenant_id, job_id, payload) VALUES (%s,%s,%s)
               ON CONFLICT (tenant_id, job_id) DO UPDATE SET payload=EXCLUDED.payload""",
            (tenant_id, job_id, Jsonb(asdict(annotation))),
        )

    def get_annotation(self, tenant_id: str, job_id: str) -> Annotation | None:
        row = self._conn.execute(
            "SELECT payload FROM annotated WHERE tenant_id=%s AND job_id=%s",
            (tenant_id, job_id),
        ).fetchone()
        if row is None:
            return None
        return _to_annotation(row[0])


def _to_annotation(payload: dict[str, Any]) -> Annotation:
    entities = [
        KeyEntity(type=e["type"], value=e["value"], grounded=bool(e.get("grounded", False)))
        for e in payload["key_entities"]
    ]
    return Annotation(
        summary=payload["summary"],
        document_type=payload["document_type"],
        key_entities=entities,
        language=payload["language"],
        source_filename=payload["source_filename"],
        page_or_sheet_count=payload["page_or_sheet_count"],
        confidence=payload["confidence"],
        extracted_at=payload["extracted_at"],
        ungrounded_fields=list(payload.get("ungrounded_fields", [])),
    )
