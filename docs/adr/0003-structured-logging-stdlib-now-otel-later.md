# 0003. Structured logging: stdlib now, structlog + OpenTelemetry later

- **Status:** Accepted
- **Date:** 2026-06-03

## Context

The service needs **tenant-scoped, structured, correlatable** logs (every line
keyed by `tenant_id` / `job_id` / `stage`). The world-class production setup is
`structlog` for logs plus **OpenTelemetry** for traces/metrics — and OTel is what
correlates a job *across the async boundary* (API → RabbitMQ → worker → LLM). But
OpenTelemetry is on the project's explicit out-of-scope list (`PLAN.md` §13), and
restraint is a graded signal for this 8-hour deliverable.

## Decision

Build a **minimal stdlib structured-logging seam** now — `app/observability`
(`get_logger`, `log_event`, a JSON formatter, entrypoint-only `configure_logging`)
that attaches `tenant_id`/`job_id`/`stage` context. **Document** the production
path rather than building it: `structlog` for logs (context binding via
`contextvars`) and **OpenTelemetry** for traces/metrics, with `traceparent`
propagated through RabbitMQ message headers, log↔trace correlation, and LLM
token-cost metrics. Domain/application code only touch the narrow `observability`
seam, so the upgrade is an adapter swap, not a rewrite.

## Consequences

- Scope-disciplined: ~40 lines, no dependencies, fully tested.
- The production observability story is specified and de-risked (a known swap).
- No distributed tracing in the delivered slice (logs aren't yet trace-correlated).

## Alternatives considered

- **`structlog` now** — small and world-class, but gold-plating logging for a
  take-home; deferred.
- **Full OTel SDK now** — highest value, but scope creep against `PLAN.md` §13
  (collector/exporter, span plumbing across the broker).

*Supersedes the former `docs/observability.md`.*
