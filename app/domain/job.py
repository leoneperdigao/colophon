"""Job — the unit of work for one document under one tenant.

Encapsulates the forward-only state machine:
    queued -> processing(raw -> curated -> annotated) -> completed | failed
Transitions move forward only; a redelivered same-stage write is a no-op; a
terminal job (completed/failed) rejects further stage transitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Status(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Stage(str, Enum):
    RAW = "raw"
    CURATED = "curated"
    ANNOTATED = "annotated"


_STAGE_ORDER: tuple[Stage, ...] = (Stage.RAW, Stage.CURATED, Stage.ANNOTATED)


def _rank(stage: Stage) -> int:
    return _STAGE_ORDER.index(stage)


@dataclass(frozen=True)
class StageError:
    stage: Stage
    message: str


@dataclass
class Job:
    job_id: str
    tenant_id: str
    source_filename: str
    content_type: str
    size_bytes: int
    status: Status = Status.QUEUED
    stage: Stage = Stage.RAW
    attempts: int = 0
    error: StageError | None = None

    @classmethod
    def new(
        cls,
        *,
        job_id: str,
        tenant_id: str,
        source_filename: str,
        content_type: str,
        size_bytes: int,
    ) -> "Job":
        return cls(
            job_id=job_id,
            tenant_id=tenant_id,
            source_filename=source_filename,
            content_type=content_type,
            size_bytes=size_bytes,
        )

    @property
    def is_terminal(self) -> bool:
        return self.status in (Status.COMPLETED, Status.FAILED)

    def start(self) -> None:
        if self.is_terminal:
            raise ValueError(f"cannot start a {self.status.value} job")
        self.status = Status.PROCESSING

    def advance_to(self, stage: Stage) -> None:
        if self.is_terminal:
            raise ValueError(f"cannot advance a {self.status.value} job")
        if _rank(stage) < _rank(self.stage):
            raise ValueError(f"backward transition {self.stage.value} -> {stage.value} rejected")
        self.stage = stage  # forward, or same-stage no-op

    def complete(self) -> None:
        if self.status is Status.FAILED:
            raise ValueError("cannot complete a failed job")
        self.status = Status.COMPLETED

    def fail(self, *, stage: Stage, message: str) -> None:
        self.status = Status.FAILED
        self.error = StageError(stage=stage, message=message)
