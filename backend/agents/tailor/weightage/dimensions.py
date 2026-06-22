"""All 14 weightage dimensions with descriptions. Scorer functions injected at runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class ScoringDimension:
    id: str
    name: str
    description: str
    max_score: float = 100.0
    scorer_fn: Optional[Callable] = None


DIMENSIONS = {
    "keyword_density": ScoringDimension(
        id="keyword_density",
        name="Keyword Density & Coverage",
        description=(
            "Measures what percentage of the JD's required and preferred keywords "
            "appear in the resume. Scores required keywords 2x preferred. "
            "Penalizes keyword stuffing (same term >4x) by -5 pts per instance. "
            "Uses stemming so 'engineered', 'engineering', 'engineer' all match."
        ),
    ),
    "skill_depth": ScoringDimension(
        id="skill_depth",
        name="Skill Depth & Demonstration",
        description=(
            "Not just presence but PROOF. Does the resume show the skill in context "
            "(a bullet with outcome) vs merely listing it in a skills section? "
            "Skill mentioned in experience section = full credit. "
            "Skill in skills section only = 50% credit. "
            "Skill with quantified outcome = bonus +10."
        ),
    ),
    "tech_stack_alignment": ScoringDimension(
        id="tech_stack_alignment",
        name="Tech Stack Alignment",
        description=(
            "Compares the JD's specific tech stack against resume mentions. "
            "Groups technologies by category and scores category coverage. "
            "Exact match = 100%, category match = 50-70%, no match = 0%."
        ),
    ),
    "experience_relevance": ScoringDimension(
        id="experience_relevance",
        name="Experience Relevance",
        description=(
            "Semantic similarity between each JD requirement and the resume's work "
            "experience bullets. Uses sentence embeddings. "
            "Recency weighted: last 2 years = 1.0x, 2-5 years = 0.8x, 5+ years = 0.5x."
        ),
    ),
    "quantified_impact": ScoringDimension(
        id="quantified_impact",
        name="Quantified Impact",
        description=(
            "Counts measurable outcomes in resume bullets: currency, percentages, "
            "scale metrics, time reductions, team sizes, rankings. "
            "Benchmark against role seniority."
        ),
    ),
    "action_verb_strength": ScoringDimension(
        id="action_verb_strength",
        name="Action Verb Strength",
        description=(
            "Maps all bullet-opening verbs to a strength tier (1-4). "
            "Tier 1: Architected, Spearheaded, Pioneered. "
            "Tier 4: Helped, Assisted, Was responsible for. "
            "Score = weighted average across all bullets."
        ),
    ),
    "section_ordering": ScoringDimension(
        id="section_ordering",
        name="Section Order Relevance",
        description=(
            "Scores whether the resume's actual section sequence matches "
            "the role's optimal sequence. Deduction per misplaced section: -8 pts."
        ),
    ),
    "bullet_quality": ScoringDimension(
        id="bullet_quality",
        name="Bullet Point Quality",
        description=(
            "Scores each bullet on 4 sub-criteria: CAR format (+25), "
            "length 40-120 chars (+25), strong action verb (+25), "
            "contains specific noun (+25)."
        ),
    ),
    "ats_parsability": ScoringDimension(
        id="ats_parsability",
        name="ATS Parsability",
        description=(
            "Structural checks for ATS compatibility: no tables, standard headings, "
            "consistent date formats, no graphics, contact info in top section."
        ),
    ),
    "seniority_calibration": ScoringDimension(
        id="seniority_calibration",
        name="Seniority Level Calibration",
        description=(
            "Checks if the resume's signals match the JD's expected seniority. "
            "Overshoot (too senior) or undershoot (too junior) both penalized."
        ),
    ),
    "domain_knowledge": ScoringDimension(
        id="domain_knowledge",
        name="Domain & Industry Knowledge",
        description=(
            "Measures alignment between the JD's domain context and the resume's "
            "demonstrated domain experience. Checks domain-specific terminology."
        ),
    ),
    "education_relevance": ScoringDimension(
        id="education_relevance",
        name="Education Relevance",
        description=(
            "Evaluated only when the JD specifies education requirements. "
            "Scores degree level match, field relevance, institution tier, "
            "coursework alignment, GPA."
        ),
    ),
    "semantic_similarity": ScoringDimension(
        id="semantic_similarity",
        name="Content Alignment",
        description=(
            "Keyword-overlap proxy measuring how well resume language aligns with JD. "
            "Compares full text, requirements vs experience, and summary vs role description."
        ),
    ),
    "voice_alignment": ScoringDimension(
        id="voice_alignment",
        name="Narrative Voice & Consistency",
        description=(
            "Checks if the resume tells a coherent career story: "
            "visible trajectory, summary matches experience, consistent theme. "
            "Scored by LLM as a narrative coherence judge."
        ),
    ),
}
