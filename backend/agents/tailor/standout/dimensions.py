"""The 8 Standout Engine dimensions — what impresses the human after the ATS passes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class StandoutDimension:
    id: str
    name: str
    description: str
    max_score: float = 100.0
    scorer_fn: Optional[Callable] = None


STANDOUT_DIMENSIONS = {
    "spike_factor": StandoutDimension(
        id="spike_factor",
        name="Spike Factor",
        description=(
            "Measures whether the candidate has a standout 'spike' — one or two "
            "achievements so impressive they alone justify an interview. "
            "Looks for: top-percentile scale metrics (>1M users, >$1M impact), "
            "marquee company names, awards, patents, viral projects. "
            "A single 10x spike matters more than ten 2x achievements."
        ),
    ),
    "trajectory_signal": StandoutDimension(
        id="trajectory_signal",
        name="Trajectory Signal",
        description=(
            "Detects a visible career arc — is this person accelerating? "
            "Signals: progressively senior titles, shrinking time between promotions, "
            "growing scope (team size, revenue owned, system scale), domain deepening "
            "or strategic pivots. Flat trajectories score low."
        ),
    ),
    "builder_ratio": StandoutDimension(
        id="builder_ratio",
        name="Builder Ratio",
        description=(
            "What fraction of the resume shows BUILDING (created, launched, designed, "
            "shipped) vs MAINTAINING (managed, supported, assisted, monitored)? "
            "Builders score higher. Ratio >0.7 = excellent, <0.3 = red flag. "
            "Weighted toward recent experience."
        ),
    ),
    "outcome_density": StandoutDimension(
        id="outcome_density",
        name="Outcome Density",
        description=(
            "How many bullets contain a concrete outcome (metric, result, shipped artifact) "
            "vs how many are pure activity descriptions? "
            "Outcome density = outcomes / total_bullets. "
            "Target: >60% for senior, >40% for mid, >25% for junior."
        ),
    ),
    "narrative_pull": StandoutDimension(
        id="narrative_pull",
        name="Narrative Pull",
        description=(
            "Does this resume tell a story that makes you want to keep reading? "
            "Checks: career theme coherence, summary that hooks, progression logic, "
            "role-to-role narrative bridges. A resume with narrative pull answers "
            "'why this person, why this role' without the reader asking."
        ),
    ),
    "uniqueness_index": StandoutDimension(
        id="uniqueness_index",
        name="Uniqueness Index",
        description=(
            "How differentiated is this candidate from the typical applicant pool? "
            "Signals: unusual skill combinations (e.g., ML + biology), cross-domain "
            "experience, unconventional education, side projects, publications, "
            "open source contributions, speaking engagements."
        ),
    ),
    "credibility_anchors": StandoutDimension(
        id="credibility_anchors",
        name="Credibility Anchors",
        description=(
            "External proof points that independently verify quality: "
            "recognized companies (FAANG, YC-backed), ranked universities, "
            "publications, patents, certifications from reputable bodies, "
            "open source project stars, conference talks. "
            "These anchors let the reader skip skepticism."
        ),
    ),
    "first_impression": StandoutDimension(
        id="first_impression",
        name="First Impression (6-Second Test)",
        description=(
            "What a recruiter gleans in the first 6 seconds: "
            "name/title clarity, summary quality (specific vs generic), "
            "most recent company/title visibility, visual hierarchy, "
            "top 2 bullets strength. This dimension predicts whether "
            "the reader continues past the fold."
        ),
    ),
}
