# Feature Specification: Document Annotation Service

**Feature Branch**: `001-document-annotation`

**Created**: 2026-06-02

**Status**: Draft

**Input**: Document Annotation Service — accept documents (PDFs and spreadsheets),
extract structured metadata from each using an AI model, and serve the results.
Acceptance and processing are decoupled because processing outlives a request.
(Source: `docs/speckit_seed.md` §2.)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Submit a document and get an immediate job identifier (Priority: P1)

An API consumer acting for a tenant uploads a document and receives a job
identifier right away, while processing continues in the background. The caller
never holds a request open waiting for the AI to finish.

**Why this priority**: This is the accept path and the core promise of the
service — work outlives the request. Without it nothing else exists.

**Independent Test**: Upload a document with a valid tenant credential and
confirm the response returns a job identifier and a "queued"/accepted status
immediately, well within any request timeout, before processing has completed.

**Acceptance Scenarios**:

1. **Given** a valid tenant credential and a supported document, **When** the
   consumer submits the upload, **Then** the service responds immediately with a
   job identifier and an accepted status, and processing proceeds in the
   background.
2. **Given** a missing or invalid credential, **When** the consumer submits an
   upload, **Then** the service rejects the request and no job is created.

---

### User Story 2 - Retrieve structured metadata by job identifier (Priority: P1)

The consumer polls for the result using the job identifier and, once processing
is complete, receives the structured metadata: at minimum a summary, a document
type, key entities, plus supporting fields (language, page/sheet count, source
filename, a confidence indicator, extraction timestamp).

**Why this priority**: This is the query path; together with Story 1 it forms the
minimum viable loop. The result must be grounded in the document, not invented.

**Independent Test**: For a job that has finished processing, fetch it by
identifier and confirm the returned metadata conforms to the agreed contract and
its extracted values are present in the document content.

**Acceptance Scenarios**:

1. **Given** a job that is still processing, **When** the consumer fetches it by
   identifier, **Then** the service returns the current status and stage without
   a final result.
2. **Given** a job that has completed, **When** the consumer fetches it by
   identifier, **Then** the service returns a status of "completed" and metadata
   that conforms to the contract and is grounded in the document.
3. **Given** an unknown job identifier, **When** the consumer fetches it, **Then**
   the service returns "not found".

---

### User Story 3 - Tenant-isolated retrieval (Priority: P2)

Each tenant can retrieve only its own jobs. Another tenant's job identifier is
indistinguishable from one that does not exist.

**Why this priority**: Isolation is the access boundary; a leak here is the most
serious failure the service can have, but it builds on Stories 1–2.

**Independent Test**: Create a job under tenant A, then fetch that identifier
with tenant B's credential and confirm the response is "not found" — not the
record, and not a different error that confirms the job exists.

**Acceptance Scenarios**:

1. **Given** a job created under tenant A, **When** tenant B fetches it by
   identifier, **Then** the service returns "not found".
2. **Given** a job created under tenant A, **When** tenant A fetches it by
   identifier, **Then** the service returns the job.

---

### User Story 4 - Idempotent re-upload (Priority: P2)

Re-uploading identical content for the same tenant returns the same job
identifier and does not reprocess the document.

**Why this priority**: Idempotency protects against duplicate work and cost and
makes retries safe, but it is a refinement of the accept path.

**Independent Test**: Upload the same document twice under one tenant and confirm
both responses carry the same job identifier and the document is processed only
once.

**Acceptance Scenarios**:

1. **Given** a document already submitted by a tenant, **When** the same tenant
   submits identical content again, **Then** the service returns the original job
   identifier and does not start a new processing run.
2. **Given** identical content submitted by two different tenants, **When** each
   submits, **Then** each tenant receives its own distinct job identifier.

---

### User Story 5 - Explicit, staged failure reporting (Priority: P3)

When a document cannot be processed, the result names the stage that failed and
carries an error, rather than silently returning a partial or empty success.

**Why this priority**: "Fails silently" is the named anti-goal; an explicit
failure state makes problems observable. It depends on the staged pipeline.

**Independent Test**: Submit a corrupt or unsupported file and confirm the job
reaches a "failed" state that names the stage at which it failed and includes an
error description.

**Acceptance Scenarios**:

1. **Given** a corrupt or unsupported document, **When** it is processed, **Then**
   the job reaches a "failed" status naming the failing stage and an error, and is
   retrievable in that state.
2. **Given** a transient processing error, **When** the stage is retried up to the
   allowed number of attempts and still fails, **Then** the job is marked failed
   with the stage and error rather than retried indefinitely.

---

### Edge Cases

- **Clean text PDF / multi-page PDF**: both produce grounded metadata with a
  correct page count.
- **Scanned, image-only PDF (no extractable text)**: the service does not invent
  content; it produces a low-confidence or explicit failure outcome rather than a
  fabricated result.
- **Simple spreadsheet / multi-sheet or messy-header spreadsheet**: both yield
  metadata with a correct sheet count; only cell values are used, never formulas.
- **Corrupt or unsupported file**: graceful, explicit failure naming the stage.
- **Duplicate upload**: same tenant → same job identifier, no reprocessing.
- **Document containing embedded "instructions"**: treated as data; it must not
  alter the system's behaviour or change the extraction task.
- **Two different tenants**: complete isolation; one tenant's content never
  appears in another's result.
- **Non-English document (optional)**: language is detected and reported.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The service MUST accept a document upload and return a job
  identifier immediately, before processing completes.
