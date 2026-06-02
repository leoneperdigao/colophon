# Implementation Plan: Document Annotation Service

**Branch**: `001-document-annotation` | **Date**: 2026-06-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-document-annotation/spec.md`

## Summary

An event-driven service that accepts a document, returns a `job_id` immediately
(202), and processes it asynchronously through **raw → curated → annotated**
stages, persisting each stage and serving the final structured metadata by id.
Technical approach: a **light hexagonal** core (domain + application depend only
on ports) wired by a composition root to local adapters — RabbitMQ (work queue +
events + DLQ), MinIO (raw blobs), Postgres (curated/annotated rows), and
LiteLLM → Anthropic (tool-use) — with a single bounded annotation agent
(classify → type-specific extract → validate/repair). Tenancy is threaded from
the Bearer credential through every store key, row, message, and log. Quality is
gated by a deterministic gold-set eval + groundedness check.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI (inbound HTTP), pika/aio-pika (RabbitMQ),
boto3/minio (S3 API), psycopg/SQLAlchemy Core (Postgres), LiteLLM → Anthropic
(LLM, tool-use), pypdf + openpyxl (parsing, values-not-formulas), pydantic
(schema validation), pytest (tests)

**Storage**: MinIO (raw, immutable, tenant-prefixed keys) + Postgres
(`jobs`, `curated`, `annotated` rows, `tenant_id` on every row)

**Testing**: pytest in three layers — **unit** (domain/application vs in-memory
fakes, no infra), **integration** (the API wired to fakes — contract,
cross-tenant, idempotency, failure — fast/offline), and **e2e** (the full pipeline
on real infra via docker-compose). Plus the `eval/` gold-set + groundedness
`make eval` target with thresholds

**Target Platform**: Linux containers via docker-compose (api + worker + rabbitmq
+ minio + postgres)

**Project Type**: Asynchronous web service + background worker (single repo)

**Performance Goals**: Upload acknowledged sub-second (well within any request
timeout); processing decoupled and may exceed a request timeout; throughput is
not a target for this slice

**Constraints**: Secrets out of repo; per-component least-privilege creds;
untrusted-input limits (size/content-type, parse timeouts, page/sheet caps,
spreadsheet values not formulas); annotation step has no tools / no side effects;
non-root containers; forward-only stage transitions; idempotent job ids

**Scale/Scope**: Take-home slice — a handful of tenants from a static token map,
small sample corpus; correctness and clean seams over scale

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | How this plan complies | Status |
|---|-----------|------------------------|--------|
| I | Hexagonal, Light | 5 ports (`BlobStore`, `Messaging`, `AnnotationStore`, `DocumentParser`, `LLMClient`), each with a real second impl (fake + infra adapter); domain imports no adapter/SDK | PASS |
| II | Scope Discipline | Plan covers must-build slice only; deferred items listed as "documented, not built" (see Deferred section) | PASS |
| III | Runnable Locally | docker-compose brings up the whole system; fakes keep it runnable if an adapter fights the env | PASS |
| IV | Security by Default | `.env.example` only; per-component creds; input validation + parse caps; values-not-formulas; no ambient authority in annotate; non-root | PASS |
| V | Tenancy Boundary | `tenant_id` from credential threaded through keys/rows/messages/logs; tenant-scoped GET → 404; cross-tenant test | PASS |
| VI | Simplicity over Cleverness | Single bounded annotation agent; no multi-agent; no autonomy | PASS |
| VII | Test-First | TDD against fakes (no infra) first; gold-set eval thresholds gate quality | PASS |
| VIII | Everything Traceable | spec/plan/research/data-model/contracts/tasks committed; decisions in research.md | PASS |

**Result**: PASS — no violations. Complexity Tracking is empty (nothing to justify).

## Project Structure

### Documentation (this feature)

```text
specs/001-document-annotation/
├── plan.md              # This file
├── research.md          # Phase 0 — resolved decisions (decision/rationale/alternatives)
├── data-model.md        # Phase 1 — entities, state machine, validation rules
├── quickstart.md        # Phase 1 — clone-to-running + demo (two tenants)
├── contracts/
│   └── openapi.yaml      # Phase 1 — POST /documents, GET /annotations/{job_id}
└── tasks.md             # Phase 2 — /speckit-tasks (NOT created here)
```

### Source Code (repository root)

```text
app/
  domain/                # Job, StageResult, Annotation, KeyEntity, Tenant — pure, no IO; tenant_id is a field
  application/
    ports/               # BlobStore, Messaging, AnnotationStore, DocumentParser, LLMClient (Protocols)
    services/            # IngestDocument, ProcessPipeline, GetAnnotation
  adapters/
    inbound/http/        # FastAPI routers + auth dependency (Bearer → tenant/scopes)
    outbound/
      messaging/         # rabbitmq adapter (queue=work, topic=events, DLX=DLQ)
      blob/              # minio/s3 adapter, tenant-prefixed keys
      store/             # postgres adapter (jobs/curated/annotated, tenant_id on rows)
    llm/                 # LiteLLM → Anthropic adapter behind LLMClient (tool-use)
    parsing/             # pdf + spreadsheet adapters behind DocumentParser
  worker/                # background consumer entrypoint (runs the pipeline)
  config/                # composition root, env-driven wiring, token→tenant map
