# Load tests

On-demand load tests (not run in CI — they need the full stack up). The strategy,
SLOs, and chaos cases are in [ADR-0010](../docs/adr/0010-load-testing-and-robustness.md).

## Ingestion plane — `ingest.js` (k6)

Ramps concurrent `POST /documents` and asserts the accept-path SLOs (p99 < 500ms,
< 1% errors). The accept path is decoupled from processing, so it should stay flat
under burst.

```bash
docker-compose up -d
uv run python samples/download_samples.py        # provides the sample PDF
k6 run -e BASE_URL=http://localhost:8000 -e TOKEN=tokenA loadtest/ingest.js
```

## Processing plane (documented — see ADR-0010)

Enqueue *N* jobs, measure drain time / queue depth / per-stage latency. LLM
latency dominates, so capacity scales with worker count (KEDA on queue depth).
Resilience cases: kill a worker mid-job (idempotency + redelivery recover), restart
the broker, inject LLM timeouts, feed poison docs (→ DLQ).
