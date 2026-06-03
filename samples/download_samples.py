"""Download a small corpus of real public PDFs + spreadsheets for robustness testing.

These are **real-world files with no ground-truth labels** — for smoke / robustness
/ load testing, distinct from the generated, ground-truth gold set the eval uses.
Sources are permissively licensed; files download on demand into
`samples/downloaded/` (gitignored) and are never committed.

Usage:  uv run python samples/download_samples.py [--dest samples/downloaded]
"""

from __future__ import annotations

import argparse
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import cast

# Pinned to specific commits for reproducibility (upstream `main` moves). To
# refresh, bump these SHAs to a newer commit and re-verify the file paths exist.
_PYPDF_REF = "818dc013ad1f537198e9fcfae8a6b0dffe25ffa3"
_PANDAS_REF = "1e1d67b5f67044c658d18986d2d8d4a6c8ec3521"
_PYPDF = f"https://raw.githubusercontent.com/py-pdf/sample-files/{_PYPDF_REF}"
_PANDAS = (
    f"https://raw.githubusercontent.com/pandas-dev/pandas/{_PANDAS_REF}/pandas/tests/io/data/excel"
)
_PYPDF_LICENSE = "CC-BY-SA-4.0 (py-pdf/sample-files)"
_PANDAS_LICENSE = "BSD-3-Clause (pandas-dev/pandas)"

MAX_BYTES = 10 * 1024 * 1024
_MAGIC: dict[str, bytes] = {"pdf": b"%PDF", "xlsx": b"PK\x03\x04"}


@dataclass(frozen=True)
class Sample:
    kind: str  # "pdf" | "xlsx"
    url: str
    filename: str
    license: str


# A deliberately varied set: clean text, annotations, links, an encrypted PDF
# (graceful-failure case), image-heavy / scanned-image-only / large multi-page
# PDFs, plus normal / empty / blank-row spreadsheets.
MANIFEST: tuple[Sample, ...] = (
    Sample(
        "pdf",
        f"{_PYPDF}/002-trivial-libre-office-writer/002-trivial-libre-office-writer.pdf",
        "pdf-text-simple.pdf",
        _PYPDF_LICENSE,
    ),
    Sample(
        "pdf", f"{_PYPDF}/024-annotations/annotated_pdf.pdf", "pdf-annotated.pdf", _PYPDF_LICENSE
    ),
    Sample(
        "pdf",
        f"{_PYPDF}/016-libre-office-link/libre-office-link.pdf",
        "pdf-link.pdf",
        _PYPDF_LICENSE,
    ),
    Sample(
        "pdf",
        f"{_PYPDF}/005-libreoffice-writer-password/libreoffice-writer-password.pdf",
        "pdf-password-protected.pdf",
        _PYPDF_LICENSE,
    ),
    Sample(
        "pdf",
        f"{_PYPDF}/003-pdflatex-image/pdflatex-image.pdf",
        "pdf-image-with-text.pdf",  # embedded image + text
        _PYPDF_LICENSE,
    ),
    Sample(
        "pdf",
        f"{_PYPDF}/007-imagemagick-images/imagemagick-CCITTFaxDecode.pdf",
        "pdf-scanned-image-only.pdf",  # image-only -> no extractable text (graceful low-signal)
        _PYPDF_LICENSE,
    ),
    Sample(
        "pdf",
        f"{_PYPDF}/009-pdflatex-geotopo/GeoTopo.pdf",
        "pdf-large-multipage.pdf",  # ~5 MB multi-page real document (file-size range)
        _PYPDF_LICENSE,
    ),
    Sample("xlsx", f"{_PANDAS}/test_converters.xlsx", "xlsx-converters.xlsx", _PANDAS_LICENSE),
    Sample("xlsx", f"{_PANDAS}/dimension_small.xlsx", "xlsx-small.xlsx", _PANDAS_LICENSE),
    Sample("xlsx", f"{_PANDAS}/empty_with_blank_row.xlsx", "xlsx-blank-rows.xlsx", _PANDAS_LICENSE),
)


def detect_kind(content: bytes) -> str | None:
    """Identify a file by magic bytes (catches HTML error pages / wrong content)."""
    for kind, magic in _MAGIC.items():
        if content.startswith(magic):
            return kind
    return None


def _fetch(url: str, *, timeout: float) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "colophon-samples"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # fixed https raw hosts
        return cast(bytes, response.read(MAX_BYTES + 1))


def download(dest: Path, *, timeout: float = 30.0) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for sample in MANIFEST:
        try:
            content = _fetch(sample.url, timeout=timeout)
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"skip {sample.filename}: {exc}")
            continue
        if len(content) > MAX_BYTES:
            print(f"skip {sample.filename}: exceeds {MAX_BYTES} bytes")
            continue
        if detect_kind(content) != sample.kind:
            print(f"skip {sample.filename}: unexpected content (not a {sample.kind})")
            continue
        out = dest / sample.filename
        out.write_bytes(content)
        saved.append(out)
        print(f"saved {out}  ({len(content)} bytes)  [{sample.license}]")
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", default="samples/downloaded", help="output directory")
    parser.add_argument("--timeout", type=float, default=30.0, help="per-file timeout (seconds)")
    args = parser.parse_args()
    paths = download(Path(args.dest), timeout=args.timeout)
    print(f"\n{len(paths)}/{len(MANIFEST)} files downloaded into {args.dest}")
    print("Real-world robustness samples (no ground-truth labels); the eval gold set is")
    print("generated with known truth — see ADR-0010 and the eval harness.")


if __name__ == "__main__":
    main()
