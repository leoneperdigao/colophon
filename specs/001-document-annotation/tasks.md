---
description: "Task list for Document Annotation Service (must-build slice)"
---

# Tasks: Document Annotation Service

**Input**: Design documents from `specs/001-document-annotation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md

**Tests**: TDD is a constitution non-negotiable (VII) — test tasks are included and MUST be written and fail before implementation.

**Organization**: Tasks grouped by user story (US1–US5 from spec.md). The walking skeleton (US1–US5) is built and unit-tested against **fakes with no infra**; real infra adapters are swapped in along ports afterward (Phase 8).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallel-safe — different files, no dependency on an incomplete task. Per the constitution, `[P]` is used **only along ports** (parsing, llm, blob, store, messaging adapters) and for genuinely independent files; the domain core and composition root are never parallelized.
- **[Story]**: US1–US5; Setup/Foundational/Infra/Polish phases carry no story label.

## Scope guard (do NOT create tasks for — documented only)

Postgres RLS · EventBridge/Step Functions as separate infra · LiteLLM proxy container · CDK/k8s manifests · OTel tracing · full identity/IdP/OAuth · full multi-tenant isolation/silo/per-tenant KMS · malware scanning, WAF, rate limiting · LLM-as-judge · online/drift eval. These belong in the README as "documented, not built."

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project skeleton and tooling.

- [ ] T001 Create the repo layout per plan.md: `app/{domain,application/{ports,services},adapters/{inbound/http,outbound/{messaging,blob,store},llm,parsing},worker,config}`, `tests/{unit,integration,e2e,fakes}`, `eval/`, `samples/`, `infra/` with `__init__.py` files where needed
- [ ] T002 Initialize the Python 3.12 project in `pyproject.toml` with FastAPI, uvicorn, pydantic, pika (or aio-pika), minio (or boto3), psycopg, litellm, pypdf, openpyxl, pytest, httpx; pin versions in a lockfile
- [ ] T003 [P] Configure ruff + black + mypy and a `pytest` config in `pyproject.toml`/`pytest.ini`
- [ ] T004 [P] Create `.env.example` (no secrets) with `ANTHROPIC_API_KEY`, model id, `TENANT_TOKENS`, and per-component infra creds; confirm `.env` is gitignored
- [ ] T005 [P] Add a `Makefile` with `up`, `test`, `eval` targets (commands may stub until later phases)

**Checkpoint**: Project imports, lints, and `pytest` runs (zero tests yet).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Domain + ports + fakes + composition root. Blocks all user stories. **Sequential and coherent — do not parallelize the domain core or composition root.**

⚠️ **CRITICAL**: No user-story work begins until this phase is complete.

- [ ] T006 Unit tests for domain entities + state machine in `tests/unit/test_domain.py`: `Job` status/stage transitions are forward-only; `failed` carries `{stage, error}`; `Annotation`/`KeyEntity`/`Tenant` shape (write first, must fail)
- [ ] T007 Unit test for idempotency in `tests/unit/test_idempotency.py`: `job_id` = lowercase-hex **SHA-256** over `tenant_id`‖`0x00`‖`filename`‖`0x00`‖content-bytes (deterministic, **not** Python `hash()`) is stable across processes and tenant-scoped (same content + different tenant → different id)
- [ ] T008 Implement pure domain entities in `app/domain/` (`job.py`, `stage_result.py`, `annotation.py`, `key_entity.py`, `tenant.py`) with `tenant_id` as a field; no IO
- [ ] T009 Implement the forward-only state machine and `compute_job_id()` in `app/domain/` (make T006, T007 pass)
- [ ] T010 Define the 5 port Protocols in `app/application/ports/`: `BlobStore`, `Messaging`, `AnnotationStore`, `DocumentParser`, `LLMClient` (interfaces only, from contracts/data-model)
- [ ] T011 [P] Implement in-memory fakes for every port in `tests/fakes/` (`fake_blob.py`, `fake_messaging.py`, `fake_store.py`, `fake_parser.py`, `fake_llm.py`)
- [ ] T012 Implement the composition root in `app/config/` (env-driven wiring + the static `token→tenant` map loader); selects fakes vs real adapters by env

**Checkpoint**: Domain + ports + fakes exist; domain unit tests green with no infra running.

---

## Phase 3: User Story 1 — Submit a document, get an immediate job id (Priority: P1) 🎯 MVP

**Goal**: `POST /documents` authenticates, derives tenant from the credential, writes raw, creates the job, enqueues work, and returns `202 + job_id` immediately.

**Independent Test**: Upload with a valid token → `202 + job_id`; missing/invalid token → `401`, no job created.

### Tests (write first, must fail)

- [ ] T013 [P] [US1] Contract test for `POST /documents` in `tests/integration/test_post_documents.py` (202 shape, 401 without token, 415/400 on bad upload) against the app wired to fakes (no infra)
- [ ] T014 [P] [US1] Unit test for the auth dependency in `tests/unit/test_auth.py`: token→tenant resolution; tenant is never read from a header/body
- [ ] T015 [US1] Unit test for `IngestDocument` in `tests/unit/test_ingest.py`: writes raw, creates `queued` job, enqueues exactly one work message carrying `tenant_id + job_id`

### Implementation

- [ ] T016 [US1] Implement the Bearer→tenant auth dependency in `app/adapters/inbound/http/auth.py` (config map; 401 on miss; tenant from credential only)
- [ ] T017 [US1] Implement `IngestDocument` service in `app/application/services/ingest_document.py` (BlobStore.put raw → AnnotationStore.create job → Messaging.enqueue)
- [ ] T018 [US1] Implement `POST /documents` router in `app/adapters/inbound/http/documents.py` (multipart, returns 202 + job_id)
- [ ] T019 [US1] Add upload validation (size cap + content-type allowlist for PDF/spreadsheet) in the router; 400/415 on violation (security control)

**Checkpoint**: US1 green against fakes — upload returns 202 + job_id, auth enforced.

---

## Phase 4: User Story 2 — Retrieve metadata by job id (Priority: P1)

**Goal**: `GET /annotations/{job_id}` returns status/stage and, when complete, the annotation. A stub worker advances raw→curated→annotated so a job reaches `completed`.

**Independent Test**: For a processed job, GET returns `completed` + a contract-conformant annotation; unknown id → `404`.

### Tests (write first, must fail)

- [ ] T020 [P] [US2] Contract test for `GET /annotations/{job_id}` in `tests/integration/test_get_annotation.py` (200 processing vs completed shape, 404 unknown) against the app wired to fakes (no infra)
- [ ] T021 [US2] Unit test for `ProcessPipeline` (stub worker) in `tests/unit/test_pipeline.py`: advances stages forward-only and persists each; uses fake parser + fake LLM
- [ ] T022 [US2] Unit test for `GetAnnotation` in `tests/unit/test_get_annotation.py`: returns status/stage/result for the owning tenant

### Implementation

- [ ] T023 [US2] Implement `ProcessPipeline` service in `app/application/services/process_pipeline.py` (raw→curated via DocumentParser, curated→annotated via LLMClient; persist + forward-only writes)
- [ ] T024 [US2] Implement `GetAnnotation` service in `app/application/services/get_annotation.py` (tenant-scoped read)
- [ ] T025 [US2] Implement `GET /annotations/{job_id}` router in `app/adapters/inbound/http/annotations.py`
- [ ] T026 [US2] Implement the worker entrypoint in `app/worker/main.py` consuming the work queue and invoking `ProcessPipeline` (stub LLM/parser via composition root for now)

**Checkpoint**: Full accept→process→retrieve loop green against fakes (MVP demoable end-to-end with stubs).

---

## Phase 5: User Story 3 — Tenant-isolated retrieval (Priority: P2)

**Goal**: A job is retrievable only by its owning tenant; another tenant's id is indistinguishable from unknown (`404`).

**Independent Test**: Create a job under tenant A; fetch with tenant B → `404`; fetch with tenant A → `200`.

### Tests (write first, must fail)

- [ ] T027 [P] [US3] Cross-tenant lookup test in `tests/integration/test_cross_tenant.py` (app wired to fakes, no infra): A creates, B gets → 404; A gets → 200
- [ ] T028 [US3] Unit test in `tests/unit/test_tenant_scoping.py`: store reads/writes are filtered by `tenant_id`; no cross-tenant existence leak

### Implementation

- [ ] T029 [US3] Enforce `tenant_id` filtering on every read/write in `GetAnnotation` and the store port usage (404 for out-of-tenant, identical to unknown)
- [ ] T030 [US3] Thread `tenant_id` into blob keys (`{tenant_id}/raw/...`), message metadata, and structured logs across services

**Checkpoint**: Cross-tenant test green; tenant seam verified end-to-end.

---

## Phase 6: User Story 4 — Idempotent re-upload (Priority: P2)

**Goal**: Re-uploading identical content for the same tenant returns the same `job_id` with no reprocessing; different tenants get distinct jobs.

**Independent Test**: Upload same file twice as tenant A → identical `job_id`, processed once.

### Tests (write first, must fail)

- [ ] T031 [P] [US4] Integration idempotency test in `tests/integration/test_idempotency.py` (app wired to fakes, no infra): duplicate upload → same id, single processing run; two tenants → distinct ids
- [ ] T032 [US4] Unit test for forward-only conditional writes in `tests/unit/test_forward_only.py`: a redelivered/duplicate stage message does not overwrite a completed result

### Implementation

- [ ] T033 [US4] Make `IngestDocument` idempotent: compute `job_id` and short-circuit if the job already exists (return existing id, no enqueue)
- [ ] T034 [US4] Implement forward-only conditional writes in the store usage (guarded on current stage/status) to make at-least-once delivery safe

**Checkpoint**: Duplicate uploads dedupe; redelivery cannot double-process.

---

## Phase 7: User Story 5 — Explicit staged failure (Priority: P3)

**Goal**: Unprocessable documents reach `failed` naming the stage + error; per-stage retry up to N, then DLQ.

**Independent Test**: Submit a corrupt/unsupported file → job `failed` with the failing stage and an error.

### Tests (write first, must fail)

- [ ] T035 [P] [US5] Integration failure test in `tests/integration/test_failure.py` (app wired to fakes, no infra): corrupt file → `failed{stage, error}`, retrievable
- [ ] T036 [US5] Unit test for retry/DLQ policy in `tests/unit/test_retry_dlq.py`: stage retried ≤ N then routed to DLQ + `failed` (not retried indefinitely)

### Implementation

- [ ] T037 [US5] Implement per-stage retry with a bounded attempt counter and `failed{stage, error}` transition in `ProcessPipeline`/worker
- [ ] T038 [US5] Wire DLQ semantics in the messaging usage (dead-letter after N attempts); ensure failures are captured, not swallowed

**Checkpoint**: All five user stories independently green against fakes.

---

## Phase 8: Real infrastructure adapters & real pipeline (swap fakes along ports)

**Purpose**: Replace fakes with real adapters behind the unchanged ports, then the real annotation agent. **These tasks are the parallel-safe unit — one subagent/worktree per port** (Constitution; `[P]`). The composition root edit (T046) is sequential.

- [ ] T039 [P] Implement the MinIO `BlobStore` adapter in `app/adapters/outbound/blob/minio_blob.py` (tenant-prefixed keys); port test reuse in `tests/e2e/test_blob_adapter.py`
- [ ] T040 [P] Implement the Postgres `AnnotationStore` adapter in `app/adapters/outbound/store/postgres_store.py` (jobs/curated/annotated, `tenant_id` non-null, forward-only guarded updates) + schema/migration
- [ ] T041 [P] Implement the RabbitMQ `Messaging` adapter in `app/adapters/outbound/messaging/rabbitmq.py` (work queue + topic exchange events + DLX; manual ack; prefetch=1)
- [ ] T042 [P] Implement the PDF + spreadsheet `DocumentParser` adapters in `app/adapters/parsing/` (pdf via pypdf with page cap + timeout; spreadsheet via openpyxl `data_only=True` — **values not formulas** — with sheet cap)
- [ ] T043 [P] Implement the LiteLLM→Anthropic `LLMClient` adapter in `app/adapters/llm/litellm_anthropic.py` (Anthropic tool-use for strict JSON; model id + key from env)
- [ ] T044 Implement the single bounded annotation agent in `app/application/services/annotate.py`: classify → route to type-specific extraction schema → extract (tool-use) → validate/repair; document content delimited as untrusted, no tools/side effects (injection-safe)
- [ ] T045 [P] Author `docker-compose.yml` (api + worker + rabbitmq + minio + postgres) with non-root users and per-component least-privilege creds
- [ ] T046 Wire real adapters in the composition root (`app/config/`) by env; keep fakes for unit tests
- [ ] T047 End-to-end test on real infra in `tests/e2e/test_pipeline_real.py`: upload a real PDF + a real spreadsheet under two tenants → completed annotations (run with infra up)

**Checkpoint**: `docker-compose up` runs the real system; e2e green on real infra.

---

## Phase 9: Samples & Evaluation

**Purpose**: Ground-truth samples + deterministic eval gate.

- [ ] T048 [P] Implement the sample generator in `samples/generate.py`: emit PDFs + spreadsheets **from known structured records**, writing each doc plus its ground-truth labels (document_type, key_entities)
- [ ] T049 [P] Generate the sample corpus covering edge cases (clean/multi-page PDF, image-only PDF, simple/multi-sheet spreadsheet, corrupt file, duplicate, embedded-instructions doc, two tenants, optional non-English)
- [ ] T050 [US-eval] Implement the gold-set scorer in `eval/score.py`: document-type accuracy, entity precision/recall, schema-valid rate vs ground truth
- [ ] T051 [US-eval] Implement the deterministic groundedness check in `eval/groundedness.py`: extracted values must appear in curated text; ungrounded → flagged + lower confidence
- [ ] T052 Wire `make eval` (and a pytest target) with thresholds (SC-003 ≥90% type accuracy, SC-004 ≥0.80 P/R, SC-005 100% schema-valid, SC-006 ≥95% grounded); fail under threshold
- [ ] T053 Surface confidence + flag low-confidence/ungrounded results in the annotation output path

**Checkpoint**: `make eval` passes its thresholds against the ground-truth corpus.

---

## Phase 10: Polish & Cross-Cutting

**Purpose**: Security hardening sweep, README, and quickstart validation.

- [ ] T054 Security sweep: confirm no secrets in repo, per-component least-privilege creds, parse timeouts + page/sheet caps enforced, spreadsheet values-not-formulas, non-root containers, document content treated as untrusted (no ambient authority)
- [ ] T055 [P] Add structured JSON logging keyed by `tenant_id`/`job_id`/`stage` across services and worker
- [ ] T056 [P] Sketch `infra/` (serverless + k8s) as documentation only (no working stack)
- [ ] T057 Write `README.md` covering PLAN.md §14: decisions & why, tradeoffs cut under time pressure, what another day buys (incl. agentic evolution), production-readiness (failure handling, idempotency, observability, cost), security posture, access control (credential→tenant, pool-vs-silo, IdP path), evaluation (gold-set + groundedness + confidence; judge/online/drift documented), how to run locally, cloud migration (serverless + k8s) — list every deferred item as "documented, not built"
- [ ] T058 Run `quickstart.md` end-to-end and confirm the definition of done (two tenants, idempotency, cross-tenant 404, `make eval`)

---

## Dependencies & Execution Order

- **Setup (Phase 1)** → no deps.
- **Foundational (Phase 2)** → depends on Setup; **blocks all user stories**.
- **User Stories (Phases 3–7)** → depend on Foundational; built against fakes. US1→US2 are the MVP loop; US3–US5 refine it. Each is independently testable.
- **Real infra (Phase 8)** → depends on the ports being fixed (Phase 2) and the stories' service logic (3–7); swaps fakes for adapters along ports `[P]`.
- **Eval (Phase 9)** → depends on the real pipeline (Phase 8) for scored runs (scorer/groundedness code can be written in parallel with Phase 8).
- **Polish (Phase 10)** → depends on all above.

### Parallel Opportunities

- Phase 1: T003, T004, T005 in parallel.
- Phase 2: T011 (fakes) parallel after ports (T010) exist; domain core (T008, T009) stays sequential.
- **Phase 8 is the main parallel front**: T039–T043 + T045 are one-subagent-per-port `[P]` (blob, store, messaging, parsing, llm, compose) over fixed interfaces; T044 (agent) follows the LLM adapter; T046 (composition root) is sequential and integrates them.
- Phase 9: T048, T049 parallel; scorer/groundedness can be written ahead of scored runs.

---

## Implementation Strategy

### MVP First

1. Phase 1 Setup → Phase 2 Foundational → Phase 3 US1 → Phase 4 US2.
2. **STOP and VALIDATE**: accept→process→retrieve loop works against fakes.

### Incremental Delivery

US3 (isolation) → US4 (idempotency) → US5 (failure), each independently testable against fakes. Then Phase 8 swaps in real infra (this is where Superpowers fans out subagents along ports in worktrees), Phase 9 adds the eval gate, Phase 10 hardens + documents.

### Handoff note

This task list is the contract Superpowers executes (Constitution VIII). Use `superpowers:test-driven-development` per task, `superpowers:using-git-worktrees` + `superpowers:dispatching-parallel-agents` for Phase 8 (ports only), and `superpowers:verification-before-completion` before claiming any task done.

## Notes

- `[P]` = different files, no incomplete-task dependency — used along ports only.
- Verify each test fails before implementing.
- Commit after each task or logical group; never commit on red.
- Stop at any checkpoint to validate a story independently.
