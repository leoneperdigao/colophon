"""GetAnnotation — tenant-scoped retrieval (US2).

Returns a read view of a job's status/stage and, when complete, its annotation.
A job outside the caller's tenant is indistinguishable from an unknown one.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.annotation_store import AnnotationStore
from app.domain.annotation import Annotation
from app.domain.job import StageError, Status


@dataclass(frozen=True)
class AnnotationView:
    job_id: str
    status: str
    stage: str
    result: Annotation | None
    error: StageError | None


class GetAnnotation:
    def __init__(self, *, store: AnnotationStore) -> None:
        self._store = store

    def execute(self, *, tenant_id: str, job_id: str) -> AnnotationView | None:
        job = self._store.get_job(tenant_id, job_id)
        if job is None:
            return None
        result = (
            self._store.get_annotation(tenant_id, job_id)
            if job.status is Status.COMPLETED
            else None
        )
        return AnnotationView(
            job_id=job.job_id,
            status=job.status.value,
            stage=job.stage.value,
            result=result,
            error=job.error,
        )
