# Phase 0 — Research & Resolved Decisions

All architectural decisions are **already resolved** in `PLAN.md` and the
decision log (`docs/speckit_seed.md` §3); this file consolidates them in
decision / rationale / alternatives form. There are **no open NEEDS
CLARIFICATION** items.

## D1 — Local runtime: real infra behind ports (no cloud emulator)

- **Decision**: Run RabbitMQ + MinIO + Postgres locally via docker-compose; the
  core talks to ports, not vendors.
- **Rationale**: Robust, auth-free, low-friction clone-and-run; depends on
  contracts, so the cloud target is an adapter/deploy choice, not a rewrite.
- **Alternatives**: Pure AWS-native (reviewer must deploy — friction); LocalStack
  (Community edition discontinued/auth-gated Mar 2026 — reviewer friction).

## D2 — Async mechanism & broker: RabbitMQ behind `Messaging`

- **Decision**: One `Messaging` port; RabbitMQ provides queue = work, topic
  exchange = stage events, dead-letter exchange = DLQ.
- **Rationale**: Durable queue keeps DLQ/retry/visibility semantics the
  failure-handling criteria reward; RabbitMQ maps most legibly to SQS/EventBridge/
  DLQ for AWS-fluent reviewers and is the fastest Python path.
- **Alternatives**: Pure event bus (loses DLQ/retry/visibility); NATS (cleaner
  only if k8s were the primary target).

## D3 — Blob + store: MinIO + Postgres

- **Decision**: MinIO (S3 API) behind `BlobStore` for raw; Postgres behind
  `AnnotationStore` for curated + annotated rows.
- **Rationale**: Real S3 API locally → adapter barely changes for cloud S3;
  Postgres is on their stack and maps to DynamoDB (serverless) or RDS (k8s).
- **Alternatives**: Local filesystem blob (no real object-store semantics);
  SQLite (loses concurrent-writer + role/grant story).

## D4 — LLM access: LiteLLM → Anthropic, tool-use, Haiku-tier

- **Decision**: `LLMClient` port; LiteLLM SDK → Anthropic; Anthropic **tool-use**
  to force strict JSON; Haiku-tier model; model id + key in env.
- **Rationale**: Tool-use gives schema-constrained output (correctness +
  injection safety); gateway brings governance (keys, budgets, spend); Haiku-tier
  is right-sized for bounded extraction.
- **Alternatives**: Direct provider SDK (loses governance); larger model
  (unjustified cost); free-text JSON parsing (brittle, unsafe).

## D5 — Annotation agent: single bounded unit

- **Decision**: classify document type → route to a type-specific extraction
  schema → extract via tool-use → validate/repair against the schema. No tools
  with side effects, no autonomy.
- **Rationale**: Bounded, deterministic task → pipeline, not autonomy; multi-agent
  fails the "when not to reach for an agent" test and reads as over-engineering.
- **Alternatives**: Multi-agent orchestration (over-engineered); single opaque
  prompt (loses per-type schemas and validate/repair).

## D6 — Access control: thin Bearer token → tenant

- **Decision**: A FastAPI dependency maps a Bearer token to a tenant + scopes via
  a static config map; tenant is derived from the credential, never a header.
- **Rationale**: Makes the tenancy story real and closes the spoofing hole at the
  cheap end; full IdP is the documented production path.
- **Alternatives**: Header-supplied tenant (honor-system isolation a reviewer
  flags); full OAuth/OIDC server (out of scope for 8h).

## D7 — Data model: persisted stages, forward-only

- **Decision**: raw (blob) → curated (row) → annotated (row); state machine
  `queued → processing(raw→curated→annotated) → completed | failed`, forward-only.
- **Rationale**: Replayability + per-stage failure isolation; forward-only writes
  make at-least-once delivery safe (no double-process / no overwrite of completed).
- **Alternatives**: Single opaque step (loses replay + isolation).

## D8 — Idempotency: content-hash job ids

- **Decision**: `job_id = hash(tenant_id + content_bytes + filename)`; re-upload
  returns the same id and does not reprocess; conditional forward-only writes.
- **Rationale**: Re-upload returns same job; at-least-once delivery cannot
  double-process; tenant in the hash keeps ids tenant-scoped.
- **Alternatives**: Random UUID (no dedup); hash without tenant (cross-tenant id
  collision).

## D9 — Evaluation: deterministic gold-set + groundedness

- **Decision**: Generate samples from known ground truth; `eval/` scores
  document-type accuracy, entity precision/recall, schema-valid rate vs the gold
  set with thresholds (`make eval`); deterministic groundedness check (extracted
  values must appear in curated text; ungrounded → flagged + lower confidence).
- **Rationale**: Antidote to silent quality failure; ground truth is free because
  we generate the samples; more rigorous than an LLM judge for extraction.
- **Alternatives**: LLM-as-judge / online + drift (documented, not built in 8h);
  no eval (the exact "fails silently" risk called out).

## D10 — Security depth: cheap controls built, full posture documented

- **Decision**: Build secrets-out-of-repo, per-component least-privilege creds,
  input size/type limits, parse timeouts + page/sheet caps, spreadsheet
  values-not-formulas, injection-safe structured output (no ambient authority),
  non-root containers. Document the full IAM/encryption/network/supply-chain
  posture.
- **Rationale**: High-signal, low-cost controls; reviewer is a security architect,
  so specificity earns credit; full posture is an 8h non-goal.
- **Alternatives**: Full posture build (out of time-box); no controls (fails the
  untrusted-input principle).

## Dependency best-practice notes

- **PDF parsing**: `pypdf` for text PDFs; enforce a page cap + parse timeout; a
  scanned image-only PDF yields no extractable text → low-confidence/explicit
  failure (no OCR in this slice; documented as an evolution).
- **Spreadsheet parsing**: `openpyxl` with `data_only=True` to read **values, not
  formulas**; enforce a sheet cap.
- **RabbitMQ**: manual ack after a stage commits; `x-dead-letter-exchange` on the
  work queue; prefetch=1 on the worker; ensure the consumer's effective
  visibility/redelivery window exceeds worker runtime.
- **Postgres**: app role is a non-superuser with grants limited to the app tables;
  `tenant_id` non-null on every row; forward-only updates via guarded `WHERE`
  clauses on current stage/status.
