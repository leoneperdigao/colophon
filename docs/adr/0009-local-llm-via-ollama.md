# 0009. Local LLM via Ollama (one LiteLLM transport, provider by model string)

- **Status:** Accepted
- **Date:** 2026-06-03

## Context

The locked stack was LiteLLM → Anthropic (ADR-0006 / constitution). Running or
testing the annotation pipeline then needs an Anthropic API key and incurs cost —
friction for a clone-and-run local setup and for iterating on the agent. We want
the service to be **fully testable locally** with no key and no spend.

## Decision

Use **one** `LiteLLMTransport`; the provider is selected by the **model string**:
`anthropic/claude-3-5-haiku-latest` (cloud) or `ollama/llama3.1` (local). The
default is a local Ollama model, overridable via `LLM_MODEL` (+ `LLM_API_BASE`).
Because a local model's structured-output / tool-use is less reliable than
Anthropic's, the agent does **not** depend on strict tool-use: it requests a JSON
object (schema in the prompt + `response_format`), then **validates and repairs**
the output and runs the **groundedness** check. `litellm` is an optional `llm`
extra, imported lazily, so the rest of the app and CI don't require it.

## Consequences

- Full local, infra-free annotation testing — no API key, no cost.
- Identical code path for cloud (Anthropic) and local (Ollama) — a config swap.
- Local model quality is lower; acceptable for development, and the gold-set eval
  (`make eval`) gates real quality regardless of provider.

## Alternatives considered

- **Anthropic only** — every local run needs a key and costs money.
- **A separate adapter per provider** — duplication; LiteLLM already abstracts the
  providers behind one interface.
