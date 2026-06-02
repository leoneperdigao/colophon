<!--
SYNC IMPACT REPORT
==================
Version change: (template) → 1.0.0
Bump rationale: Initial ratification of the project constitution (MAJOR baseline).

Principles defined (8):
  I.   Hexagonal, Light
  II.  Scope Discipline
  III. Runnable Locally Is the Deliverable
  IV.  Security by Default
  V.   Tenancy Is an Access Boundary
  VI.  Simplicity over Cleverness
  VII. Test-First (NON-NEGOTIABLE)
  VIII.Everything Traceable

Sections:
  Added: "Locked Stack & Architecture Constraints" (technology + port constraints)
  Added: "Development Workflow & Quality Gates" (two-framework flow, branching, eval gate)
  Added: "Governance"

Templates / artifacts reviewed:
  ✅ .specify/templates/plan-template.md  — generic "Constitution Check" gate; fills at plan time, no edit needed
  ✅ .specify/templates/spec-template.md  — no hardcoded principle references, no edit needed
  ✅ .specify/templates/tasks-template.md — no hardcoded principle references, no edit needed
  ✅ CLAUDE.md                            — already aligned (stack, scope, tenancy, TDD, out-of-scope)
  ✅ docs/BRANCHING.md                    — already aligned (trunk-based, traceability)

Deferred TODOs: none.
-->

# Document Annotation Service Constitution

This constitution governs an **8-hour take-home**: an event-driven document
annotation service. It encodes the non-negotiable principles that keep the build
clean, runnable, and well-scoped. **The design is resolved** (see `PLAN.md`);
this document is the rule of law for *how* it is built, not an invitation to
re-open *what* is built. Where a tool, skill, or contributor conflicts with a
principle here, the constitution wins.

## Core Principles

### I. Hexagonal, Light

Domain and application logic MUST depend only on ports. Ports exist ONLY where a
real second implementation does: `BlobStore`, `Messaging`, `AnnotationStore`,
`DocumentParser`, `LLMClient`. New ports MUST NOT be introduced for layering's
own sake. Adapters depend inward on ports; the domain core never imports an
adapter, a framework type, or an SDK. A composition root wires adapters by
environment.

*Rationale:* clean seams are the graded signal and the migration story; ports
where substitution is real keep the seams honest and the core portable.

### II. Scope Discipline

Every advanced element follows one rule: **design it in, document it, implement
only the minimal seam.** The must-build slice MUST be complete before any
deferred item is started. Items on the out-of-scope list (see `PLAN.md` §13 /
`CLAUDE.md`) MUST NOT be built; if one appears necessary, STOP and ask rather
than building it. Restraint is a deliberate quality signal, not a gap.

*Rationale:* a small correct system scores higher than a sprawling half-built
one; grading rewards tradeoffs made under time pressure.

### III. Runnable Locally Is the Deliverable

The system MUST be clone-and-run via `docker-compose up` at every slice. The
cloud target is an adapter-and-deploy choice, documented but not built. Code
MUST depend on contracts, never on a vendor SDK or a cloud emulator in the
domain/application layers. If an infra adapter fights the environment, fall back
to the in-memory fake behind the same port, keep the system running, and record
the gap — do not let a wedged dependency burn the clock.

*Rationale:* reviewers run it locally; portability behind ports is the whole
point of the hexagonal choice.

### IV. Security by Default

Secrets MUST NEVER be committed: `.env.example` is committed, real `.env` is
gitignored, and LLM provider keys live only in the gateway, never in app code or
images. Each component MUST hold its own least-privilege credentials. All
uploaded content is untrusted: enforce size and content-type validation, parse
timeouts, and page/sheet caps; extract spreadsheet **values, never formulas**.
The annotation step MUST have no tools and no side effects (no ambient
authority), so an injection cannot make it act. Containers run non-root.

*Rationale:* document content is an injection and resource-exhaustion vector; the
cheap controls are high-signal and the reviewer is a security architect.

### V. Tenancy Is an Access Boundary

`tenant_id` MUST be derived from the authenticated credential and MUST NEVER be
read from a client-supplied field. It MUST be threaded through the domain, blob
keys, store rows, message metadata, and logs. Every read and write MUST be
tenant-scoped; another tenant's `job_id` MUST return **404**, never the record.
A cross-tenant lookup test MUST exist and pass.

*Rationale:* a header-supplied tenant with no auth is honor-system isolation;
binding tenant to the credential closes the spoofing hole and makes the isolation
story real.

### VI. Simplicity over Cleverness

A bounded task is a pipeline, not an autonomous agent. The annotation step is a
**single bounded unit** — classify → type-specific structured extraction
(tool-use) → validate/repair — with no autonomy, no tools with side effects, and
**no multi-agent orchestration**. The agentic evolution path is documented, not
built.

