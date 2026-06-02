"""ProcessPipeline — raw -> curated -> annotated (US2).

Runs the staged pipeline for one job: parse the raw upload into curated content,
annotate it, persisting each stage with forward-only transitions. Failures are
captured as a terminal `failed` state naming the stage, never swallowed.
"""

from __future__ import annotations

from app.application.ports.annotation_store import AnnotationStore
from app.application.ports.blob_store import BlobNotFound, BlobStore
from app.application.ports.document_parser import DocumentParser, ParseError
from app.application.ports.llm_client import LLMClient, LLMError
from app.application.ports.messaging import WorkMessage
from app.domain.job import Stage


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

        try:
            raw = self._blob.get_raw(tenant_id, job_id)
        except BlobNotFound as exc:
            job.fail(stage=Stage.RAW, message=str(exc))
            self._store.update_job(job)
            return

        try:
            curated = self._parser.parse(raw, job.content_type, job.source_filename)
        except ParseError as exc:
            job.fail(stage=Stage.CURATED, message=str(exc))
            self._store.update_job(job)
            return
        self._store.put_curated(tenant_id, job_id, curated)
        job.advance_to(Stage.CURATED)
        self._store.update_job(job)

        try:
            annotation = self._llm.annotate(curated, job.source_filename)
        except LLMError as exc:
            job.fail(stage=Stage.ANNOTATED, message=str(exc))
            self._store.update_job(job)
            return
        self._store.put_annotation(tenant_id, job_id, annotation)
        job.advance_to(Stage.ANNOTATED)
        job.complete()
        self._store.update_job(job)
