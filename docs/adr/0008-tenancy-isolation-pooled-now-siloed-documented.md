# 0008. Tenancy isolation: pooled now, siloed documented

- **Status:** Accepted
- **Date:** 2026-06-03

## Context

The service is multi-tenant, and **isolation is the security boundary**. The brief
asks for neither auth nor tenancy, but a client-supplied tenant header with no
auth is honor-system isolation a reviewer flags immediately. Threading `tenant_id`
from line one is cheap; retrofitting it is not. Auth, authorization, and tenancy
are **one boundary**: the credential establishes the principal, the principal
carries the tenant, the tenant scopes everything.

## Decision

Build the **pooled** model now:

- **Tenant derived from the credential**, never a client-supplied field (closes
  the spoofing / injection-driven tenant-flip hole).
- `tenant_id` threaded through the domain, blob keys, store rows, message
  metadata, and logs; **tenant-scoped reads** — another tenant's `job_id` returns
  **404**, with a cross-tenant lookup test.
- Optional Postgres **row-level security** keyed on `tenant_id` as an enforced
  control (build if time).

**Document** the production isolation model: pooled (RLS + per-tenant scoped
credentials + per-tenant index) by default; **siloed** (separate
account/workspace/DB) for governance-heavy clients — most start pooled and silo on
demand. AI-layer isolation: shared store/cache/context are tenant-scoped so one
tenant's content never enters another's prompt. Close the **leak surfaces**:
caches keyed without tenant, the DLQ, and logs (all can carry another tenant's
content); per-tenant KMS keys and quotas (noisy-neighbour).

## Consequences

- A real isolation story at the cheap end, with a credible scale path.
- Threading tenant from the first line avoids an expensive retrofit.
- Full enforcement (RLS everywhere, silo deployment, per-tenant KMS) is deferred —
  documented, not built.

## Alternatives considered

- **Client-supplied tenant header, no auth** — spoofable honor-system isolation; a
  reviewer flags it immediately.
- **Full isolation enforcement + silo deployment now** — out of scope for the
  8-hour box; documented as the production posture.
