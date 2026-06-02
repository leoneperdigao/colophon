"""Upload helpers — treat client-supplied metadata as untrusted."""

from __future__ import annotations

import ntpath
import posixpath


def safe_filename(raw: str | None) -> str:
    """Reduce a client-supplied filename to a bare basename.

    Browsers and some clients send path-laden names (``C:\\fakepath\\f.pdf`` or
    ``/a/b/f.pdf``). The filename flows into blob keys and the deterministic
    job_id, so strip any directory component (both separators) and fall back to a
    safe default when nothing usable remains.
    """
    name = posixpath.basename(ntpath.basename(raw or ""))
    return name or "upload"
