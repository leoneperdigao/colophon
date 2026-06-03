# 0012. Multi-client customization & extension model

- **Status:** Accepted
- **Date:** 2026-06-03

## Context

The product is a **core** annotation service used by multiple client tenants, but
real deployments need **per-client variation**: which document types matter, the
extraction **schema/fields** per type, prompt/model variants, validation
thresholds, output shaping, and occasionally a client-specific parser or
post-processor. Some extensions are shared by all clients; some belong to one.

This is fundamentally a **configuration & extensibility** problem, and it
intersects two existing decisions: tenancy isolation (ADR-0008, pooled vs siloed)
and the cloud-deploy model (ADR-0006, ports make the target a deploy-time choice).
Two common answers are floated in practice:

- **Plugin architecture** — load client/extension code at runtime (entry-points).
- **Build + deploy config** — per-client images/deployments bundling extensions.

Both are valid; neither is free.

## Decision

**Config-driven extension, chosen by the principle of least power.** Treat each
variation point as a **strategy behind a port/registry**, selected by **per-tenant
configuration** resolved at the composition root:

- A shared **core** set of document types + extraction schemas/prompts/thresholds.
- **Per-tenant config** (feature flags + overrides/additions) that selects or
  extends the core — e.g. tenant *X* adds a `claim_form` type with its own schema
  and prompt; tenant *Y* raises the confidence threshold; tenant *Z* turns a type
  off. This is **data, not code**.
- The annotation agent's existing **classify → type-specific extraction schema**
  step is the natural seam: the `(tenant, document_type) → schema/prompt` mapping
  is configuration looked up at the composition root and handed to the agent.
- Tenant config is itself **tenant-isolated** — one client's config/prompts can
  never affect another's processing or output (a leak surface from ADR-0005/0008).

### Escalation path (least power first; escalate only when forced)

1. **Config flags / values** — per-tenant settings; the default, covers most needs.
2. **In-tree strategy registry** — register additional adapters/schemas/strategies
   in the codebase, enabled per tenant. One deployment, all code reviewed.
3. **Plugin entry-points** — out-of-tree / third-party code loaded at runtime.
   Only when a client needs genuinely custom logic. **Heavy and risky**: plugin
   versioning, **sandboxing**, supply-chain exposure, and tenant-isolation of
   executing code (running client code is a large attack surface). Reserve, and
   isolate.
4. **Per-client build / deploy (silo)** — a separate image/deployment bundling a
   client's extensions; reserve for governance-heavy or deeply-customised clients
   (the silo tier of ADR-0008). Cost: N pipelines/images to maintain.

## Consequences

- Most per-client needs are met with **no code-loading and no extra deployments** —
  the safest and cheapest option, and a strong fit for an early multi-client
  product.
- The hexagonal ports + composition root already provide the seam: an "extension"
  is *registering a strategy and toggling it per tenant*, not a new architecture.
- **Security:** the default avoids running client-supplied code entirely. When
  plugins become unavoidable, they are sandboxed and tenant-isolated, and treated
  as untrusted supply chain.
- Per-client builds/silos remain available for the rare deeply-custom or
  governance case, consistent with ADR-0006 (deploy-time) and ADR-0008 (silo).
- For this take-home scope, the seam is **designed and documented**; a minimal
  per-tenant document-type/schema registry is a small, additive change behind the
  agent when a second client's needs make it concrete.

## Alternatives considered

- **Plugin-first (runtime client code) as the default** — powerful but
  over-engineered for the common case and a real security liability; rejected as
  the default, kept as a sandboxed escalation.
- **Per-client build/deploy as the default** — N deployments for what is usually a
  config difference; reserves a heavy tool for a light job; rejected as the
  default, kept for the silo tier.
- **One hardcoded behaviour for all clients** — cannot serve a real multi-client
  product; rejected.
