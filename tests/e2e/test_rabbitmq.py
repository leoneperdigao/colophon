"""RabbitMQ Messaging adapter — real infra (opt-in). Skipped without RabbitMQ.

Run: `make up` (or a RabbitMQ container), then `pytest tests/e2e/test_rabbitmq.py`.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

pika = pytest.importorskip("pika")  # skip when the 'infra' extra isn't installed (CI)

from app.adapters.outbound.messaging.rabbitmq import (  # noqa: E402
    DLQ,
    WORK_QUEUE,
    RabbitMqMessaging,
)
from app.application.ports.messaging import WorkMessage  # noqa: E402

_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")


@pytest.fixture(scope="session")
def messaging() -> Iterator[RabbitMqMessaging]:
    try:
        adapter = RabbitMqMessaging(url=_URL, max_attempts=3)
    except pika.exceptions.AMQPConnectionError as exc:  # only "can't connect" -> skip
        pytest.skip(f"RabbitMQ not reachable: {exc}")
    yield adapter
    adapter.close()


def _purge(messaging: RabbitMqMessaging) -> None:
    messaging._channel.queue_purge(WORK_QUEUE)
    messaging._channel.queue_purge(DLQ)


def test_enqueue_then_consume(messaging: RabbitMqMessaging) -> None:
    _purge(messaging)
    received: list[WorkMessage] = []
    messaging.enqueue(WorkMessage(tenant_id="t1", job_id="j1"))
    messaging.consume(received.append, inactivity_timeout=2)
    assert received == [WorkMessage(tenant_id="t1", job_id="j1")]


def test_failing_handler_retries_then_dead_letters(messaging: RabbitMqMessaging) -> None:
    _purge(messaging)
    attempts: list[WorkMessage] = []

    def always_fail(message: WorkMessage) -> None:
        attempts.append(message)
        raise RuntimeError("boom")

    messaging.enqueue(WorkMessage(tenant_id="t1", job_id="jx"))
    messaging.consume(always_fail, inactivity_timeout=2)

    assert len(attempts) == 3  # max_attempts, then give up
    method, _props, body = messaging._channel.basic_get(DLQ, auto_ack=True)
    assert method is not None  # the message was dead-lettered
    assert b"jx" in body
