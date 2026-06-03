# Untrusted input & document poisoning — security posture

Every uploaded document is **untrusted**: it may be malformed, abusive
(resource-exhaustion), type-spoofed, or **poisoned with prompt injection**. This
is the posture — what's built, what's being built, and what's documented for
later. Split per Constitution IV (Security by Default) and the scope-discipline
rule (build the cheap controls, document the rest).

## Threat model

| Threat | Vector | Goal of the attacker |
| --- | --- | --- |
| Malformed file | corrupt/truncated bytes | crash the worker, silent/partial result |
| Resource exhaustion | huge/deeply-nested file, zip/cell bomb, slow-to-parse | DoS the worker (memory/CPU) |
| Type confusion | spoofed `Content-Type` header | reach a parser the bytes aren't meant for |
| Formula injection | spreadsheet `=WEBSERVICE/=HYPERLINK`/DDE | exfiltrate data / execute on a victim's machine |
| Active content | PDF embedded JS / launch actions / embedded files | code execution during processing |
| **Prompt injection** | text that says "ignore instructions and …" | make the AI step act, leak, or fabricate output |

## Built (cheap, high-signal controls)

- **Content-type allowlist, not denylist** — accept only what we can parse
  (`pdf`, `xlsx`); everything else is `415` at the edge. One `content_types`
  source of truth feeds both the HTTP allowlist and the parser router.
- **Bounded upload** — read at most `MAX_UPLOAD_BYTES + 1`; oversized → `413`
  (no memory exhaustion from a large body).
- **Page / sheet caps** — reject documents over the page/sheet limit (defends
  decompression/structure bombs).
- **Values, never formulas** — spreadsheets are read with `data_only=True`, so a
  `=WEBSERVICE(...)`/`=HYPERLINK(...)`/DDE payload is never surfaced or evaluated.
- **No code execution on parse** — PDF handling extracts *text only*; embedded
  JavaScript, launch actions, and embedded files are never run or followed.
- **Graceful failure** — any parser exception becomes a `ParseError` → the job
  ends `failed{stage}` with the error. No crash, no silent or partial success.
- **(LLM slice) No ambient authority** — the annotation step has **no tools and
  no side effects**, so injected instructions cannot make it *act*.

## Being built next (input-hardening slice)

- **Parse wall-clock timeout** — a per-document time budget around `parse()` so a
  crafted slow-to-parse file can't pin a worker CPU (Constitution IV requires
  parse timeouts; this closes the gap).
- **Cell-count cap (xlsx)** — bound total cells read, hardening against zip/cell
  bombs that stay under the sheet cap.

## Prompt-injection defense (LLM-adapter / agent slice)

Defense-in-depth so that poisoned content cannot redirect the system:

1. **No ambient authority (architectural)** — the agent can only emit schema
   fields; it has no tools and no side effects, so "ignore instructions and
   delete everything" is inert. Strongest layer.
2. **Strict structured output** — Anthropic **tool-use** forces a validated JSON
   schema; the model returns fields, never free-form text or actions.
3. **Content delimited & labelled untrusted** — document text is wrapped in clear
   boundaries and presented as *data to extract from, not instructions to follow*.
4. **Groundedness check (deterministic)** — extracted values must appear in the
   curated text; fabricated/injected entities are flagged and lower confidence.
5. **Output validation/repair** — non-conforming output is repaired or the job
   fails loudly, never served as authoritative.

## Documented for later (the mature posture)

- **Magic-byte / content sniffing** — verify the real signature (`%PDF-`,
  `PK\x03\x04` zip) at the edge so a spoofed `Content-Type` is rejected up front,
  not deep in the parser. (Today a spoofed type still fails *gracefully* because
  the real parser rejects it.)
- **Broader file types** — `text/plain` (low attack surface), `csv` (stdlib),
  legacy `xls`, `docx`; each is a new parser behind the router + one allowlist
  entry. Keep the allowlist discipline.
- **Sandboxed parsing** — run parsers in a subprocess / seccomp / gVisor / Lambda
  with no network and a hard CPU+memory+wall-clock kill, so a parser-library
  exploit or runaway loop is contained (a thread cannot truly cancel a C-loop).
- **Malware scanning & CDR** — ClamAV (or a cloud scanner) and content
  disarm-and-reconstruct on upload, before processing.
- **AI-layer hardening at scale** — injection/jailbreak classifiers on the input,
  an output policy (entity allow/deny, PII handling), per-tenant prompt isolation
  (one tenant's content never enters another's context), and red-team/eval suites
  for injection regression.
- **Abuse limits** — per-tenant upload quotas and rate limiting (noisy-neighbour
  / cost-bomb defense). WAF + rate limiting at the edge.

Malware scanning, WAF, and rate limiting are on the project's explicit
out-of-scope list — documented here, built in production.
