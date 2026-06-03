"""End-to-end smoke test against a running stack (the Definition of Done).

Exercises the real path through the compose services: upload under two distinct
tenants (a real PDF and a real spreadsheet) -> 202 + job_id -> background worker
runs raw->curated->annotated -> poll -> a valid annotation; then proves tenant
isolation (tenant B cannot read tenant A's job: 404, not the record).

Run against `make up`:  uv run python scripts/smoke.py
Env: BASE_URL (default http://localhost:8000), TENANT_TOKENS (token:tenant,...).
"""

from __future__ import annotations

import os
import sys
import time

import httpx

from app.adapters.parsing.content_types import PDF, XLSX
from samples.generate import GoldSample, build_gold_set

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
POLL_TIMEOUT_S = float(os.getenv("SMOKE_TIMEOUT", "60"))


def _tokens() -> tuple[str, str]:
    """Two distinct tenant tokens from TENANT_TOKENS (falls back to the .env.example pair)."""
    raw = os.getenv("TENANT_TOKENS", "tokenA:tenant-a,tokenB:tenant-b")
    toks = [p.split(":", 1)[0].strip() for p in raw.split(",") if ":" in p]
    if len(toks) < 2:
        sys.exit("smoke: need at least two tenant tokens in TENANT_TOKENS")
    return toks[0], toks[1]


def _sample(content_type: str) -> GoldSample:
    return next(s for s in build_gold_set() if s.content_type == content_type)


def _upload(client: httpx.Client, token: str, sample: GoldSample) -> str:
    resp = client.post(
        "/documents",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (sample.filename, sample.content, sample.content_type)},
    )
    assert resp.status_code == 202, f"upload: {resp.status_code} {resp.text}"
    return str(resp.json()["job_id"])


def _poll(client: httpx.Client, token: str, job_id: str) -> dict[str, object]:
    deadline = time.monotonic() + POLL_TIMEOUT_S
    while time.monotonic() < deadline:
        resp = client.get(f"/annotations/{job_id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, f"poll: {resp.status_code} {resp.text}"
        body: dict[str, object] = resp.json()
        if body["status"] in ("completed", "failed"):
            return body
        time.sleep(1)
    sys.exit(f"smoke: job {job_id} did not finish within {POLL_TIMEOUT_S}s")


def _assert_annotated(label: str, body: dict[str, object]) -> None:
    if body["status"] != "completed":
        sys.exit(f"smoke: {label} ended {body['status']} (error={body.get('error')})")
    result = body["result"]
    assert isinstance(result, dict), f"{label}: missing result"
    for field in ("summary", "document_type", "key_entities", "language"):
        assert field in result, f"{label}: annotation missing {field!r}"
    print(
        f"  ✓ {label}: completed — type={result['document_type']!r}, "
        f"{len(result['key_entities'])} entities"
    )


def main() -> None:
    token_a, token_b = _tokens()
    with httpx.Client(base_url=BASE_URL, timeout=10) as client:
        print(f"smoke: target {BASE_URL}")
        pdf_job = _upload(client, token_a, _sample(PDF))
        xlsx_job = _upload(client, token_b, _sample(XLSX))
        print(f"  ✓ uploaded: tenant-A pdf={pdf_job[:12]}…  tenant-B xlsx={xlsx_job[:12]}…")

        _assert_annotated("tenant-A PDF", _poll(client, token_a, pdf_job))
        _assert_annotated("tenant-B XLSX", _poll(client, token_b, xlsx_job))

        # Tenant isolation: B must not see A's job — 404, never the record.
        cross = client.get(
            f"/annotations/{pdf_job}", headers={"Authorization": f"Bearer {token_b}"}
        )
        assert cross.status_code == 404, f"cross-tenant leak: {cross.status_code} {cross.text}"
        print("  ✓ cross-tenant read of A's job by B -> 404")
    print("smoke: PASS")


if __name__ == "__main__":
    main()
