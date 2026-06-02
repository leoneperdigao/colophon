"""AnnotationStore port — jobs + curated + annotated rows, all tenant-scoped."""

from __future__ import annotations

from typing import Protocol

from app.domain.annotation import Annotation
from app.domain.job import Job
from app.domain.stage_result import Curated


class AnnotationStore(Protocol):
    def create_job(self, job: Job) -> None:
        """Persist a new job. No-op/idempotent if the job_id already exists."""
        ...

    def get_job(self, tenant_id: str, job_id: str) -> Job | None:
        """Return the job iff it belongs to tenant_id, else None (no cross-tenant leak)."""
        ...

    def update_job(self, job: Job) -> None:
        """Persist a forward-only job state change."""
        ...

    def put_curated(self, tenant_id: str, job_id: str, curated: Curated) -> None: ...

    def get_curated(self, tenant_id: str, job_id: str) -> Curated | None: ...

    def put_annotation(self, tenant_id: str, job_id: str, annotation: Annotation) -> None: ...

    def get_annotation(self, tenant_id: str, job_id: str) -> Annotation | None: ...
