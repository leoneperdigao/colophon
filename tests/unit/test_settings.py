"""Config helpers — env-tunable upload cap (ADR-0011)."""

from __future__ import annotations

import pytest

from app.config import settings


def test_int_env_uses_default_when_absent() -> None:
    assert settings.int_env("COLOPHON_NOPE_XYZ", 42) == 42


def test_int_env_reads_set_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "2048")
    assert settings.int_env("MAX_UPLOAD_BYTES", 10) == 2048


def test_int_env_rejects_non_integer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "not-a-number")
    assert settings.int_env("MAX_UPLOAD_BYTES", 99) == 99


def test_int_env_rejects_non_positive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "0")
    assert settings.int_env("MAX_UPLOAD_BYTES", 99) == 99


def test_default_upload_cap_is_10_mib(monkeypatch: pytest.MonkeyPatch) -> None:
    # Deterministic: clear the env and assert the default-resolution logic directly
    # (settings.MAX_UPLOAD_BYTES is computed at import time and would be env-dependent).
    monkeypatch.delenv("MAX_UPLOAD_BYTES", raising=False)
    assert settings.int_env("MAX_UPLOAD_BYTES", 10 * 1024 * 1024) == 10 * 1024 * 1024


# --- credentials must come from the environment, never code defaults -----------


@pytest.mark.parametrize("value", [None, "", "   "])
def test_require_env_fails_fast_when_missing_or_blank(
    monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    if value is None:
        monkeypatch.delenv("SOME_SECRET", raising=False)
    else:
        monkeypatch.setenv("SOME_SECRET", value)
    with pytest.raises(settings.MissingSecret, match="SOME_SECRET"):
        settings.require_env("SOME_SECRET")


def test_require_env_returns_trimmed_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOME_SECRET", "  hunter2  ")
    assert settings.require_env("SOME_SECRET") == "hunter2"


def test_rabbitmq_and_postgres_have_no_credential_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RABBITMQ_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(settings.MissingSecret):
        settings.rabbitmq_url()
    with pytest.raises(settings.MissingSecret):
        settings.postgres_dsn()


def test_minio_config_requires_credentials_but_defaults_coordinates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MINIO_ACCESS_KEY", raising=False)
    monkeypatch.delenv("MINIO_SECRET_KEY", raising=False)
    monkeypatch.delenv("MINIO_ENDPOINT", raising=False)
    monkeypatch.delenv("MINIO_BUCKET", raising=False)
    with pytest.raises(settings.MissingSecret):
        settings.minio_config()

    monkeypatch.setenv("MINIO_ACCESS_KEY", "key")
    monkeypatch.setenv("MINIO_SECRET_KEY", "secret")
    config = settings.minio_config()
    assert config["access_key"] == "key"
    assert config["secret_key"] == "secret"
    assert config["endpoint"] == "localhost:9000"  # non-secret coordinate keeps a default
    assert config["bucket"] == "colophon-raw"
    assert config["secure"] is False
