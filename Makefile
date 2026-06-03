.PHONY: install test lint eval samples up down

install:        ## sync deps (add extras: uv sync --extra llm --extra infra --extra parsing)
	uv sync --dev

test:           ## unit + integration tests (no infra)
	uv run pytest

lint:           ## ruff + mypy across all Python
	uv run ruff check app tests samples eval
	uv run ruff format --check app tests samples eval
	uv run mypy app samples eval

eval:           ## gold-set quality gate (needs a model: Ollama locally, or Anthropic)
	uv run python -m eval.run

samples:        ## download the real-world robustness corpus (gitignored)
	uv run python samples/download_samples.py

up:             ## bring up the local stack (api + worker + rabbitmq + minio + postgres)
	docker compose up --build

down:
	docker compose down -v
