"""Container.from_env profile selection — no infra required.

The `memory` profile must wire the in-memory fakes (so CI and the walking
skeleton run with zero infra and zero optional imports). The `local` profile is
covered end-to-end by the compose smoke test; here we only assert selection and
the unknown-profile guard.
"""

from __future__ import annotations

import pytest

from app.adapters.outbound.blob.memory import InMemoryBlobStore
from app.adapters.outbound.messaging.memory import InMemoryMessaging
from app.adapters.outbound.store.memory import InMemoryAnnotationStore
from app.adapters.parsing.stub import StubParser
from app.config.container import Container


def test_defaults_to_memory_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_PROFILE", raising=False)
    monkeypatch.setenv("TENANT_TOKENS", "tokenA:tenant-a")

    container = Container.from_env()

    assert isinstance(container.blob, InMemoryBlobStore)
    assert isinstance(container.store, InMemoryAnnotationStore)
    assert isinstance(container.messaging, InMemoryMessaging)
    assert isinstance(container.parser, StubParser)
    assert container.token_map == {"tokenA": "tenant-a"}


def test_unknown_profile_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_PROFILE", "bogus")
    with pytest.raises(ValueError, match="APP_PROFILE"):
        Container.from_env()


def test_local_profile_wires_real_adapters(monkeypatch: pytest.MonkeyPatch) -> None:
    """The local branch must build the real adapters via the lazy builders.

    We stub the builders so the test needs no infra; this pins the wiring
    (which port gets which builder) without importing minio/psycopg/pika.
    """
    monkeypatch.setenv("APP_PROFILE", "local")
    monkeypatch.setenv("TENANT_TOKENS", "tokenA:tenant-a")
    sentinel_blob, sentinel_store, sentinel_msg = object(), object(), object()
    sentinel_parser, sentinel_llm = object(), object()
    monkeypatch.setattr(Container, "_build_blob", staticmethod(lambda: sentinel_blob))
    monkeypatch.setattr(Container, "_build_store", staticmethod(lambda: sentinel_store))
    monkeypatch.setattr(Container, "_build_messaging", staticmethod(lambda: sentinel_msg))
    monkeypatch.setattr(Container, "_build_parser", staticmethod(lambda: sentinel_parser))
    monkeypatch.setattr(Container, "_build_llm", staticmethod(lambda: sentinel_llm))

    container = Container.from_env()

    assert container.blob is sentinel_blob
    assert container.store is sentinel_store
    assert container.messaging is sentinel_msg
    assert container.parser is sentinel_parser
    assert container.llm is sentinel_llm
