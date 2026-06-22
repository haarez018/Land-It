"""Per-role weight distributions for the 8 Standout Engine dimensions. Weights sum to 1.0."""

from __future__ import annotations

STANDOUT_ROLE_PROFILES: dict[str, dict[str, float]] = {
    "software_engineer_backend": {
        "spike_factor": 0.12,
        "trajectory_signal": 0.10,
        "builder_ratio": 0.18,
        "outcome_density": 0.15,
        "narrative_pull": 0.08,
        "uniqueness_index": 0.10,
        "credibility_anchors": 0.12,
        "first_impression": 0.15,
    },
    "software_engineer_frontend": {
        "spike_factor": 0.10,
        "trajectory_signal": 0.08,
        "builder_ratio": 0.20,
        "outcome_density": 0.12,
        "narrative_pull": 0.10,
        "uniqueness_index": 0.12,
        "credibility_anchors": 0.10,
        "first_impression": 0.18,
    },
    "ml_engineer": {
        "spike_factor": 0.15,
        "trajectory_signal": 0.10,
        "builder_ratio": 0.12,
        "outcome_density": 0.15,
        "narrative_pull": 0.08,
        "uniqueness_index": 0.10,
        "credibility_anchors": 0.18,
        "first_impression": 0.12,
    },
    "product_manager": {
        "spike_factor": 0.15,
        "trajectory_signal": 0.15,
        "builder_ratio": 0.08,
        "outcome_density": 0.18,
        "narrative_pull": 0.15,
        "uniqueness_index": 0.07,
        "credibility_anchors": 0.10,
        "first_impression": 0.12,
    },
    "data_scientist": {
        "spike_factor": 0.14,
        "trajectory_signal": 0.08,
        "builder_ratio": 0.10,
        "outcome_density": 0.15,
        "narrative_pull": 0.08,
        "uniqueness_index": 0.12,
        "credibility_anchors": 0.20,
        "first_impression": 0.13,
    },
    "devops_sre": {
        "spike_factor": 0.10,
        "trajectory_signal": 0.10,
        "builder_ratio": 0.20,
        "outcome_density": 0.15,
        "narrative_pull": 0.07,
        "uniqueness_index": 0.08,
        "credibility_anchors": 0.15,
        "first_impression": 0.15,
    },
    "research_scientist": {
        "spike_factor": 0.18,
        "trajectory_signal": 0.08,
        "builder_ratio": 0.05,
        "outcome_density": 0.10,
        "narrative_pull": 0.10,
        "uniqueness_index": 0.15,
        "credibility_anchors": 0.24,
        "first_impression": 0.10,
    },
    "design_ux": {
        "spike_factor": 0.12,
        "trajectory_signal": 0.10,
        "builder_ratio": 0.18,
        "outcome_density": 0.10,
        "narrative_pull": 0.15,
        "uniqueness_index": 0.12,
        "credibility_anchors": 0.08,
        "first_impression": 0.15,
    },
}


def get_standout_role_profile(role_type: str) -> dict[str, float]:
    """Return standout dimension weights for a given role type."""
    return STANDOUT_ROLE_PROFILES.get(role_type, _get_generic_standout_profile())


def _get_generic_standout_profile() -> dict[str, float]:
    """Uniform fallback: equal weight per standout dimension."""
    n = 8
    return {k: round(1.0 / n, 4) for k in STANDOUT_ROLE_PROFILES["software_engineer_backend"]}
