# Quickstart — Document Annotation Service

Clone-to-running, plus a two-tenant demo that exercises the async loop,
idempotency, and tenant isolation. (Commands are the target developer experience;
they become real as the slice is implemented.)

## Prerequisites

- Docker + docker-compose
- An Anthropic API key (for the real annotation stage)

## 1. Configure

```bash
cp .env.example .env
# edit .env: set ANTHROPIC_API_KEY and the model id (Haiku-tier).
# Two demo tenants are pre-seeded in the token->tenant map, e.g.:
#   TENANT_TOKENS=tokenA:tenant-a,tokenB:tenant-b
```

Secrets live only in `.env` (gitignored) and the LLM gateway — never in code or
images.

## 2. Run

```bash
docker-compose up --build      # api + worker + rabbitmq + minio + postgres
```

## 3. Demo

```bash
# Upload as tenant A -> 202 + job_id immediately (processing continues async)
JOB=$(curl -s -X POST http://localhost:8000/documents \
  -H "Authorization: Bearer tokenA" \
  -F "file=@samples/out/report_clean.pdf" | jq -r .job_id)

# Poll until completed
curl -s http://localhost:8000/annotations/$JOB \
  -H "Authorization: Bearer tokenA" | jq

# Idempotency: re-upload identical content as tenant A -> SAME job_id, no reprocess
curl -s -X POST http://localhost:8000/documents \
  -H "Authorization: Bearer tokenA" \
  -F "file=@samples/out/report_clean.pdf" | jq -r .job_id   # == $JOB

# Tenant isolation: tenant B fetching A's job -> 404 (not the record)
curl -s -o /dev/null -w "%{http_code}\n" \
  http://localhost:8000/annotations/$JOB \
  -H "Authorization: Bearer tokenB"                          # 404
```

## 4. Tests & eval

```bash
# Fast, NO infra — domain + the API wired to fakes (contract, cross-tenant, idempotency, failure)
pytest tests/unit tests/integration

# Full pipeline on REAL infra — requires the stack up
docker-compose up -d
pytest tests/e2e

make eval                    # gold-set thresholds + groundedness check
```

## What "done" looks like

- Upload returns `202 + job_id` sub-second; processing outlives the request.
- A completed job returns an `Annotation` that conforms to the contract and is
  grounded in the document.
- Re-upload returns the same `job_id` with no reprocessing.
- Cross-tenant lookup returns `404`.
- A corrupt/unsupported file ends `failed` naming the stage.
- `make eval` passes its thresholds (document-type accuracy, entity P/R,
  schema-valid rate, groundedness).
