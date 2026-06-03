"""In-memory AnnotationStore adapter — tenant-scoped, no-infra profile.

Keys include tenant_id, so a wrong-tenant lookup misses (returns None) — modelling
"another tenant's id is indistinguishable from unknown".
"""

from __future__ import annotations

import copy

from app.domain.annotation import Annotation
from app.domain.job import Job
from app.domain.stage_result import Curated


class InMemoryAnnotationStore:
    def __init__(self) -> None:
        self._jobs: dict[tuple[str, str], Job] = {}
        self._curated: dict[tuple[str, str], Curated] = {}
        self._annotations: dict[tuple[str, str], Annotation] = {}

    def create_job(self, job: Job) -> None:
        self._jobs.setdefault((job.tenant_id, job.job_id), copy.deepcopy(job))

    def get_job(self, tenant_id: str, job_id: str) -> Job | None:
        job = self._jobs.get((tenant_id, job_id))
        return copy.deepcopy(job) if job is not None else None

    def update_job(self, job: Job) -> None:
        # Terminal jobs are immutable: the first completed/failed write wins, so a
        # redelivered/concurrent worker cannot clobber a finished result (mirrors the
        # Postgres adapter's conditional UPDATE). See ADR-0013.
        existing = self._jobs.get((job.tenant_id, job.job_id))
        if existing is not None and existing.is_terminal:
            return
        self._jobs[(job.tenant_id, job.job_id)] = copy.deepcopy(job)

    def put_curated(self, tenant_id: str, job_id: str, curated: Curated) -> None:
        self._curated[(tenant_id, job_id)] = curated

    def get_curated(self, tenant_id: str, job_id: str) -> Curated | None:
        return self._curated.get((tenant_id, job_id))

    def put_annotation(self, tenant_id: str, job_id: str, annotation: Annotation) -> None:
        self._annotations[(tenant_id, job_id)] = annotation

    def get_annotation(self, tenant_id: str, job_id: str) -> Annotation | None:
        return self._annotations.get((tenant_id, job_id))
