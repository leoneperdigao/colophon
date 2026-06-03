# 0011. File-size handling & scaling

- **Status:** Accepted
- **Date:** 2026-06-03

## Context

Uploaded documents range from a few KB to several MB (our robustness corpus
includes a ~5 MB multi-page PDF). Unbounded uploads are a memory / cost / DoS
risk, but the service must also have a credible path to larger files without a
rewrite. We need a *good-enough* capability for this scope and a recorded scaling
decision.

## Decision

**Good-enough for this scope (built):**

- **Per-upload size cap** — `MAX_UPLOAD_BYTES`, default **10 MiB**, env-tunable per
  deployment. Comfortably covers real PDFs/spreadsheets here.
- **Bounded read** — the API reads at most `cap + 1` bytes and returns **413** if
  exceeded, so it **never buffers more than the cap** regardless of the client.
- **Parse-side bounds** — page / sheet / cell caps + a wall-clock parse timeout
  bound *work*, independent of byte size (a 5 MB image-only PDF has little text).
- **Storage split** — the raw bytes live in blob storage (MinIO/S3); only curated
  text + the annotation live in Postgres. **LLM cost scales with extracted text
  length, not file size**, so a large image PDF is cheap to annotate.

**Documented — the scaling path (not built):**

- **Content-Length fast-reject** — reject oversized uploads from the
  `Content-Length` header *before* reading the body (the bounded read stays as the
  authoritative guard, since the header can be absent/spoofed).
- **Stream upload → blob** — stream the request body straight to S3 (multipart)
  instead of buffering; the worker streams from blob during parse. Upload size is
  then decoupled from API memory.
- **Presigned direct-to-S3 upload** — for large files, the API issues a presigned
  URL and creates the job; the client uploads bytes directly to S3 and the API
  never handles them. This is also required to sidestep **API Gateway / Lambda
  payload limits** (≈6 MB sync, 10 MB API GW) in the serverless target.
- **Streaming parse** — pypdf per-page and openpyxl `read_only` already stream;
  keep memory bounded for large *valid* files; OCR for scanned PDFs is a separate,
  heavier worker path.
- **Per-tenant quotas & tiers** — size limits and storage/processing quotas per
  tenant (cost + noisy-neighbour control), per ADR-0008.
- **Very large docs** — chunk or split via Step Functions on serverless (Lambda's
  15-min ceiling), per the migration mapping.

## Consequences

- Memory, cost, and abuse are bounded today with a few cheap controls; the cap is
  tunable without code changes.
- The path to large-file ingestion is a known adapter/wiring change (stream or
  presigned-to-blob), not a redesign — consistent with the hexagonal seams.
- Until streaming/presigned upload is built, the hard ceiling on a single document
  is `MAX_UPLOAD_BYTES`.

## Alternatives considered

- **No cap / buffer whole file** — memory-exhaustion DoS; rejected.
- **Stream-to-blob / presigned now** — the right production answer, but more than
  this scope needs for ≤10 MB documents; documented and deferred.
