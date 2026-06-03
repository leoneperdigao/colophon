# 0001. Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-06-03

## Context

The Spec Kit seed (§3) notes that the resolved decisions "double as ADR seeds;
consider writing them into `docs/adr/`." Design-time decisions are already
captured in the constitution and `specs/001-document-annotation/research.md`. But
decisions made **during execution** (branching model, logging approach, retry/DLQ
placement, input-security posture) had been landing as ad-hoc `docs/*.md` files
and PR descriptions — not a durable, discoverable trail. Constitution VIII
requires decisions to be traceable.

## Decision

Adopt lightweight, Nygard-style **ADRs** in `docs/adr/`, numbered sequentially
and indexed in `README.md`. ADRs capture **execution-time** architecture
decisions; design-time decisions stay in the constitution / `research.md`. An ADR
is **immutable once Accepted** — to change a decision, add a new ADR that
supersedes the old one.

## Consequences

- A single, auditable decision trail; reviewers can see *why*, not just *what*.
- Small per-decision overhead (one short file).
- Two homes for decisions (constitution/research vs ADRs) — mitigated by stating
  the split here and in the index.

## Alternatives considered

- **Decisions in PR descriptions only** — not durable or discoverable after merge.
- **Everything in `research.md`** — mixes settled design-time decisions with
  evolving execution-time ones; harder to evolve/supersede cleanly.
