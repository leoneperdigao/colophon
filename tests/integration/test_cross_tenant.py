"""Cross-tenant isolation — app wired to fakes, no infra. T027 (US3).

Acceptance/regression guard for the tenancy boundary established in US1/US2:
another tenant's job id must be indistinguishable from an unknown one.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.adapters.inbound.http.app import create_app
from app.config.container import Container

PDF = ("f.pdf", b"hello world", "application/pdf")
A = {"Authorization": "Bearer tokenA"}
B = {"Authorization": "Bearer tokenB"}


def _client() -> TestClient:
    container = Container.in_memory(token_map={"tokenA": "tenant-a", "tokenB": "tenant-b"})
    return TestClient(create_app(container))


def test_other_tenant_gets_404_owner_gets_200() -> None:
    client = _client()
    job_id = client.post("/documents", headers=A, files={"file": PDF}).json()["job_id"]
    # Tenant B must not be able to tell the job exists.
    assert client.get(f"/annotations/{job_id}", headers=B).status_code == 404
    # Tenant A (the owner) can.
    assert client.get(f"/annotations/{job_id}", headers=A).status_code == 200
