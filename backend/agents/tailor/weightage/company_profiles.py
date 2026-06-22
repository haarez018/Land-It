"""
Company-specific scoring profiles — weight overrides applied on top of
role + seniority weights, then renormalized.

Each profile captures what a specific company or company archetype
disproportionately values in a candidate's resume. These are multipliers
on the already role+seniority-adjusted weights.

8 profiles:
  - google, stripe, netflix, meta, early_stage_startup,
    faang_generic, consulting_firm, mid_size_tech
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CompanyProfile:
    """A company-specific scoring weight adjustment profile."""
    id: str
    name: str
    hiring_philosophy: str
    # Multipliers for ATS dimensions (14). Missing keys → 1.0 (no change)
    ats_multipliers: dict[str, float] = field(default_factory=dict)
    # Multipliers for Standout dimensions (8). Missing keys → 1.0 (no change)
    standout_multipliers: dict[str, float] = field(default_factory=dict)
    interview_signals: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)


COMPANY_PROFILES: dict[str, CompanyProfile] = {
    "google": CompanyProfile(
        id="google",
        name="Google",
        hiring_philosophy=(
            "Google prizes system-design depth, education pedigree, and "
            "quantified impact at scale. Keywords matter less — they have "
            "strong internal screening."
        ),
        ats_multipliers={
            "keyword_density": 0.8,
            "skill_depth": 1.4,
            "tech_stack_alignment": 0.7,
            "experience_relevance": 1.3,
            "quantified_impact": 1.4,
            "action_verb_strength": 1.0,
            "section_ordering": 0.9,
            "bullet_quality": 1.1,
            "ats_parsability": 0.9,
            "seniority_calibration": 1.4,
            "domain_knowledge": 1.3,
            "education_relevance": 1.2,
            "semantic_similarity": 1.0,
            "voice_alignment": 0.7,
        },
        standout_multipliers={
            "spike_factor": 1.5,
            "trajectory_signal": 1.3,
            "builder_ratio": 1.0,
            "outcome_density": 1.3,
            "narrative_pull": 0.8,
            "uniqueness_index": 1.1,
            "credibility_anchors": 1.5,
            "first_impression": 0.9,
        },
        interview_signals=[
            "System design depth with scale metrics (>1M users)",
            "Publications, patents, or open-source contributions",
            "Progression from L3 to L5+ with clear scope increases",
        ],
        red_flags=[
            "Vague impact statements without numbers",
            "Only maintenance/support experience, no building",
        ],
    ),
    "stripe": CompanyProfile(
        id="stripe",
        name="Stripe",
        hiring_philosophy=(
            "Stripe values precise technical depth, quantified business "
            "outcomes, and a builder mindset. They want people who ship."
        ),
        ats_multipliers={
            "keyword_density": 1.0,
            "skill_depth": 1.5,
            "tech_stack_alignment": 1.4,
            "experience_relevance": 1.2,
            "quantified_impact": 1.6,
            "action_verb_strength": 1.2,
            "section_ordering": 0.9,
            "bullet_quality": 1.3,
            "ats_parsability": 1.0,
            "seniority_calibration": 1.1,
            "domain_knowledge": 1.3,
            "education_relevance": 0.6,
            "semantic_similarity": 1.0,
            "voice_alignment": 0.9,
        },
        standout_multipliers={
            "spike_factor": 1.3,
            "trajectory_signal": 1.1,
            "builder_ratio": 1.5,
            "outcome_density": 1.4,
            "narrative_pull": 1.3,
            "uniqueness_index": 0.9,
            "credibility_anchors": 1.1,
            "first_impression": 1.0,
        },
        interview_signals=[
            "Revenue or cost impact with exact dollar figures",
            "Experience with payments, fintech, or distributed systems",
            "Strong builder-verb-heavy bullet points (shipped, designed, architected)",
        ],
        red_flags=[
            "Generic resume with no quantified outcomes",
            "Heavy on 'managed' and 'coordinated' verbs",
        ],
    ),
    "netflix": CompanyProfile(
        id="netflix",
        name="Netflix",
        hiring_philosophy=(
            "Netflix's Freedom & Responsibility culture values senior, "
            "autonomous operators with massive impact and strong voice."
        ),
        ats_multipliers={
            "keyword_density": 0.8,
            "skill_depth": 1.2,
            "tech_stack_alignment": 1.0,
            "experience_relevance": 1.5,
            "quantified_impact": 1.5,
            "action_verb_strength": 1.5,
            "section_ordering": 0.8,
            "bullet_quality": 1.3,
            "ats_parsability": 0.9,
            "seniority_calibration": 1.5,
            "domain_knowledge": 1.0,
            "education_relevance": 0.5,
            "semantic_similarity": 0.8,
            "voice_alignment": 1.8,
        },
        standout_multipliers={
            "spike_factor": 1.4,
            "trajectory_signal": 1.4,
            "builder_ratio": 1.2,
            "outcome_density": 1.6,
            "narrative_pull": 1.3,
            "uniqueness_index": 1.0,
            "credibility_anchors": 0.8,
            "first_impression": 1.1,
        },
        interview_signals=[
            "Evidence of autonomous decision-making at senior level",
            "Large-scale impact metrics (team size, revenue, system scale)",
            "Clear career trajectory with shrinking time between promotions",
        ],
        red_flags=[
            "Junior titles or lack of autonomous leadership examples",
            "Education-heavy resume with thin work experience",
        ],
    ),
    "meta": CompanyProfile(
        id="meta",
        name="Meta",
        hiring_philosophy=(
            "Meta emphasizes tech stack alignment, move-fast culture, and "
            "experience relevance. Quantified impact with scale matters."
        ),
        ats_multipliers={
            "keyword_density": 1.0,
            "skill_depth": 1.2,
            "tech_stack_alignment": 1.3,
            "experience_relevance": 1.3,
            "quantified_impact": 1.2,
            "action_verb_strength": 1.1,
            "section_ordering": 1.0,
            "bullet_quality": 1.1,
            "ats_parsability": 1.0,
            "seniority_calibration": 1.2,
            "domain_knowledge": 1.0,
            "education_relevance": 1.0,
            "semantic_similarity": 1.0,
            "voice_alignment": 0.9,
        },
        standout_multipliers={
            "spike_factor": 1.3,
            "trajectory_signal": 1.2,
            "builder_ratio": 1.2,
            "outcome_density": 1.3,
            "narrative_pull": 0.9,
            "uniqueness_index": 1.0,
            "credibility_anchors": 1.2,
            "first_impression": 1.0,
        },
        interview_signals=[
            "Scale metrics with user-facing products (>10M users)",
            "Fast iteration and shipping cadence",
            "Cross-functional collaboration at scale",
        ],
        red_flags=[
            "Slow-paced, waterfall-style project descriptions",
            "No experience with large-scale consumer products",
        ],
    ),
    "early_stage_startup": CompanyProfile(
        id="early_stage_startup",
        name="Early-Stage Startup",
        hiring_philosophy=(
            "Startups need generalists who ship fast. Builder verbs > maintainer "
            "verbs, side projects matter, education is irrelevant."
        ),
        ats_multipliers={
            "keyword_density": 0.7,
            "skill_depth": 0.9,
            "tech_stack_alignment": 1.3,
            "experience_relevance": 1.0,
            "quantified_impact": 1.3,
            "action_verb_strength": 1.4,
            "section_ordering": 0.6,
            "bullet_quality": 1.1,
            "ats_parsability": 0.5,
            "seniority_calibration": 0.8,
            "domain_knowledge": 0.7,
            "education_relevance": 0.3,
            "semantic_similarity": 0.8,
            "voice_alignment": 1.2,
        },
        standout_multipliers={
            "spike_factor": 1.2,
            "trajectory_signal": 0.8,
            "builder_ratio": 1.8,
            "outcome_density": 1.2,
            "narrative_pull": 1.1,
            "uniqueness_index": 1.4,
            "credibility_anchors": 0.6,
            "first_impression": 1.3,
        },
        interview_signals=[
            "Side projects, open-source, or personal shipping evidence",
            "Full-stack or breadth experience across the stack",
            "Founding, co-founding, or early-employee experience",
        ],
        red_flags=[
            "Only big-company experience with narrow scope",
            "No evidence of working without heavy process/support",
        ],
    ),
    "faang_generic": CompanyProfile(
        id="faang_generic",
        name="FAANG (Generic)",
        hiring_philosophy=(
            "Balanced big-tech profile emphasizing system design, impact "
            "metrics, and seniority calibration."
        ),
        ats_multipliers={
            "keyword_density": 1.1,
            "skill_depth": 1.3,
            "tech_stack_alignment": 1.1,
            "experience_relevance": 1.2,
            "quantified_impact": 1.3,
            "action_verb_strength": 1.1,
            "section_ordering": 1.0,
            "bullet_quality": 1.1,
            "ats_parsability": 1.0,
            "seniority_calibration": 1.3,
            "domain_knowledge": 1.1,
            "education_relevance": 1.2,
            "semantic_similarity": 1.0,
            "voice_alignment": 0.8,
        },
        standout_multipliers={
            "spike_factor": 1.3,
            "trajectory_signal": 1.2,
            "builder_ratio": 1.1,
            "outcome_density": 1.2,
            "narrative_pull": 0.9,
            "uniqueness_index": 1.0,
            "credibility_anchors": 1.2,
            "first_impression": 1.0,
        },
        interview_signals=[
            "System design experience at meaningful scale",
            "Clear progression through engineering levels",
            "Strong academic credentials or equivalent proof points",
        ],
        red_flags=[
            "No quantified impact in any bullet point",
            "Unclear career progression despite many years of experience",
        ],
    ),
    "consulting_firm": CompanyProfile(
        id="consulting_firm",
        name="Consulting Firm (McKinsey/Bain/BCG)",
        hiring_philosophy=(
            "Consulting firms prize communication, structured thinking, "
            "and pedigree. Bullet quality and education matter enormously."
        ),
        ats_multipliers={
            "keyword_density": 0.9,
            "skill_depth": 0.7,
            "tech_stack_alignment": 0.5,
            "experience_relevance": 1.2,
            "quantified_impact": 1.5,
            "action_verb_strength": 1.3,
            "section_ordering": 1.2,
            "bullet_quality": 1.5,
            "ats_parsability": 1.0,
            "seniority_calibration": 1.2,
            "domain_knowledge": 1.3,
            "education_relevance": 1.4,
            "semantic_similarity": 1.0,
            "voice_alignment": 1.4,
        },
        standout_multipliers={
            "spike_factor": 1.1,
            "trajectory_signal": 1.4,
            "builder_ratio": 0.7,
            "outcome_density": 1.3,
            "narrative_pull": 1.5,
            "uniqueness_index": 1.2,
            "credibility_anchors": 1.5,
            "first_impression": 1.4,
        },
        interview_signals=[
            "Polished, MECE-structured bullet points",
            "Top university or MBA",
            "Cross-industry or cross-functional experience",
        ],
        red_flags=[
            "Purely technical resume with no business impact",
            "Weak education section without compensating experience",
        ],
    ),
    "mid_size_tech": CompanyProfile(
        id="mid_size_tech",
        name="Mid-Size Tech Company",
        hiring_philosophy=(
            "Balanced profile with slight emphasis on tech stack fit and "
            "domain knowledge. Practical, no extreme biases."
        ),
        ats_multipliers={
            "keyword_density": 1.0,
            "skill_depth": 1.1,
            "tech_stack_alignment": 1.2,
            "experience_relevance": 1.1,
            "quantified_impact": 1.1,
            "action_verb_strength": 1.0,
            "section_ordering": 1.0,
            "bullet_quality": 1.1,
            "ats_parsability": 1.0,
            "seniority_calibration": 1.0,
            "domain_knowledge": 1.2,
            "education_relevance": 0.9,
            "semantic_similarity": 1.0,
            "voice_alignment": 1.0,
        },
        standout_multipliers={
            "spike_factor": 1.0,
            "trajectory_signal": 1.1,
            "builder_ratio": 1.1,
            "outcome_density": 1.1,
            "narrative_pull": 1.0,
            "uniqueness_index": 1.1,
            "credibility_anchors": 1.0,
            "first_impression": 1.1,
        },
        interview_signals=[
            "Relevant domain experience in the company's vertical",
            "Strong tech stack alignment with practical depth",
            "Track record of shipping features end-to-end",
        ],
        red_flags=[
            "Overqualified with only FAANG-scale experience",
            "No evidence of working in smaller, scrappier teams",
        ],
    ),
}


# ── Aliases for fuzzy matching ────────────────────────────────────────────────

_ALIASES: dict[str, str] = {
    "google": "google",
    "alphabet": "google",
    "deepmind": "google",
    "stripe": "stripe",
    "netflix": "netflix",
    "meta": "meta",
    "facebook": "meta",
    "meta platforms": "meta",
    "apple": "faang_generic",
    "amazon": "faang_generic",
    "microsoft": "faang_generic",
    "faang": "faang_generic",
    "mckinsey": "consulting_firm",
    "bain": "consulting_firm",
    "bcg": "consulting_firm",
    "boston consulting": "consulting_firm",
    "deloitte": "consulting_firm",
    "accenture": "consulting_firm",
}


def _infer_company_type(company_name: str) -> Optional[CompanyProfile]:
    """
    Infer a company type from a free-form company name.

    Checks against known aliases first, then looks for startup signals.
    Returns None if no match — no override applied.
    """
    lower = company_name.lower().strip()

    # Check aliases
    for alias, profile_id in _ALIASES.items():
        if alias in lower:
            return COMPANY_PROFILES[profile_id]

    # Startup signals
    startup_signals = ["startup", "seed", "series a", "pre-seed", "yc ", "y combinator"]
    if any(signal in lower for signal in startup_signals):
        return COMPANY_PROFILES["early_stage_startup"]

    return None


def get_company_profile(company: str) -> Optional[CompanyProfile]:
    """
    Look up a company profile by company name.

    Tries exact ID match first, then _infer_company_type() for fuzzy match.
    Returns None if no matching profile found.
    """
    if not company:
        return None

    # Exact ID match
    if company in COMPANY_PROFILES:
        return COMPANY_PROFILES[company]

    return _infer_company_type(company)


def apply_company_profile(
    weights: dict[str, float],
    profile: CompanyProfile,
    dimension_type: str = "ats",
) -> dict[str, float]:
    """
    Apply a company profile's multipliers on top of existing weights,
    then renormalize to sum 1.0.

    Args:
        weights: Current weights dict (already role + seniority adjusted)
        profile: CompanyProfile with multipliers
        dimension_type: "ats" for ATS dimensions, "standout" for Standout dimensions

    Returns:
        New weights dict renormalized to sum 1.0
    """
    multipliers = (
        profile.ats_multipliers if dimension_type == "ats"
        else profile.standout_multipliers
    )

    adjusted = {}
    for k, v in weights.items():
        mult = multipliers.get(k, 1.0)
        adjusted[k] = v * mult

    total = sum(adjusted.values())
    if total == 0:
        return weights

    return {k: v / total for k, v in adjusted.items()}
