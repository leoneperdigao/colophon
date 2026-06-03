"""Render a live annotation result as a styled HTML report (for a screenshot).

Uploads a real PDF (tenant A) and spreadsheet (tenant B) to a running stack,
polls each to completion, and writes a self-contained HTML report to
docs/assets/report.html. `scripts/make_media.sh` then screenshots it with headless
Chrome into docs/assets/report.png for the README.

Run against a live stack:  uv run python scripts/render_report.py
"""

from __future__ import annotations

import html
import os
import time
from pathlib import Path
from typing import Any

import httpx

from app.adapters.parsing.content_types import PDF, XLSX
from samples.generate import GoldSample, build_gold_set

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
OUT = Path(os.getenv("REPORT_HTML", "docs/assets/report.html"))
_TOKENS = {
    "tenant-a": os.getenv("DEMO_TOKEN_A", "tokenA"),
    "tenant-b": os.getenv("DEMO_TOKEN_B", "tokenB"),
}


def _sample(content_type: str) -> GoldSample:
    return next(s for s in build_gold_set() if s.content_type == content_type)


def _run(client: httpx.Client, token: str, sample: GoldSample) -> dict[str, Any]:
    job_id = client.post(
        "/documents",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (sample.filename, sample.content, sample.content_type)},
    ).json()["job_id"]
    for _ in range(60):
        body: dict[str, Any] = client.get(
            f"/annotations/{job_id}", headers={"Authorization": f"Bearer {token}"}
        ).json()
        if body["status"] in ("completed", "failed"):
            return body
        time.sleep(1)
    raise SystemExit(f"render_report: job {job_id} did not finish")


def _entities_rows(entities: list[dict[str, Any]]) -> str:
    if not entities:
        return '<tr><td colspan="3" class="muted">— none —</td></tr>'
    cells = []
    for entity in entities:
        grounded = entity.get("grounded", False)
        badge = (
            '<span class="badge ok">grounded</span>'
            if grounded
            else '<span class="badge warn">ungrounded</span>'
        )
        cells.append(
            f"<tr><td>{html.escape(str(entity.get('type', '')))}</td>"
            f"<td>{html.escape(str(entity.get('value', '')))}</td><td>{badge}</td></tr>"
        )
    return "\n".join(cells)


def _card(tenant: str, filename: str, body: dict[str, Any]) -> str:
    result = body.get("result") or {}
    status = html.escape(str(body.get("status", "")))
    entities = result.get("key_entities", [])
    confidence = result.get("confidence", "—")
    return f"""
    <section class="card">
      <header>
        <div class="doc">{html.escape(filename)}</div>
        <div class="tags">
          <span class="tag tenant">{html.escape(tenant)}</span>
          <span class="tag status">{status}</span>
          <span class="tag type">{html.escape(str(result.get("document_type", "—")))}</span>
        </div>
      </header>
      <dl class="meta">
        <div><dt>language</dt><dd>{html.escape(str(result.get("language", "—")))}</dd></div>
        <div><dt>pages / sheets</dt><dd>{html.escape(str(result.get("page_or_sheet_count", "—")))}</dd></div>
        <div><dt>confidence</dt><dd>{html.escape(str(confidence))}</dd></div>
        <div><dt>job_id</dt><dd class="mono">{html.escape(str(body.get("job_id", ""))[:20])}…</dd></div>
      </dl>
      <p class="summary">{html.escape(str(result.get("summary", "")))}</p>
      <table>
        <thead><tr><th>entity</th><th>value</th><th>groundedness</th></tr></thead>
        <tbody>{_entities_rows(entities)}</tbody>
      </table>
    </section>"""


_STYLE = """
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 40px; background: #f7f9fc; font-family: -apple-system,
    Segoe UI, Roboto, Helvetica, Arial, sans-serif; color: #0b2540; }
  h1 { font-size: 24px; margin: 0 0 4px; }
  .sub { color: #5b6b7b; font-size: 14px; margin: 0 0 28px; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
  .card { background: #fff; border: 1px solid #e3e9f2; border-radius: 14px;
    padding: 22px 24px; box-shadow: 0 1px 3px rgba(16,40,80,.06); }
  .card header { display: flex; justify-content: space-between; align-items: center;
    gap: 12px; border-bottom: 1px solid #eef2f8; padding-bottom: 14px; margin-bottom: 14px; }
  .doc { font-weight: 700; font-size: 16px; }
  .tags { display: flex; gap: 6px; flex-wrap: wrap; }
  .tag { font-size: 11px; padding: 3px 9px; border-radius: 999px; font-weight: 600; }
  .tenant { background: #e7f0fb; color: #0b4a82; }
  .status { background: #e6f7ee; color: #18794e; }
  .type { background: #eef0f3; color: #44515f; }
  .meta { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 18px; margin: 0 0 14px; }
  .meta div { display: flex; justify-content: space-between; border-bottom: 1px dotted #eef2f8;
    padding-bottom: 4px; }
  dt { color: #6a7a8a; font-size: 12px; } dd { margin: 0; font-size: 12px; font-weight: 600; }
  .mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-weight: 500; }
  .summary { background: #f8fafd; border-left: 3px solid #1168bd; padding: 10px 14px;
    border-radius: 6px; font-size: 13px; line-height: 1.5; color: #2a3a4a; }
  table { width: 100%; border-collapse: collapse; margin-top: 14px; font-size: 12.5px; }
  th { text-align: left; color: #6a7a8a; font-weight: 600; border-bottom: 2px solid #eef2f8;
    padding: 6px 8px; }
  td { padding: 6px 8px; border-bottom: 1px solid #f2f5fa; }
  .muted { color: #9aa7b4; text-align: center; }
  .badge { font-size: 10.5px; padding: 2px 8px; border-radius: 999px; font-weight: 600; }
  .badge.ok { background: #e6f7ee; color: #18794e; }
  .badge.warn { background: #fdf0e3; color: #9a5a16; }
  footer { color: #8a97a4; font-size: 12px; margin-top: 24px; }
"""


def main() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=10) as client:
        pdf = _run(client, _TOKENS["tenant-a"], _sample(PDF))
        xlsx = _run(client, _TOKENS["tenant-b"], _sample(XLSX))
    cards = _card("tenant-a", _sample(PDF).filename, pdf) + _card(
        "tenant-b", _sample(XLSX).filename, xlsx
    )
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Annotation report</title><style>{_STYLE}</style></head>
<body>
  <h1>Annotation report</h1>
  <p class="sub">Two tenants · groundedness-checked structured metadata · retrieved via
    <code>GET /annotations/{{job_id}}</code></p>
  <div class="grid">{cards}</div>
  <footer>Generated from a live stack by scripts/render_report.py · values are
    deterministically grounded against the curated text.</footer>
</body></html>"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(doc, encoding="utf-8")
    print(f"render_report: wrote {OUT}")


if __name__ == "__main__":
    main()