tests/
  unit/                  # domain + application vs fakes (no infra)
  integration/           # API wired to fakes — contract, cross-tenant, idempotency, failure (no infra)
  e2e/                   # full pipeline on real infra (docker-compose)
  fakes/                 # in-memory adapters implementing each port
eval/                    # gold-set scoring + groundedness check + thresholds
samples/                 # generator (docs + ground-truth labels)
infra/                   # CDK / k8s SKETCH ONLY (documented, not built)
docker-compose.yml
Makefile                 # eval, test, up targets
.env.example
README.md
```

**Structure Decision**: Single-repo light-hexagonal layout (PLAN.md §5). The
domain and application layers are infra-free and tested against `tests/fakes/`;
adapters are the only code that imports an SDK or framework. The worker and the
HTTP inbound are two entrypoints over the same application services, wired by
`app/config/` per environment. This is the seam that makes the serverless/k8s
migration a wiring change, not a rewrite.

## Phasing (build order — vertical slices, TDD)

1. **Walking skeleton**: domain (+tenant_id) + ports + application services +
   unit tests vs fakes → HTTP + auth dep + **stub worker** that just advances
   stages → fetch by id. Tenant-scoped lookup + cross-tenant test green with
   fakes, no infra.
2. **Real infra adapters** behind the same ports: RabbitMQ, MinIO, Postgres;
   docker-compose; e2e on real infra with a stub LLM.
3. **Parsing adapters + LLM adapter + annotation agent**: pdf/spreadsheet parse;
   LiteLLM → Anthropic tool-use; classify → extract → validate/repair; real
   raw→curated→annotated pipeline.
4. **Samples + eval + security controls**: ground-truth sample generator; `eval/`
   gold-set + groundedness + thresholds (`make eval`); wire cheap security
   controls; confirm clone-and-run.
5. **README**: decisions, tradeoffs, another-day, production-readiness, security,
   access control, evaluation, agentic evolution, migration mapping.

Parallelize **only along ports** (parsing, llm, blob, store) via subagents/
worktrees once port interfaces are fixed in phase 1; keep domain core and
composition root sequential.

## Migration mapping (documented, not built)

| Concern | Local (delivered) | Serverless (AWS) | Kubernetes |
|---------|-------------------|------------------|------------|
| BlobStore | MinIO | S3 | MinIO / S3 |
| AnnotationStore | Postgres | DynamoDB | RDS / Postgres operator |
| Messaging: work | RabbitMQ queue | SQS + DLQ | RabbitMQ (Amazon MQ / operator) |
| Messaging: events | RabbitMQ topic exchange | EventBridge | broker topic / NATS |
| Worker | container/process | Lambda (container image) via SQS | Deployment + KEDA on queue depth |
| Inbound HTTP | uvicorn/FastAPI | API Gateway + Lambda (Mangum) | Service + Ingress |
| Auth | token→tenant map | API Gateway JWT authorizer | middleware/sidecar + IdP |

Gotchas for README: SQS visibility timeout must exceed worker runtime; package
the worker as a **container-image** Lambda (PDF/LLM deps exceed layer limits);
Lambda 15-min ceiling → chunk or Step Functions for very large docs; on k8s scale
workers on queue depth (KEDA).

## Deferred — documented, not built (Constitution II; PLAN.md §13)

Postgres RLS · EventBridge/Step Functions as separate infra (worker runs stages
in-process) · LiteLLM **proxy** container (SDK used) · CDK/k8s manifests (sketch
in `infra/` only) · OTel tracing · full identity/IdP/OAuth (thin token→tenant is
the whole auth build) · full multi-tenant isolation / silo / per-tenant KMS ·
malware scanning, WAF, rate limiting · LLM-as-judge · online/drift eval. The
README explains each split and how the ports make them swap-in, not rewrites.

## Complexity Tracking

> No Constitution Check violations — this section is intentionally empty.
