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


def test_default_upload_cap_is_10_mib() -> None:
    assert settings.MAX_UPLOAD_BYTES == 10 * 1024 * 1024
