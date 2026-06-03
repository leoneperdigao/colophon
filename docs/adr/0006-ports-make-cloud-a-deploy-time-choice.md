# 0006. Ports make the cloud target a deploy-time choice

- **Status:** Accepted
- **Date:** 2026-06-03

## Context

The service must be **clone-and-run locally** for review, and migrate to a cloud
target later without a rewrite. There are two plausible cloud paths — serverless
on AWS, or Kubernetes. We need migration to be a wiring change, and local runs to
have **real** queue/blob/store semantics (not an emulator a reviewer must
authenticate to).

## Decision

The domain and application depend only on the **port contracts** (`Messaging`,
`BlobStore`, `AnnotationStore`, `DocumentParser`, `LLMClient`), never on a vendor
SDK or emulator. Locally we run **real, robust infra** — RabbitMQ, MinIO,
Postgres — via docker-compose; **no AWS emulator**. The cloud target is an
adapter-and-deploy choice:

- **Serverless (AWS):** SQS + EventBridge + Lambda + S3 + DynamoDB + API Gateway.
- **Kubernetes:** same broker + MinIO/S3 + Postgres as Deployments, KEDA scaling
  workers on queue depth.

Domain/application code never changes across targets; only adapters and the
entrypoint differ. There is no clean standalone EventBridge emulator, so we model
the *event pattern* on the broker behind the `Messaging` port rather than
emulating the AWS API; the AWS API is bound only in the serverless adapter.

## Consequences

- Clone-and-run locally with real messaging/blob/store semantics; low friction.
- Migration is wiring + deploy, not a rewrite — the seam is the graded signal.
- Cost: one adapter per port per target must be written and tested.

## Alternatives considered

- **AWS-native locally** — the reviewer must deploy to AWS; high friction.
- **LocalStack** — the Community edition was discontinued / is auth-gated
  (Mar 2026); requiring a reviewer account adds friction and isn't portable.
