# Observability — built vs. documented

**Decision (2026-06-02):** keep a minimal, stdlib-based structured-logging seam for
the take-home; document the world-class production path. OpenTelemetry is on the
project's out-of-scope list (`PLAN.md` §13 / constitution) — *documented, not
built* — and restraint is a graded signal.

## Built now (the minimal seam)

`app/observability.py`, stdlib `logging` only:

- `log_event(logger, event, *, tenant_id, job_id, stage=None, level=…)` emits an
  event with **`tenant_id` / `job_id` / `stage`** attached as structured context.
- `JsonFormatter` renders one JSON object per line.
- `configure_logging()` installs the JSON handler at the **process entrypoint
  only**, and no-ops if the host (uvicorn/pytest) already configured logging.
- Services log the lifecycle: `job.created`, `job.duplicate`, `stage.started`,
  `stage.advanced`, `job.completed`, `job.failed` — every line correlatable by
  tenant and job.

Why minimal: it's ~40 lines, no dependencies, and lives behind a tiny seam, so
the upgrade below is an **internal swap**, not a rewrite.

## Documented — the production path (not built here)

### 1. `structlog` for logs

Replace `log_event` with `structlog` processors and **context binding** via
`contextvars` (bind `tenant_id`/`job_id`/`stage` once at the edge of a request /
message, every downstream log inherits it). JSON renderer in prod, console
renderer in dev. The `app/observability` module is the only thing that changes.

### 2. OpenTelemetry for traces + metrics

The high-value win is **trace context across the async boundary**: the work
outlives the request, so a single job should be one distributed trace spanning
**API → RabbitMQ → worker → LLM**.

- **Tracing:** OTel SDK + auto-instrumentation for FastAPI and the worker.
  **Propagate `traceparent` through the message:** inject the span context into
  RabbitMQ message headers on publish, extract and continue it on consume. Each
  stage (raw/curated/annotated) and each LLM call becomes a child span.
- **Log↔trace correlation:** a structlog/OTel processor stamps `trace_id` /
  `span_id` onto every log line, so logs and traces join up.
- **Metrics:** queue depth, per-stage latency, success/failure counts, and
  **LLM token spend / cost** (LiteLLM exposes cost per call) as OTel metrics.
- **Export:** OTLP → OTel Collector → Jaeger/Tempo (traces) + Prometheus
  (metrics); on AWS, X-Ray + CloudWatch via the same exporter swap.

### 3. Why this is a swap, not a rewrite

Domain and application code never import a logging/telemetry vendor — they call
the narrow `observability` seam. Adopting structlog + OTel changes that module
and the entrypoint wiring (and adds header propagation in the messaging adapter);
the hexagonal core is untouched. Same pattern as every other port in this repo.
