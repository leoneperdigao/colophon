"""Idempotency: deterministic, tenant-scoped job_id. T007."""

import hashlib


from app.domain.identity import compute_job_id


def test_job_id_is_deterministic_hex_sha256() -> None:
    a = compute_job_id("t1", b"hello", "f.pdf")
    b = compute_job_id("t1", b"hello", "f.pdf")
    assert a == b
    assert len(a) == 64
    assert all(c in "0123456789abcdef" for c in a)


def test_job_id_matches_canonical_nul_delimited_sha256() -> None:
    # tenant_id || 0x00 || filename || 0x00 || content-bytes, lowercase hex.
    expected = hashlib.sha256(b"t1\x00f.pdf\x00hello").hexdigest()
    assert compute_job_id("t1", b"hello", "f.pdf") == expected


def test_job_id_is_tenant_scoped() -> None:
    assert compute_job_id("t1", b"hello", "f.pdf") != compute_job_id("t2", b"hello", "f.pdf")


def test_job_id_varies_with_content_and_filename() -> None:
    base = compute_job_id("t1", b"hello", "f.pdf")
    assert base != compute_job_id("t1", b"world", "f.pdf")
    assert base != compute_job_id("t1", b"hello", "g.pdf")


def test_nul_delimiter_prevents_field_boundary_collision() -> None:
    # Without domain separation, ("ab","c") and ("a","bc") could collide.
    assert compute_job_id("ab", b"x", "c.pdf") != compute_job_id("a", b"x", "bc.pdf")
