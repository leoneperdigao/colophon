"""Gold-set scoring metrics (pure). T050."""

from __future__ import annotations

from collections.abc import Iterable

from eval.metrics import Prediction, Thresholds, compute_report


def _p(
    expected_type: str,
    predicted_type: str,
    expected: Iterable[str] = (),
    predicted: Iterable[str] = (),
    *,
    valid: bool = True,
    ungrounded: Iterable[str] = (),
) -> Prediction:
    return Prediction(
        expected_type=expected_type,
        predicted_type=predicted_type,
        expected_values=frozenset(expected),
        predicted_values=frozenset(predicted),
        schema_valid=valid,
        ungrounded_values=frozenset(ungrounded),
    )


def test_document_type_accuracy() -> None:
    report = compute_report([_p("invoice", "invoice"), _p("report", "invoice")])
    assert report.document_type_accuracy == 0.5


def test_entity_precision_and_recall_micro_averaged() -> None:
    # predicted {acme, ghost} vs expected {acme, $5}: TP=1 -> P=1/2, R=1/2
    report = compute_report([_p("invoice", "invoice", {"acme", "$5"}, {"acme", "ghost"})])
    assert report.entity_precision == 0.5
    assert report.entity_recall == 0.5


def test_schema_valid_rate() -> None:
    report = compute_report([_p("a", "a", valid=True), _p("a", "a", valid=False)])
    assert report.schema_valid_rate == 0.5


def test_groundedness_rate() -> None:
    # predicted {acme, $5}, ungrounded {$5} -> 1 of 2 grounded
    report = compute_report([_p("a", "a", set(), {"acme", "$5"}, ungrounded={"$5"})])
    assert report.groundedness_rate == 0.5


def test_perfect_predictions_pass_thresholds() -> None:
    report = compute_report([_p("invoice", "invoice", {"acme"}, {"acme"})])
    assert report.passes(Thresholds())


def test_below_threshold_fails() -> None:
    report = compute_report([_p("invoice", "report")])  # wrong type
    assert not report.passes(Thresholds(document_type_accuracy=0.9))
