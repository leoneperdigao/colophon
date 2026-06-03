"""RabbitMQ adapter contract checks that need no broker (and no 'infra' extra).

`max_attempts` is validated before any connection is opened, so the guard is
fully unit-testable. The rest of the adapter is covered by the opt-in e2e suite
in tests/e2e/test_rabbitmq.py against a real broker.
"""

from __future__ import annotations

import pytest

from app.adapters.outbound.messaging.rabbitmq import RabbitMqMessaging


@pytest.mark.parametrize("bad", [0, -1])
def test_rejects_non_positive_max_attempts(bad: int) -> None:
    with pytest.raises(ValueError, match="max_attempts must be >= 1"):
        RabbitMqMessaging(url="amqp://guest:guest@localhost:5672/", max_attempts=bad)
