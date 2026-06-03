"""LiteLLM transport — one adapter, many providers (Anthropic or Ollama).

The provider is chosen by the model string (`anthropic/claude-...` vs
`ollama/llama3.1`), so the same code path serves cloud and fully-local testing.
`litellm` is imported lazily so the rest of the app (and CI) needn't install it.
"""

from __future__ import annotations

import json
from typing import Any

from app.application.ports.llm_transport import TransportError


def parse_json_object(content: str | None) -> dict[str, Any]:
    """Parse a JSON object from a model response, tolerating prose/code-fence noise."""
    if not content or not content.strip():
        raise TransportError("empty model response")
    candidates = [content]
    start, end = content.find("{"), content.rfind("}")
    if start != -1 and end > start:
        candidates.append(content[start : end + 1])
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    raise TransportError("model did not return a JSON object")


class LiteLLMTransport:
    def __init__(
        self, *, model: str, api_base: str | None = None, temperature: float = 0.0
    ) -> None:
        self._model = model
        self._api_base = api_base
        self._temperature = temperature

    def generate(self, *, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        try:
            import litellm
        except ImportError as exc:  # pragma: no cover - depends on the optional 'llm' extra
            raise TransportError("litellm is not installed (install the 'llm' extra)") from exc

        messages = [
            {
                "role": "system",
                "content": f"{system}\nRespond ONLY with a single JSON object matching this "
                f"JSON schema:\n{json.dumps(schema)}",
            },
            {"role": "user", "content": user},
        ]
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
        }
        if self._api_base:
            kwargs["api_base"] = self._api_base

        try:
            response = litellm.completion(response_format={"type": "json_object"}, **kwargs)
        except Exception:  # provider may reject response_format — retry without it
            try:
                response = litellm.completion(**kwargs)
            except Exception as exc:  # pragma: no cover - network/provider failure
                raise TransportError("LLM call failed") from exc

        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, KeyError) as exc:  # pragma: no cover
            raise TransportError("malformed LLM response") from exc
        return parse_json_object(content)
