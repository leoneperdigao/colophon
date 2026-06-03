"""Run the gold-set evaluation: parse + annotate each generated document, score
against its known labels, and gate on thresholds.

`make eval` runs this against the configured LLM (Ollama locally, or Anthropic),
so it needs a model available. The harness itself (parse → score → thresholds) is
tested in CI with an injected oracle, no model required.
"""

from __future__ import annotations

import sys

from app.adapters.parsing.factory import build_document_parser
from app.application.ports.document_parser import ParseError
from app.application.ports.llm_client import LLMClient, LLMError
from eval.metrics import Prediction, Report, Thresholds, compute_report
from samples.generate import build_gold_set


def _norm(value: str) -> str:
    return value.strip().casefold()


def evaluate(llm: LLMClient) -> Report:
    parser = build_document_parser()
    predictions: list[Prediction] = []
    for sample in build_gold_set():
        expected = frozenset(_norm(value) for _type, value in sample.key_entities)
        try:
            curated = parser.parse(sample.content, sample.content_type, sample.filename)
            annotation = llm.annotate(curated, sample.filename)
        except (ParseError, LLMError):
            predictions.append(
                Prediction(sample.document_type, "", expected, frozenset(), False, frozenset())
            )
            continue
        predictions.append(
            Prediction(
                expected_type=sample.document_type,
                predicted_type=annotation.document_type,
                expected_values=expected,
                predicted_values=frozenset(_norm(e.value) for e in annotation.key_entities),
                schema_valid=True,
                ungrounded_values=frozenset(_norm(v) for v in annotation.ungrounded_fields),
            )
        )
    return compute_report(predictions)


def main() -> int:
    from app.adapters.llm.factory import build_annotator  # lazy: avoids importing litellm in CI

    report = evaluate(build_annotator())
    print(report.render())
    shortfalls = report.shortfalls(Thresholds())
    if shortfalls:
        print("\nFAILED — below thresholds:")
        for line in shortfalls:
            print(f"  - {line}")
        return 1
    print("\nPASS — all thresholds met")
    return 0


if __name__ == "__main__":
    sys.exit(main())
