"""Confidence Calibration: compute Brier scores from resolved applications."""

from __future__ import annotations

from dataclasses import dataclass

from backend.agents.planner.calibration import compute_calibration, CalibrationReport


@dataclass
class CalibrationDashboard:
    overall_brier: float
    sharpness: float
    n_resolved: int
    accuracy: float
    predicted_callbacks: int
    actual_callbacks: int
    calibration_buckets: list[dict]
    is_well_calibrated: bool
    interpretation: str


async def compute_brier_scores(user_id: str) -> CalibrationDashboard:
    """
    Fetch resolved applications from Supabase and compute calibration metrics.

    Only applications with a known `callback_probability` and a terminal status
    (offer, interviewing, rejected) are included in the calculation.
    """
    from backend.db import get_db

    rows = (
        get_db()
        .table("applications")
        .select("status, callback_probability")
        .eq("user_id", user_id)
        .in_("status", ["offer", "rejected", "interviewing"])
        .execute()
        .data
    )

    predictions: list[tuple[float, bool]] = []
    for row in rows:
        prob = row.get("callback_probability")
        if prob is None:
            continue
        outcome = row["status"] in ("offer", "interviewing")
        predictions.append((float(prob), outcome))

    report: CalibrationReport = compute_calibration(predictions)

    if predictions:
        probs = [p for p, _ in predictions]
        mean_p = sum(probs) / len(probs)
        sharpness = round(sum((p - mean_p) ** 2 for p in probs) / len(probs), 4)
    else:
        sharpness = 0.0

    buckets = [
        {
            "range_low": b.range_low,
            "range_high": b.range_high,
            "predicted_count": b.predicted_count,
            "actual_callbacks": b.actual_callbacks,
            "actual_rate": b.actual_rate,
        }
        for b in report.calibration_buckets
    ]

    return CalibrationDashboard(
        overall_brier=report.brier_score,
        sharpness=sharpness,
        n_resolved=report.total_predictions,
        accuracy=report.accuracy,
        predicted_callbacks=report.predicted_callbacks,
        actual_callbacks=report.actual_callbacks,
        calibration_buckets=buckets,
        is_well_calibrated=report.is_well_calibrated,
        interpretation=_interpret(report),
    )


def _interpret(report: CalibrationReport) -> str:
    if report.total_predictions == 0:
        return (
            "No resolved applications yet. Apply and track outcomes "
            "to see how accurate your callback predictions are."
        )

    bs = report.brier_score
    if bs < 0.05:
        quality = "excellent"
    elif bs < 0.10:
        quality = "good"
    elif bs < 0.15:
        quality = "fair"
    elif bs < 0.25:
        quality = "poor"
    else:
        quality = "no better than random"

    calibrated = "well-calibrated" if report.is_well_calibrated else "miscalibrated"

    return (
        f"Your callback predictions are {quality} (Brier {bs:.3f}) and {calibrated} "
        f"across {report.total_predictions} resolved applications — "
        f"predicted {report.predicted_callbacks} callbacks, "
        f"actual {report.actual_callbacks}."
    )
