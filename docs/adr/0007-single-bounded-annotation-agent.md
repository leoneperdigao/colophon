# 0007. Single bounded annotation agent, not multi-agent

- **Status:** Accepted
- **Date:** 2026-06-03

## Context

The brief says an "AI agent" processes the document. That phrasing invites an
agent framework or a multi-agent system. But annotation here is a **bounded,
deterministic extraction task**, and the design is graded on judgment —
specifically, knowing *when not* to reach for an agent.

## Decision

The annotate stage is **one bounded unit**, not a society of agents:

1. **classify** the document type →
2. route to a **type-specific extraction schema** (an invoice's fields differ
   from a report's) →
3. **extract** via Anthropic **tool-use** (strict JSON schema) →
4. **validate/repair** against the schema.

It has **no autonomy, no tools with side effects, and no multi-agent
orchestration**. This is also the strongest prompt-injection defense (ADR-0005):
with no ambient authority, injected instructions cannot make it *act*.

## Consequences

- Simple, deterministic, and fully testable against a fake LLM transport.
- Injection-safe by construction; output constrained to a validated schema.
- **Documented evolution path** (not built): if the task grows to mixed-modality
  or open-ended understanding (OCR, table extraction, cross-document reasoning),
  the stage becomes a single tool-using (ReAct-style) agent; an orchestrator-worker
  split only if genuinely parallel specialized subtasks emerge. The `LLMClient`
  port + staged pipeline make that a swap, not a rewrite.

## Alternatives considered

- **Multi-agent orchestration** — over-engineering for a bounded task; fails the
  "when not to reach for an agent" test; contradicts the simplicity principle.
- **Single opaque prompt** — loses per-type schemas and the validate/repair step.
