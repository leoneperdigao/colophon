# 0010. Load testing & robustness strategy

- **Status:** Accepted
- **Date:** 2026-06-03

## Context

The service has two planes with very different load profiles: a fast **ingestion
plane** (`POST /documents` → 202) and a slow **processing plane** (the worker
pipeline, dominated by LLM latency). "Robust enough" means: the accept path stays
fast and available under burst, the processing plane absorbs backlog without loss
or duplication, and a single abusive document can't take a worker down. We need a
clear way to *test* that, and to record which robustness mechanisms are built vs
documented.

## Decision

**Test the two planes separately, against explicit SLOs.**

- **Ingestion plane** — HTTP load with **k6** (sketch in `loadtest/`): ramp
  concurrent uploads and assert the 202 latency/error SLOs. Because accept is
  decoupled from processing, the API should stay flat under load (it only writes
  raw, creates the job, enqueues).
- **Processing plane** — a throughput harness: enqueue *N* jobs, measure
  **drain time, queue depth, and per-stage latency percentiles**. Capacity model:
  `throughput ≈ workers × (1 / per-doc latency)`; LLM latency dominates, so scale
  **workers** (KEDA on queue depth) and LLM concurrency, and right-size the model.
- **Resilience / chaos** — kill a worker mid-job (idempotency + redelivery must
  recover with no double-processing), restart the broker, inject LLM timeouts,
  and feed poison documents (must land in the DLQ, not loop).

**SLOs (starting targets):** p99 accept latency < 500 ms; accept error rate
< 1% under target burst; queue fully drains within the agreed window after a
spike; zero lost or duplicated jobs under worker kill.

### Robustness mechanisms

**Built (and tested) now:**
- **Decoupling / backpressure** — the queue buffers bursts; the API never blocks
  on processing.
- **Bounded per-document resources** — upload size cap, parse **wall-clock
  timeout** + page/sheet/cell caps (a crafted doc can't pin a worker).
- **Idempotency** — content-hash `job_id` + forward-only writes; re-delivery and
  re-upload can't double-process (proven by tests).
- **Explicit failure** — unprocessable docs end `failed{stage}`, never silent.

**Documented (production):**
- **Retry + DLQ** — broker-native (RabbitMQ DLX), per ADR-0004.
- **Horizontal scaling** — KEDA autoscaling workers on queue depth; Lambda/SQS in
  serverless.
- **Timeouts + pooling everywhere** — LLM call, DB, broker, HTTP; connection
  pools sized to worker concurrency.
- **Graceful degradation** — if the LLM is slow/down, jobs stay queued and retry
  rather than failing fast.
- **Abuse limits** — per-tenant quotas + rate limiting (noisy-neighbour), per
  ADR-0005/0008.
- **Observability under load** — queue depth, per-stage latency, success/failure,
  and LLM token spend as the signals to alert on (ADR-0003).

## Consequences

- A concrete, repeatable way to answer "is it robust enough?" with numbers, not
  vibes; SLOs make regressions visible.
- The load-test harness itself (k6 scripts, the enqueue/drain script, chaos cases)
  is **documented and sketched**, not wired into CI — running it needs the full
  stack up; it is an on-demand / pre-release activity.

## Alternatives considered

- **No load testing** — robustness becomes a guess; the async design's whole point
  (handling load gracefully) goes unverified.
- **One end-to-end load test only** — conflates the fast accept path with the slow
  LLM path and hides where the real bottleneck (the worker/LLM) is.
