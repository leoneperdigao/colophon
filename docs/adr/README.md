# Architecture Decision Records

Lightweight (Nygard-style) records of **execution-time** architecture decisions —
the choices made while building, which aren't captured in the design-time
artifacts. Per the Spec Kit seed (§3), decisions "double as ADR seeds; consider
writing them into `docs/adr/`," and this satisfies Constitution VIII (everything
traceable).

- **Design-time** decisions live in `.specify/memory/constitution.md` and
  `specs/001-document-annotation/research.md` (the Spec Kit decision log).
- **Execution-time** decisions live here.

ADRs are **immutable once Accepted** — to change one, add a new ADR that
**supersedes** it (don't rewrite history). Use [`template.md`](./template.md).

## Index

| # | Title | Status |
|---|-------|--------|
| [0001](./0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](./0002-trunk-based-branching.md) | Trunk-based branching | Accepted |
| [0003](./0003-structured-logging-stdlib-now-otel-later.md) | Structured logging: stdlib now, structlog + OpenTelemetry later | Accepted |
| [0004](./0004-retry-and-dead-lettering-are-broker-native.md) | Retry & dead-lettering are broker-native | Accepted |
| [0005](./0005-untrusted-input-and-prompt-injection-defense.md) | Untrusted-input handling & prompt-injection defense | Accepted |
