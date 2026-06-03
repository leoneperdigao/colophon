"""ProcessPipeline — raw -> curated -> annotated (US2).

Runs the staged pipeline for one job: parse the raw upload into curated content,
annotate it, persisting each stage with forward-only transitions. Failures are
captured as a terminal `failed` state naming the stage, never swallowed. Every
transition is logged with tenant/job/stage context.
"""

from __future__ import annotations

import logging

from app.application.ports.annotation_store import AnnotationStore
from app.application.ports.blob_store import BlobNotFound, BlobStore
from app.application.ports.document_parser import DocumentParser, ParseError
from app.application.ports.llm_client import LLMClient, LLMError
from app.application.ports.messaging import WorkMessage
from app.domain.job import Job, Stage
from app.observability import get_logger, log_event

_logger = get_logger(__name__)


class ProcessPipeline:
    def __init__(
        self,
        *,
        blob: BlobStore,
        store: AnnotationStore,
        parser: DocumentParser,
        llm: LLMClient,
    ) -> None:
        self._blob = blob
        self._store = store
        self._parser = parser
        self._llm = llm

    def execute(self, message: WorkMessage) -> None:
        tenant_id, job_id = message.tenant_id, message.job_id
        job = self._store.get_job(tenant_id, job_id)
        if job is None or job.is_terminal:
            return  # unknown, or already done/failed (idempotent on redelivery)

        job.start()
        self._store.update_job(job)
        log_event(
            _logger, "stage.started", tenant_id=tenant_id, job_id=job_id, stage=Stage.RAW.value
        )

        try:
            raw = self._blob.get_raw(tenant_id, job_id)
        except BlobNotFound as exc:
            return self._fail(job, Stage.RAW, str(exc))

        try:
            curated = self._parser.parse(raw, job.content_type, job.source_filename)
        except ParseError as exc:
            return self._fail(job, Stage.CURATED, str(exc))
        self._store.put_curated(tenant_id, job_id, curated)
        job.advance_to(Stage.CURATED)
        self._store.update_job(job)
        log_event(
            _logger, "stage.advanced", tenant_id=tenant_id, job_id=job_id, stage=Stage.CURATED.value
        )

        try:
            annotation = self._llm.annotate(curated, job.source_filename)
        except LLMError as exc:
            return self._fail(job, Stage.ANNOTATED, str(exc))
        self._store.put_annotation(tenant_id, job_id, annotation)
        job.advance_to(Stage.ANNOTATED)
        job.complete()
        self._store.update_job(job)
        log_event(
            _logger,
            "job.completed",
            tenant_id=tenant_id,
            job_id=job_id,
            stage=Stage.ANNOTATED.value,
        )

    def _fail(self, job: Job, stage: Stage, message: str) -> None:
        job.fail(stage=stage, message=message)
        self._store.update_job(job)
        log_event(
            _logger,
            "job.failed",
            tenant_id=job.tenant_id,
            job_id=job.job_id,
            stage=stage.value,
            level=logging.WARNING,
        )
