# Phase 1 — Data Model

Entities are pure domain types (no IO). `tenant_id` is a first-class field on
every persisted entity and is derived from the credential, never client-supplied.

## Entities

### Tenant

| Field | Type | Notes |
|-------|------|-------|
| `tenant_id` | string | Stable id resolved from the Bearer token via the static map. Never client-supplied. |
| `scopes` | set[string] | e.g. `documents:write`, `annotations:read` (coarse, optional). |

### Job

The unit of work for one uploaded document under one tenant.

| Field | Type | Notes |
|-------|------|-------|
| `job_id` | string | Lowercase-hex **SHA-256** over `tenant_id`‖`0x00`‖`filename`‖`0x00`‖content-bytes (NUL-delimited for domain separation; deterministic across processes/hosts — **not** Python's built-in `hash()`). Idempotency key. |
| `tenant_id` | string | Owner; scopes every read/write. |
| `source_filename` | string | Original upload name (sanitised). |
| `content_type` | string | Validated MIME (pdf / spreadsheet types only). |
| `size_bytes` | int | Validated against the size cap. |
| `status` | enum | `queued` → `processing` → `completed` \| `failed`. |
| `stage` | enum | `raw` → `curated` → `annotated`. Current stage. |
| `attempts` | int | Per-stage retry counter; bounded before DLQ. |
| `error` | object? | `{stage, message}` when `status = failed`. Else null. |
| `created_at` / `updated_at` | timestamp | Audit. |

**Validation / invariants**
- `job_id` is deterministic; re-uploading identical `(tenant, content, filename)`
  yields the same id and does **not** create a second job.
- `tenant_id` is non-null on every row; all queries filter by it.
- Transitions are **forward-only** (see state machine); a `completed` or `failed`
  job is terminal and is never overwritten by a redelivered message.

### Raw stage result (BlobStore)

| Field | Type | Notes |
|-------|------|-------|
| `key` | string | `{tenant_id}/raw/{job_id}/{filename}` — tenant-prefixed. |
| `bytes` | binary | The immutable original upload. Source of truth for replay. |

### Curated stage result (AnnotationStore row)

| Field | Type | Notes |
|-------|------|-------|
| `job_id` / `tenant_id` | string | Scope. |
| `text` | string | Extracted, normalised text (spreadsheet: cell **values**, not formulas). |
| `structure` | object | Light structure (e.g. per-page / per-sheet blocks). |
| `detected_type_hint` | string? | Cheap pre-LLM hint, if any. |
| `page_or_sheet_count` | int | Pages (PDF) or sheets (spreadsheet). |

### Annotation (Annotated stage result) — the retrievable result

| Field | Type | Notes |
|-------|------|-------|
| `summary` | string | Short faithful summary. |
| `document_type` | enum | e.g. `invoice` \| `report` \| `spreadsheet` \| `letter` \| `other` (finalised with the sample set). |
| `key_entities` | KeyEntity[] | Extracted typed values. |
| `language` | string | Detected (e.g. `en`). |
| `source_filename` | string | Echoed from the job. |
| `page_or_sheet_count` | int | From curated. |
| `confidence` | float [0,1] | Reported indicator; lowered by ungrounded values. |
| `extracted_at` | timestamp | ISO-8601. |
| `ungrounded_fields` | string[] | Always present (empty list when all grounded); lists values not locatable in curated text (flagged). |

### KeyEntity

| Field | Type | Notes |
|-------|------|-------|
| `type` | enum | `org` \| `person` \| `date` \| `amount` \| … |
| `value` | string | The extracted value; expected to appear in curated text. |
| `grounded` | bool | True iff `value` is locatable in curated text. |

## State machine

```text
            upload (raw written, job created)
                       │
                    queued ──enqueue──► processing
                                          │  raw ──parse──► curated ──annotate──► annotated
                                          │     │              │                     │
                                          │   (retry ≤ N per stage; on exhaustion → failed{stage,error})
                                          ▼
                                completed (annotated persisted)   failed (terminal, names stage)
```

- **Forward-only**: `raw → curated → annotated`; `queued → processing → completed|failed`.
- **Idempotent**: redelivery of an already-applied stage is a no-op (guarded write).
- **Replayable**: any stage re-runs from the persisted prior stage (raw is immutable).

## Mapping to storage

| Entity | Store | Key / scope |
|--------|-------|-------------|
| Raw | MinIO | `{tenant_id}/raw/{job_id}/{filename}` |
| Job, Curated, Annotation | Postgres | tables `jobs`, `curated`, `annotated`; `tenant_id` non-null on every row; PK includes `job_id`; every query filters `tenant_id`. |
| Work + events | RabbitMQ | message metadata carries `tenant_id` + `job_id`; DLX after N attempts. |
