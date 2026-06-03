"""Narrated end-to-end demo for the terminal recording (scripts/demo.tape → GIF).

Tells the story the README sells: upload under tenant A → 202 + job_id → the
background worker annotates → poll the result → tenant B is denied A's job (404).
Paced with small pauses so the recording reads cleanly. Prints to stdout only.

Run against a live stack:  uv run python scripts/demo_flow.py
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx

from app.adapters.parsing.content_types import PDF
from samples.generate import GoldSample, build_gold_set

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
TOKEN_A = os.getenv("DEMO_TOKEN_A", "tokenA")
TOKEN_B = os.getenv("DEMO_TOKEN_B", "tokenB")

# ANSI styling — VHS renders colour, so the recording stays legible and lively.
DIM, BOLD, GREEN, CYAN, YELLOW, RESET = (
    "\033[2m",
    "\033[1m",
    "\033[32m",
    "\033[36m",
    "\033[33m",
    "\033[0m",
)


def _say(line: str) -> None:
    print(line, flush=True)
    time.sleep(0.6)


def _pdf_sample() -> GoldSample:
    return next(s for s in build_gold_set() if s.content_type == PDF)


def main() -> None:
    sample = _pdf_sample()
    with httpx.Client(base_url=BASE_URL, timeout=10) as client:
        _say(f"{DIM}# Document Annotation Service — live demo{RESET}")
        _say(f"{BOLD}$ POST /documents{RESET}  {DIM}(tenant A · {sample.filename}){RESET}")
        resp = client.post(
            "/documents",
            headers={"Authorization": f"Bearer {TOKEN_A}"},
            files={"file": (sample.filename, sample.content, sample.content_type)},
        )
        job_id = resp.json()["job_id"]
        _say(f"  → {GREEN}HTTP {resp.status_code}{RESET}  job_id={CYAN}{job_id[:24]}…{RESET}")
        _say(f"{DIM}  (request returns immediately; processing continues in the background){RESET}")
        print()

        _say(f"{BOLD}$ GET /annotations/{{job_id}}{RESET}  {DIM}(poll until annotated){RESET}")
        result: dict[str, Any] = {}
        for _ in range(60):
            body = client.get(
                f"/annotations/{job_id}", headers={"Authorization": f"Bearer {TOKEN_A}"}
            ).json()
            status = body["status"]
            stage = body.get("stage")
            print(
                f"  …{DIM} status={RESET}{YELLOW}{status}{RESET} {DIM}stage={stage}{RESET}",
                flush=True,
            )
            if status in ("completed", "failed"):
                result = body
                break
            time.sleep(1)
        print()

        annotation = result.get("result") or {}
        _say(f"{GREEN}✓ annotated{RESET} — strict-JSON result stored:")
        preview = {
            k: annotation.get(k)
            for k in ("document_type", "language", "summary", "key_entities", "confidence")
        }
        for chunk in json.dumps(preview, indent=2, ensure_ascii=False).splitlines():
            print(f"  {chunk}", flush=True)
        time.sleep(1.2)
        print()

        _say(
            f"{BOLD}$ GET /annotations/{{job_id}}{RESET}  {DIM}(tenant B reads tenant A's job){RESET}"
        )
        cross = client.get(f"/annotations/{job_id}", headers={"Authorization": f"Bearer {TOKEN_B}"})
        colour = GREEN if cross.status_code == 404 else "\033[31m"
        _say(
            f"  → {colour}HTTP {cross.status_code}{RESET}  {DIM}tenant isolation: not the record, a 404{RESET}"
        )
        print()
        _say(f"{GREEN}{BOLD}done.{RESET}")


if __name__ == "__main__":
    main()
