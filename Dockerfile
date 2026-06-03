# Single image, two roles (api / worker) selected by the compose command.
# Multi-stage: deps are resolved from the lockfile, then app code is copied in.
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH

# Pinned uv from the official distroless image (no curl|sh).
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

WORKDIR /app

# Layer 1 — dependencies only (cached until the lockfile changes).
# Real adapters need the infra + llm extras; parsing deps are in the core set.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --extra infra --extra llm

# Layer 2 — the application package.
COPY app ./app
RUN uv sync --frozen --no-dev --extra infra --extra llm

# Non-root by default (Constitution IV / least privilege). Owns only what it runs.
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app /opt/venv
USER appuser

# Overridden per service in docker-compose.yml.
CMD ["uvicorn", "app.asgi:app", "--host", "0.0.0.0", "--port", "8000"]
