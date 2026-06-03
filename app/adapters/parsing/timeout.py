"""TimeoutParser — a wall-clock budget around any DocumentParser (Constitution IV).

A crafted document can be slow to parse even within page/sheet/cell caps (a CPU
DoS). This decorator runs the wrapped parser on a daemon thread and gives up after
a budget, surfacing a graceful ParseError instead of pinning a worker.

Note: a daemon thread cannot be force-killed, so a runaway parse keeps consuming
CPU in the background until it returns; it just no longer blocks the worker. A
hard kill needs subprocess/sandbox isolation — see ADR-0005 (documented for later).
"""

from __future__ import annotations

import threading

from app.application.ports.document_parser import DocumentParser, ParseError
from app.domain.stage_result import Curated


class TimeoutParser:
    def __init__(self, inner: DocumentParser, *, timeout_seconds: float = 30.0) -> None:
        self._inner = inner
        self._timeout = timeout_seconds

    def parse(self, content: bytes, content_type: str, filename: str) -> Curated:
        result: list[Curated] = []
        error: list[Exception] = []

        def _run() -> None:
            try:
                result.append(self._inner.parse(content, content_type, filename))
            except Exception as exc:  # captured and re-raised on the calling thread
                error.append(exc)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(self._timeout)

        if thread.is_alive():
            raise ParseError("parsing timed out")
        if error:
            raise error[0]
        return result[0]
