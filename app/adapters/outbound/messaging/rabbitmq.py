"""RabbitMQ Messaging adapter — durable work queue with bounded retry + DLX/DLQ.

Maps cleanly to the cloud target (SQS + DLQ). `pika` is imported lazily so the
module is importable without the `infra` extra. Retry/DLQ (ADR-0004): each message
carries an attempt count; on handler failure it is re-published up to `max_attempts`
times, then dead-lettered to the DLX (→ DLQ). The pipeline is idempotent, so
re-delivery is safe.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from app.application.ports.messaging import WorkMessage

WORK_QUEUE = "colophon.work"
DLX = "colophon.dlx"
DLQ = "colophon.work.dlq"
_ATTEMPT_HEADER = "x-attempt"


def _load_pika() -> Any:
    try:
        import pika
    except ImportError as exc:  # the 'infra' extra isn't installed
        raise RuntimeError("pika is not installed — install the 'infra' extra") from exc
    return pika


class RabbitMqMessaging:
    def __init__(self, *, url: str, max_attempts: int = 3) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1 (at least one handler invocation)")
        self._pika = _load_pika()
        self._max_attempts = max_attempts
        self._connection = self._pika.BlockingConnection(self._pika.URLParameters(url))
        self._channel = self._connection.channel()
        self._declare_topology()

    def _declare_topology(self) -> None:
        self._channel.exchange_declare(DLX, exchange_type="fanout", durable=True)
        self._channel.queue_declare(DLQ, durable=True)
        self._channel.queue_bind(DLQ, DLX)
        self._channel.queue_declare(
            WORK_QUEUE, durable=True, arguments={"x-dead-letter-exchange": DLX}
        )

    def close(self) -> None:
        if self._connection.is_open:
            self._connection.close()

    @staticmethod
    def _encode(message: WorkMessage) -> bytes:
        return json.dumps({"tenant_id": message.tenant_id, "job_id": message.job_id}).encode()

    @staticmethod
    def _decode(body: bytes) -> WorkMessage:
        data = json.loads(body)
        return WorkMessage(tenant_id=data["tenant_id"], job_id=data["job_id"])

    def _publish(self, body: bytes, *, attempt: int) -> None:
        self._channel.basic_publish(
            exchange="",
            routing_key=WORK_QUEUE,
            body=body,
            properties=self._pika.BasicProperties(
                delivery_mode=2, headers={_ATTEMPT_HEADER: attempt}
            ),
        )

    def enqueue(self, message: WorkMessage) -> None:
        self._publish(self._encode(message), attempt=0)

    def consume(
        self, handler: Callable[[WorkMessage], None], *, inactivity_timeout: float | None = None
    ) -> None:
        """Consume work, applying bounded retry + dead-lettering.

        Blocks forever by default (the worker). Pass `inactivity_timeout` to return
        once the queue is idle (used by tests).
        """
        try:
            for method, properties, body in self._channel.consume(
                WORK_QUEUE, inactivity_timeout=inactivity_timeout
            ):
                if method is None:  # idle past the timeout
                    break
                attempt = (properties.headers or {}).get(_ATTEMPT_HEADER, 0)
                try:
                    handler(self._decode(body))
                except Exception:  # noqa: BLE001 - any handler failure is retried/dead-lettered
                    if attempt + 1 < self._max_attempts:
                        self._publish(body, attempt=attempt + 1)  # retry a fresh copy
                        self._channel.basic_ack(method.delivery_tag)
                    else:
                        self._channel.basic_nack(method.delivery_tag, requeue=False)  # -> DLX/DLQ
                    continue
                self._channel.basic_ack(method.delivery_tag)
        finally:
            self._channel.cancel()  # always release the server-side consumer