- **FR-002**: The service MUST derive the acting tenant from the caller's
  credential and MUST NOT accept a tenant supplied in the request body or headers.
- **FR-003**: The service MUST reject uploads and retrievals that lack a valid
  credential, without creating or revealing any job.
- **FR-004**: The service MUST process each document asynchronously through
  ordered, persisted stages: preserve the original, extract its content, then
  produce structured metadata.
- **FR-005**: Each stage MUST be independently retryable, and processing MUST be
  replayable from a persisted earlier stage without re-doing successful prior
  stages.
- **FR-006**: Stage transitions MUST move forward only; a completed stage's result
  MUST NOT be overwritten by a later redelivery of the same work.
- **FR-007**: The produced metadata MUST include at minimum a summary, a document
  type, and key entities, plus supporting fields: language, page or sheet count,
  source filename, a confidence indicator, and an extraction timestamp.
- **FR-008**: Extracted values MUST be grounded in the document's content; values
  that cannot be located in the content MUST be flagged and MUST lower the
  reported confidence.
- **FR-009**: The service MUST provide retrieval by job identifier returning the
  current status and stage and, when complete, the metadata.
- **FR-010**: Retrieval MUST be tenant-scoped: a job belonging to another tenant,
  and an unknown job, MUST both return "not found" and be indistinguishable.
- **FR-011**: Re-uploading identical content for the same tenant MUST return the
  same job identifier and MUST NOT reprocess the document.
- **FR-012**: Identical content uploaded by different tenants MUST produce
  distinct, tenant-scoped jobs.
- **FR-013**: A document that cannot be processed MUST result in an explicit
  "failed" status that names the failing stage and includes an error; the service
  MUST NOT return a silent, partial, or empty success.
- **FR-014**: A stage MUST be retried up to a bounded number of attempts; after the
  limit it MUST be isolated as failed rather than retried indefinitely.
- **FR-015**: Uploaded content MUST be treated as untrusted: the service MUST
  validate type and size, bound parsing effort (time and document size/page/sheet
  limits), and MUST use spreadsheet cell values, never evaluate formulas.
- **FR-016**: Document content, including any embedded "instructions", MUST NOT be
  able to change the system's behaviour or the extraction task.
- **FR-017**: One tenant's content MUST NEVER appear in another tenant's result,
  including via shared caches, failure records, or logs.
- **FR-018**: Output quality MUST be measurable against a set of known-correct
  samples, reporting document-type accuracy, key-entity precision and recall, and
  the share of results that conform to the metadata contract, evaluated against
  defined thresholds.

### Key Entities *(include if feature involves data)*

- **Tenant**: A client organisation, established by the caller's credential. Owns
  and scopes every job and result. Never client-supplied.
- **Job**: A unit of work for one uploaded document under one tenant, identified by
  an identifier derived from the tenant and the content (so identical re-uploads
  collide). Carries status (`queued`, `processing`, `completed`, `failed`), the
  current stage, and an error when failed.
- **Raw stage result**: The preserved original upload — immutable, the source of
  truth from which later stages are replayable.
- **Curated stage result**: The document's extracted, normalised content (text and
  structure, detected type, page/sheet count) produced before metadata extraction.
- **Annotated stage result (Annotation)**: The final structured metadata — summary,
  document type, key entities, language, page/sheet count, source filename,
  confidence, extraction timestamp. The retrievable result.
- **Key Entity**: A typed value extracted from the document (e.g. organisation,
  person, date, amount), each expected to be grounded in the curated content.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of uploads with a valid credential receive a job identifier
  before processing completes, well within a normal request timeout.
- **SC-002**: Documents whose processing takes longer than a single request can
  wait still complete and are retrievable by identifier 100% of the time.
- **SC-003**: Document-type classification is correct on at least 90% of the
  known-correct sample set.
- **SC-004**: Key-entity extraction achieves at least 0.80 precision and 0.80
  recall against the known-correct sample set.
- **SC-005**: 100% of served annotations conform to the agreed metadata contract
  (all required fields present and well-typed).
- **SC-006**: At least 95% of extracted values are grounded in the document
  content; every ungrounded value is flagged and lowers reported confidence.
- **SC-007**: Cross-tenant retrieval returns "not found" 100% of the time; no
  test or audit reveals one tenant's content in another tenant's result.
- **SC-008**: Re-uploading identical content for the same tenant returns the same
  identifier and triggers no reprocessing 100% of the time.
- **SC-009**: 100% of documents that cannot be processed end in a "failed" state
  that names the failing stage; none end in a silent or partial success.

## Assumptions

- A small, fixed set of tenants and credentials is sufficient for this slice;
  full identity/login is out of scope (a credential maps to a tenant).
- Supported input types are PDFs and spreadsheets; other types fail gracefully and
  explicitly at validation/parse.
- The known-correct sample set is self-generated from known ground truth, so the
  expected document type and key entities are available for measuring quality.
- The thresholds in Success Criteria are starting targets for this slice and may
  be tuned once the sample set is finalised.
- "Immediately" for acknowledgement means fast enough to never approach a request
  timeout (sub-second in normal operation), not a hard real-time guarantee.
- Confidence is a reported indicator to surface low-confidence/ungrounded results
  for review; it is not a calibrated probability.

## Out of Scope

- A user interface.
- An end-user login or identity product (sign-up, password reset, an identity
  provider). A credential-to-tenant mapping is the whole access surface here.
- Model training or fine-tuning.
- Cross-document or multi-document reasoning; each document is annotated on its own.
