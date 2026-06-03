.PHONY: install test lint eval samples up up-d down smoke media

install:        ## sync deps (add extras: uv sync --extra llm --extra infra --extra parsing)
	uv sync --dev

test:           ## unit + integration tests (no infra)
	uv run pytest

lint:           ## ruff + mypy across all Python
	uv run ruff check app tests samples eval scripts
	uv run ruff format --check app tests samples eval scripts
	uv run mypy app samples eval scripts

eval:           ## gold-set quality gate (needs a model: Ollama locally, or Anthropic)
	uv run python -m eval.run

samples:        ## download the real-world robustness corpus (gitignored)
	uv run python samples/download_samples.py

up:             ## bring up the local stack (api + worker + rabbitmq + minio + postgres)
	docker compose up --build

up-d:           ## same, detached (for `make smoke`)
	docker compose up --build -d

down:
	docker compose down -v

smoke:          ## end-to-end check against a running stack (two tenants, real PDF + xlsx)
	uv run python scripts/smoke.py

media:          ## regenerate README media (demo.gif via VHS + report.png via headless Chrome)
	scripts/make_media.sh