*Rationale:* multi-agent here fails the "when not to reach for an agent" test and
reads as over-engineering under time pressure.

### VII. Test-First (NON-NEGOTIABLE)

TDD is mandatory: write the port test against fakes first (RED), implement
(GREEN), then refactor. The domain and application layers MUST be fully testable
with **no infra running**. Output quality MUST be measured by a gold-set eval
with thresholds (`make eval`) plus a deterministic groundedness check — not by
inspection. A commit MUST NOT be pushed on red.

*Rationale:* "fails silently" is the named failure mode; fakes keep the core fast
and deterministic, and the gold-set turns quality into a gate instead of vibes.

### VIII. Everything Traceable

Spec, decisions, plan, and tasks MUST be committed and versioned. Spec Kit
authors the artifacts (`constitution.md`, `spec.md`, `plan.md`, `tasks.md`);
implementation executes against them and regenerates none of the design.
Settled decisions live in the artifacts and are not re-litigated mid-build.

*Rationale:* one source of truth prevents the two frameworks from fighting and
keeps the reasoning auditable.

## Locked Stack & Architecture Constraints

The stack is fixed; substitutions require explicit approval:

- **Runtime:** Python 3.12 · FastAPI · pytest · docker-compose (api + worker +
  rabbitmq + minio + postgres).
- **Ports → local adapters:** `Messaging` → RabbitMQ (queue = work, topic
  exchange = events, DLX = dead-letter); `BlobStore` → MinIO (S3 API,
  tenant-prefixed keys); `AnnotationStore` → Postgres (`tenant_id` on rows);
  `LLMClient` → LiteLLM → Anthropic (tool-use for strict JSON, Haiku-tier model,
  model id + key in env); `DocumentParser` → PDF + spreadsheet adapters.
- **Data stages:** raw (immutable, blob) → curated (parsed, persisted) →
  annotated (final metadata). State machine `queued → processing(raw → curated →
  annotated) → completed | failed`, **forward-only** transitions.
- **Idempotency:** `job_id = hash(tenant + content + filename)`; re-upload returns
  the same job and is not reprocessed.
- **Failure handling:** per-stage retry, DLQ after N attempts, a `failed` state
  naming the stage and error; any stage replayable from the persisted prior
  stage.

## Development Workflow & Quality Gates

- **Two frameworks, distinct roles.** Spec Kit *authors* (`/speckit-constitution`
  → `/speckit-specify` → `/speckit-clarify` → `/speckit-plan` → `/speckit-tasks`,
  must-build slice only; **do NOT run `/speckit-implement`**). Superpowers
  *executes* against the committed artifacts with TDD and subagents. They MUST
  NOT both drive implementation.
- **Vertical slices, not horizontal layers.** First slice end-to-end and running
  (upload → 202 + job_id → enqueue → stub worker → fetch), then thicken in place.
- **Parallelize only along ports.** Parsing, LLM, blob, and store adapters are
  independent given fixed port interfaces — one subagent each is safe. The domain
  core and composition root stay sequential and coherent; never parallelize them.
- **Branching.** Trunk-based per `docs/BRANCHING.md`: protected `main`; Spec Kit
  cuts the `NNN-*` feature branch; short-lived `feat/NNN-<slice>` branches per
  slice or port; Conventional Commits; small green commits; PRs to integrate.
- **Definition of done.** `docker-compose up`; upload a PDF and a spreadsheet
  under two tenants; poll; valid annotation; cross-tenant lookup → 404;
  `make eval` passes thresholds; unit + e2e tests green; README covers `PLAN.md`
  §14 including deferred items as "documented, not built."

## Governance

This constitution supersedes other practices for this project. When guidance
conflicts, the constitution prevails; `PLAN.md` is the decision of record for
resolved design questions.

- **Amendments** require a committed change to this file with an updated Sync
  Impact Report and a version bump. Dependent templates and guidance files
  (`plan-template.md`, `spec-template.md`, `tasks-template.md`, `CLAUDE.md`,
  `docs/BRANCHING.md`) MUST be reviewed for alignment in the same change.
- **Versioning policy (semantic):** MAJOR = backward-incompatible governance or
  principle removal/redefinition; MINOR = a new principle/section or materially
  expanded guidance; PATCH = clarifications and non-semantic refinements.
- **Compliance.** Every plan and PR MUST satisfy the plan template's Constitution
  Check. Any deviation MUST be justified in the plan's Complexity Tracking or
  rejected. Use `CLAUDE.md` for day-to-day runtime guidance; it MUST stay
  consistent with this constitution.

**Version**: 1.0.0 | **Ratified**: 2026-06-02 | **Last Amended**: 2026-06-02
