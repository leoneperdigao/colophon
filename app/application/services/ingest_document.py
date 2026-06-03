"""IngestDocument — the accept path (US1).

Writes raw, creates the job, enqueues work, returns the job_id. Tenant is passed
in already resolved from the credential (never client-supplied).
"""

from __future__ import annotations

from app.application.ports.annotation_store import AnnotationStore
from app.application.ports.blob_store import BlobStore
from app.application.ports.messaging import Messaging, WorkMessage
from app.domain.identity import compute_job_id
from app.domain.job import Job
from app.observability import get_logger, log_event

_logger = get_logger(__name__)


class IngestDocument:
    def __init__(self, *, blob: BlobStore, store: AnnotationStore, messaging: Messaging) -> None:
        self._blob = blob
        self._store = store
        self._messaging = messaging

    def execute(self, *, tenant_id: str, filename: str, content_type: str, content: bytes) -> str:
        job_id = compute_job_id(tenant_id, content, filename)
        if self._store.get_job(tenant_id, job_id) is not None:
            log_event(_logger, "job.duplicate", tenant_id=tenant_id, job_id=job_id)
            return job_id  # idempotent: identical re-upload, do not reprocess
        self._blob.put_raw(tenant_id, job_id, filename, content)
        self._store.create_job(
            Job.new(
                job_id=job_id,
                tenant_id=tenant_id,
                source_filename=filename,
                content_type=content_type,
                size_bytes=len(content),
            )
        )
        self._messaging.enqueue(WorkMessage(tenant_id=tenant_id, job_id=job_id))
        log_event(_logger, "job.created", tenant_id=tenant_id, job_id=job_id, stage="raw")
        return job_id
