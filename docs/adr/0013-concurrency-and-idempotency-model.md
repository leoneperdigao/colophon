# 0013. Concurrency & idempotency model

- **Status:** Accepted
- **Date:** 2026-06-03

## Context

Work is delivered at-least-once (RabbitMQ redelivery on nack/timeout/crash;
bounded retry per [ADR-0004](./0004-retry-and-dead-lettering-are-broker-native.md)).
The pipeline must therefore be safe under **redelivery** and, if we ever run more
than one worker, under **concurrent processing of the same job**.

Two mechanisms already make duplicate work *benign rather than corrupting*:

- **Content-addressed identity** — `job_id = SHA-256(tenant ‖ filename ‖ content)`,
  so the raw blob (`put_object` to a content-addressed key) and the annotation
  (`INSERT … ON CONFLICT DO UPDATE`) are idempotent: re-writing produces identical
  bytes/rows.
- **Forward-only state machine** — the `Job` domain object rejects backward stage
  transitions and refuses to advance/complete a terminal job.

But the domain guard is enforced **in memory**, and `ProcessPipeline.execute`
does *read-then-act* (`get_job` → check `is_terminal` → process → `update_job`).
With a single worker this is correct. With concurrent workers there is a TOCTOU
window: two consumers can both read a non-terminal job, both pass the check, and
both process — and an **unconditional** `UPDATE` could let a stale write clobber a
finished result.

## Decision

1. **Terminal jobs are immutable at the store.** `update_job` is a **conditional
   write**: Postgres `UPDATE … WHERE status NOT IN ('completed','failed')`; the
   in-memory fake mirrors it. The transition *into* a terminal state still applies
   (its source row is non-terminal); once terminal, no later write wins. This
   closes the result-clobber failure mode — the first completed/failed write is
   final — for redelivery and the concurrent case alike.

2. **Keep a single worker as the deployed default.** With one worker, redelivery
   is the only concurrency, and the `is_terminal` early-return plus idempotent
   writes already make it safe. We do **not** build a distributed claim protocol
   for the 8-hour scope.

3. **Document the multi-worker hardening** rather than build it (below).

## Consequences

- Redelivery and concurrent workers can no longer **overwrite** a finished job;
  the worst case is *duplicate processing* (both workers run the LLM), which wastes
  tokens but converges to the same content-addressed result. We surface this
  honestly rather than claim exactly-once.
- The conditional write is one SQL clause and a three-line fake guard — cheap,
  tested (unit + Postgres e2e), no new infra.

## Alternatives considered

- **Optimistic claim (the multi-worker hardening).** Make starting a job an atomic
  claim: `UPDATE jobs SET status='processing' WHERE job_id=… AND status='queued'`
  and proceed only if `rowcount == 1`, so exactly one worker owns a job. Combined
  with the conditional writes here, that gives effective once-only processing.
  Deferred: it needs a `claim_job` port method across all stores and isn't required
  at single-worker scale.
- **SELECT … FOR UPDATE SKIP LOCKED** as the queue (Postgres-as-queue). Rejected:
  RabbitMQ is the chosen broker ([ADR-0004](./0004-retry-and-dead-lettering-are-broker-native.md));
  adding a second queueing mechanism is redundant.
- **Optimistic version column** (`WHERE updated_at = <read value>`, bump on write).
  More general than the terminal guard but heavier; the terminal-immutability
  invariant is what actually protects the result, so we took the minimal form.
