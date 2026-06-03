# 0005. Untrusted-input handling & prompt-injection defense

- **Status:** Accepted
- **Date:** 2026-06-03

## Context

Every uploaded document is **untrusted**: it may be malformed, abusive
(resource-exhaustion), type-spoofed, or **poisoned with prompt injection**.
Constitution IV requires treating uploads as untrusted and building the cheap,
high-signal controls while documenting the rest.

**Threat model:**

| Threat | Vector | Attacker goal |
| --- | --- | --- |
| Malformed file | corrupt/truncated bytes | crash the worker, silent/partial result |
| Resource exhaustion | huge/nested file, zip/cell bomb, slow parse | DoS the worker (memory/CPU) |
| Type confusion | spoofed `Content-Type` header | reach a parser the bytes aren't meant for |
| Formula injection | spreadsheet `=WEBSERVICE/=HYPERLINK`/DDE | exfiltrate / execute on a victim machine |
| Active content | PDF embedded JS / launch actions | code execution during processing |
| **Prompt injection** | text saying "ignore instructions and …" | make the AI act, leak, or fabricate output |

## Decision

**Built now (cheap, high-signal):**

- **Content-type allowlist, not denylist** — accept only what we can parse
  (`pdf`, `xlsx`); else `415`. One `content_types.SUPPORTED` feeds both the HTTP
  allowlist and the parser router.
- **Bounded upload** — read at most `MAX_UPLOAD_BYTES + 1` → `413` (no memory
  blow-up); **page / sheet caps** (decompression/structure bombs).
- **Values, never formulas** — spreadsheets read with `data_only=True`, so
  `=WEBSERVICE`/`=HYPERLINK`/DDE payloads are never surfaced or evaluated.
- **No code execution on parse** — PDFs are text-extracted only; embedded JS,
  launch actions, and embedded files are never run.
- **Graceful, non-leaking failure** — any parse error → `failed{stage}` with a
  **stable, user-safe** message; the underlying exception is kept as the chained
  cause and logged, never returned to clients.

**Being built next (input-hardening slice):** a per-document **parse wall-clock
timeout** (closes the Constitution IV "parse timeouts" gap) and an **xlsx
cell-count cap** (zip/cell bombs under the sheet cap).

**Prompt-injection defense (LLM-adapter slice), defense-in-depth:**

1. **No ambient authority (architectural)** — the annotate step has no tools and
   no side effects; injected instructions cannot make it *act*. Strongest layer.
2. **Strict structured output** via Anthropic **tool-use** (validated JSON schema,
   not free-form actions).
3. **Content delimited & labelled untrusted** in the prompt (data to extract from,
   not instructions to follow).
4. **Groundedness check** — extracted values must appear in the curated text;
   fabricated/injected values are flagged and lower confidence.

**Documented for later (mature posture):** magic-byte/content sniffing
(anti-spoofing), broader types (`text/plain`, `csv`, `xls`, `docx`), sandboxed
parsing (subprocess/seccomp with hard CPU/mem/wall-clock kill), malware scanning +
CDR, AI-layer hardening (injection classifiers, output policy, per-tenant prompt
isolation), and per-tenant quotas / rate limiting. Malware scanning, WAF, and rate
limiting are on the explicit out-of-scope list.

## Consequences

- High-signal controls are in place cheaply; a clear production roadmap exists.
- The strongest injection defense (no ambient authority) is structural, not a
  filter that can be bypassed.
- Some hardening (timeout, sandboxing, sniffing) is deferred — tracked above.

## Alternatives considered

- **Denylist of bad types** — unbounded attack surface; rejected for an allowlist.
- **Accept any file type** — attack surface + quality risk; rejected.
- **Full malware scanning / sandboxing now** — high value but out of scope for the
  8-hour box; documented instead.
