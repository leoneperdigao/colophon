# 0004. Retry & dead-lettering are broker-native

- **Status:** Accepted
- **Date:** 2026-06-03

## Context

The spec requires **per-stage retry** and **dead-lettering after N attempts**, with
a `failed` state naming the stage. True retry/DLQ depends on **message redelivery**,
which is a property of the broker. The walking skeleton's in-memory `Messaging`
adapter drains the queue once, synchronously — it has no redelivery.

## Decision

Implement retry and dead-lettering with **RabbitMQ DLX + redelivery** in the
messaging adapter (Phase 8), **not** faked on the in-memory queue. The explicit
**`failed{stage}`** state for unprocessable documents is built now (it doesn't
need a broker). Correctness under at-least-once delivery rests on the pipeline's
**idempotency on redelivery**, which is already implemented and tested
(redelivering a completed/failed job is a no-op; forward-only stage writes).

## Consequences

- No artificial retry/DLQ simulation on a fake (avoids misleading, untestable
  machinery — Constitution VI, simplicity).
- Real retry/DLQ semantics arrive with the real broker, where they're native.
- Until Phase 8, the local in-memory profile has no automatic retry (documented).

## Alternatives considered

- **Simulate retry/DLQ on the in-memory queue** — elaborate fake of a broker
  feature; brittle and not representative of production behaviour.
