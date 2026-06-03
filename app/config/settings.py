"""Environment-driven configuration (no secrets in code)."""

from __future__ import annotations

import os
from typing import TypedDict

from app.adapters.parsing.content_types import SUPPORTED


class MissingSecret(RuntimeError):
    """Raised when a required secret/credential env var is unset or empty."""


def require_env(name: str) -> str:
    """Read a required env var, failing fast if it is missing or empty.

    Used for credentials so secrets are never baked into the code as defaults
    (Constitution IV): the value must come from the environment, or we refuse to
    start. Only the 'local' profile's builders call these, so 'memory'/CI never
    trip the guard.
    """
    value = os.getenv(name, "").strip()
    if not value:
        raise MissingSecret(f"{name} must be set (no default for credentials)")
    return value


def int_env(name: str, default: int) -> int:
    """Read a positive integer from the environment, falling back on absent/invalid."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


# Upload limits (untrusted input — Constitution IV). Tunable per deployment; the
# default (10 MiB) comfortably covers PDFs/spreadsheets at this scope. See ADR-0011
# for file-size handling and the scaling path (stream-to-blob / presigned upload).
MAX_UPLOAD_BYTES = int_env("MAX_UPLOAD_BYTES", 10 * 1024 * 1024)

# Accept only what the parser supports (single source of truth).
ALLOWED_CONTENT_TYPES = SUPPORTED


def app_profile() -> str:
    """Adapter wiring profile: 'memory' (default — no infra, CI/skeleton) or 'local'
    (real RabbitMQ/MinIO/Postgres). Production picks 'local' and points the infra
    env vars at managed services."""
    return os.getenv("APP_PROFILE", "memory").strip().lower()


class MinioConfig(TypedDict):
    endpoint: str
    access_key: str
    secret_key: str
    bucket: str
    secure: bool


def rabbitmq_url() -> str:
    """Full AMQP URL incl. credentials — required (no embedded-credential default)."""
    return require_env("RABBITMQ_URL")


def postgres_dsn() -> str:
    """Postgres DSN incl. credentials — required (no embedded-credential default)."""
    return require_env("DATABASE_URL")


def minio_config() -> MinioConfig:
    """MinIO/S3 settings. Credentials are required (never defaulted in code); the
    non-secret coordinates (endpoint/bucket/scheme) keep sensible local defaults."""
    return MinioConfig(
        endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
        access_key=require_env("MINIO_ACCESS_KEY"),
        secret_key=require_env("MINIO_SECRET_KEY"),
        bucket=os.getenv("MINIO_BUCKET", "colophon-raw"),
        secure=os.getenv("MINIO_SECURE", "false").strip().lower() == "true",
    )


def llm_model() -> str:
    """LiteLLM model id. Defaults to a local Ollama model for infra-free testing;
    set e.g. `anthropic/claude-3-5-haiku-latest` (+ ANTHROPIC_API_KEY) for cloud."""
    return os.getenv("LLM_MODEL", "ollama/llama3.1")


def llm_api_base() -> str | None:
    """Optional provider base URL (e.g. a non-default Ollama host)."""
    return os.getenv("LLM_API_BASE") or os.getenv("OLLAMA_API_BASE") or None


def load_token_map(raw: str | None = None) -> dict[str, str]:
    """Parse `TENANT_TOKENS` of the form 'tokenA:tenant-a,tokenB:tenant-b'."""
    raw = raw if raw is not None else os.getenv("TENANT_TOKENS", "")
    token_map: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair:
            continue
        token, _, tenant = pair.partition(":")
        token, tenant = token.strip(), tenant.strip()
        if token and tenant:
            token_map[token] = tenant
    return token_map
