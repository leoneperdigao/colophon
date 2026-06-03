"""Structured, tenant-scoped logging. T030 (US3)."""

from __future__ import annotations

import logging

import pytest

from app.observability import get_logger, log_event


def test_log_event_attaches_tenant_job_stage_context(caplog: pytest.LogCaptureFixture) -> None:
    logger = get_logger("colophon.test")
    with caplog.at_level(logging.INFO):
        log_event(logger, "job.created", tenant_id="t1", job_id="j1", stage="raw")
    record = caplog.records[-1]
    assert record.getMessage() == "job.created"
    assert getattr(record, "tenant_id") == "t1"
    assert getattr(record, "job_id") == "j1"
    assert getattr(record, "stage") == "raw"


def test_log_event_stage_optional(caplog: pytest.LogCaptureFixture) -> None:
    logger = get_logger("colophon.test")
    with caplog.at_level(logging.INFO):
        log_event(logger, "job.enqueued", tenant_id="t1", job_id="j1")
    record = caplog.records[-1]
    assert getattr(record, "tenant_id") == "t1"
    assert getattr(record, "stage") is None
