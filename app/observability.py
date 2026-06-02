"""Structured, tenant-scoped logging.

Every log line about a job carries `tenant_id`, `job_id`, and (where relevant)
`stage`, so logs are correlatable and never ambiguous about whose data they
describe. A JSON formatter is available for real entrypoints; tests assert on the
structured context attributes directly.
"""

from __future__ import annotations

import json
import logging

_CONTEXT_KEYS = ("tenant_id", "job_id", "stage")
_HANDLER_NAME = "colophon-json"


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    tenant_id: str,
    job_id: str,
    stage: str | None = None,
    level: int = logging.INFO,
) -> None:
    """Emit a structured event with tenant/job/stage context."""
    logger.log(level, event, extra={"tenant_id": tenant_id, "job_id": job_id, "stage": stage})


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {"level": record.levelname, "event": record.getMessage()}
        for key in _CONTEXT_KEYS:
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload)


def configure_logging(level: int = logging.INFO) -> None:
    """Install a JSON handler on the root logger once (idempotent)."""
    root = logging.getLogger()
    if any(h.name == _HANDLER_NAME for h in root.handlers):
        return
    handler = logging.StreamHandler()
    handler.set_name(_HANDLER_NAME)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level)
