"""Gold-set scoring: document-type accuracy, entity precision/recall, schema-valid
rate, and groundedness — pure functions over per-document predictions (no IO/LLM).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Prediction:
    expected_type: str
    predicted_type: str
    expected_values: frozenset[str]
    predicted_values: frozenset[str]
    schema_valid: bool
    ungrounded_values: frozenset[str]


@dataclass(frozen=True)
class Thresholds:
    document_type_accuracy: float = 0.90
    entity_precision: float = 0.80
    entity_recall: float = 0.80
    schema_valid_rate: float = 1.00
    groundedness_rate: float = 0.95


@dataclass(frozen=True)
class Report:
    count: int
    document_type_accuracy: float
    entity_precision: float
    entity_recall: float
    schema_valid_rate: float
    groundedness_rate: float
    failures: list[str] = field(default_factory=list)

    def passes(self, thresholds: Thresholds) -> bool:
        return not self.shortfalls(thresholds)

    def shortfalls(self, thresholds: Thresholds) -> list[str]:
        checks = {
            "document_type_accuracy": thresholds.document_type_accuracy,
            "entity_precision": thresholds.entity_precision,
            "entity_recall": thresholds.entity_recall,
            "schema_valid_rate": thresholds.schema_valid_rate,
            "groundedness_rate": thresholds.groundedness_rate,
        }
        return [
            f"{name}: {getattr(self, name):.3f} < {minimum:.3f}"
            for name, minimum in checks.items()
            if getattr(self, name) < minimum
        ]

    def render(self) -> str:
        lines = [
            f"gold set: {self.count} documents",
            f"  document_type_accuracy : {self.document_type_accuracy:.3f}",
            f"  entity_precision       : {self.entity_precision:.3f}",
            f"  entity_recall          : {self.entity_recall:.3f}",
            f"  schema_valid_rate      : {self.schema_valid_rate:.3f}",
            f"  groundedness_rate      : {self.groundedness_rate:.3f}",
        ]
        return "\n".join(lines)


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 1.0


def compute_report(predictions: Sequence[Prediction]) -> Report:
    count = len(predictions)
    type_hits = sum(p.expected_type == p.predicted_type for p in predictions)

    true_positives = sum(len(p.predicted_values & p.expected_values) for p in predictions)
    predicted_total = sum(len(p.predicted_values) for p in predictions)
    expected_total = sum(len(p.expected_values) for p in predictions)
    ungrounded_total = sum(len(p.ungrounded_values) for p in predictions)

    return Report(
        count=count,
        document_type_accuracy=_ratio(type_hits, count),
        entity_precision=_ratio(true_positives, predicted_total),
        entity_recall=_ratio(true_positives, expected_total),
        schema_valid_rate=_ratio(sum(p.schema_valid for p in predictions), count),
        groundedness_rate=_ratio(predicted_total - ungrounded_total, predicted_total),
    )
