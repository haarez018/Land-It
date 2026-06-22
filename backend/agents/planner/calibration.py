"""Confidence Calibration Dashboard: measures prediction accuracy with Brier score."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class CalibrationBucket:
    range_low: float
    range_high: float
    predicted_count: int
    actual_callbacks: int
    actual_rate: float


@dataclass
class CalibrationReport:
    total_predictions: int
    total_outcomes_known: int
    predicted_callbacks: int
    actual_callbacks: int
    accuracy: float
    brier_score: float
    calibration_buckets: list[CalibrationBucket]
    is_well_calibrated: bool
    adjustment_needed: str | None


def compute_calibration(
    predictions: list[tuple[float, bool]],
) -> CalibrationReport:
    """
    Args:
        predictions: list of (predicted_probability, actual_outcome) pairs
    """
    if not predictions:
        return CalibrationReport(
            total_predictions=0, total_outcomes_known=0,
            predicted_callbacks=0, actual_callbacks=0,
            accuracy=0, brier_score=1.0,
            calibration_buckets=[], is_well_calibrated=False,
            adjustment_needed="No data — need prediction/outcome pairs",
        )

    n = len(predictions)
    actual_callbacks = sum(1 for _, outcome in predictions if outcome)
    predicted_callbacks = sum(1 for prob, _ in predictions if prob >= 0.30)

    # Brier score: mean squared error of probability predictions
    brier = sum((prob - (1.0 if outcome else 0.0)) ** 2 for prob, outcome in predictions) / n

    # Bucketed calibration
    bucket_edges = [(0, 0.1), (0.1, 0.2), (0.2, 0.3), (0.3, 0.4), (0.4, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 1.0)]
    buckets: list[CalibrationBucket] = []
    max_deviation = 0

    for lo, hi in bucket_edges:
        in_bucket = [(p, o) for p, o in predictions if lo <= p < hi]
        if in_bucket:
            count = len(in_bucket)
            actual = sum(1 for _, o in in_bucket if o)
            rate = actual / count
            buckets.append(CalibrationBucket(lo, hi, count, actual, round(rate, 3)))
            midpoint = (lo + hi) / 2
            max_deviation = max(max_deviation, abs(rate - midpoint))

    well_calibrated = brier < 0.25 and max_deviation < 0.15

    # Accuracy: % of correct binary predictions (threshold 0.30)
    correct = sum(
        1 for prob, outcome in predictions
        if (prob >= 0.30 and outcome) or (prob < 0.30 and not outcome)
    )
    accuracy = correct / n if n else 0

    adjustment = None
    if not well_calibrated:
        if brier >= 0.25:
            adjustment = f"Brier score {brier:.3f} is high — sigmoid parameters may need tuning"
        elif max_deviation >= 0.15:
            adjustment = f"Max bucket deviation {max_deviation:.2f} — predictions are over/under-confident"

    return CalibrationReport(
        total_predictions=n,
        total_outcomes_known=n,
        predicted_callbacks=predicted_callbacks,
        actual_callbacks=actual_callbacks,
        accuracy=round(accuracy, 3),
        brier_score=round(brier, 4),
        calibration_buckets=buckets,
        is_well_calibrated=well_calibrated,
        adjustment_needed=adjustment,
    )
