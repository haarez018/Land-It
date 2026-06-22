"""Seniority-based weight adjustments for the 8 Standout Engine dimensions."""

from __future__ import annotations

STANDOUT_SENIORITY_MULTIPLIERS: dict[str, dict[str, float]] = {
    "intern": {
        "spike_factor": 0.5,          # Interns rarely have spikes — downweight
        "trajectory_signal": 0.4,     # Too early for trajectory
        "builder_ratio": 1.2,         # Show you build, even as an intern
        "outcome_density": 0.6,       # Lower expectations
        "narrative_pull": 0.7,        # Story matters less early on
        "uniqueness_index": 1.4,      # Side projects matter MORE for interns
        "credibility_anchors": 1.5,   # School, hackathons, early signals matter a lot
        "first_impression": 1.3,      # Must nail the first look
    },
    "junior": {
        "spike_factor": 0.7,
        "trajectory_signal": 0.6,
        "builder_ratio": 1.2,
        "outcome_density": 0.8,
        "narrative_pull": 0.8,
        "uniqueness_index": 1.3,
        "credibility_anchors": 1.3,
        "first_impression": 1.2,
    },
    "mid": {
        "spike_factor": 1.0,
        "trajectory_signal": 1.0,
        "builder_ratio": 1.0,
        "outcome_density": 1.0,
        "narrative_pull": 1.0,
        "uniqueness_index": 1.0,
        "credibility_anchors": 1.0,
        "first_impression": 1.0,
    },
    "senior": {
        "spike_factor": 1.3,          # Spikes matter — show 10x impact
        "trajectory_signal": 1.3,     # Should show clear progression
        "builder_ratio": 1.1,
        "outcome_density": 1.4,       # High expectations for outcomes
        "narrative_pull": 1.2,        # Story should be compelling
        "uniqueness_index": 0.8,      # Less novelty weight
        "credibility_anchors": 0.9,
        "first_impression": 1.0,
    },
    "staff_principal": {
        "spike_factor": 1.5,          # Must have at least one 10x spike
        "trajectory_signal": 1.4,
        "builder_ratio": 1.0,
        "outcome_density": 1.5,       # Every bullet should have an outcome
        "narrative_pull": 1.4,        # Career arc is the story
        "uniqueness_index": 0.7,
        "credibility_anchors": 0.8,
        "first_impression": 0.9,
    },
    "executive": {
        "spike_factor": 1.6,          # Must have multiple jaw-droppers
        "trajectory_signal": 1.5,     # Arc from IC to exec
        "builder_ratio": 0.8,         # More strategy, less building
        "outcome_density": 1.6,       # Revenue, team, company-level outcomes
        "narrative_pull": 1.5,        # Resume IS the narrative
        "uniqueness_index": 0.6,
        "credibility_anchors": 1.0,
        "first_impression": 0.8,
    },
}


def apply_standout_seniority_adjustment(
    base_weights: dict[str, float],
    seniority: str,
) -> dict[str, float]:
    """Multiply base standout weights by seniority multipliers, then renormalize to sum 1.0."""
    multipliers = STANDOUT_SENIORITY_MULTIPLIERS.get(
        seniority, STANDOUT_SENIORITY_MULTIPLIERS["mid"]
    )
    adjusted = {k: base_weights[k] * multipliers[k] for k in base_weights}
    total = sum(adjusted.values())
    if total == 0:
        return base_weights
    return {k: v / total for k, v in adjusted.items()}
