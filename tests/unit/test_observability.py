"""Structured, tenant-scoped logging. T030 (US3)."""

from __future__ import annotations

import json
import logging

import pytest

from app.observability import JsonFormatter, get_logger, log_event


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


def test_json_formatter_emits_event_and_context() -> None:
    record = logging.LogRecord(
        name="colophon.test",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="job.failed",
        args=(),
        exc_info=None,
    )
    record.tenant_id, record.job_id, record.stage = "t1", "j1", "annotated"

    payload = json.loads(JsonFormatter().format(record))

    assert payload == {
        "level": "WARNING",
        "event": "job.failed",
        "tenant_id": "t1",
        "job_id": "j1",
        "stage": "annotated",
    }


def test_json_formatter_omits_absent_context() -> None:
    record = logging.LogRecord(
        name="colophon.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="service.started",
        args=(),
        exc_info=None,
    )
    payload = json.loads(JsonFormatter().format(record))
    assert payload == {"level": "INFO", "event": "service.started"}
