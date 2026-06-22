"""
Job-profile fit scoring: reverse ATS engine that scores JD against user profile.

Evaluates how well a job matches the candidate across 8 dimensions:
  1. Skill match (required + preferred)
  2. Tech stack alignment
  3. Seniority fit
  4. Experience years match
  5. Domain overlap
  6. Location / remote preference
  7. Role type alignment
  8. Culture/values alignment

Returns a 0-100 fit score with dimension breakdown.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Optional

from backend.parsers.schemas import Resume, JobDescription


@dataclass
class FitDimension:
    """Score for a single fit dimension."""
    name: str
    score: float  # 0-100
    weight: float
    weighted_score: float
    explanation: str


@dataclass
class FitResult:
    """Complete fit score result."""
    total_score: float
    dimensions: list[FitDimension]
    match_summary: str
    strengths: list[str]
    gaps: list[str]
    dealbreakers: list[str]


# ── Dimension scorers ──────────────────────────────────────────────────────


def _score_skill_match(resume: Resume, jd: JobDescription) -> tuple[float, str, list[str], list[str]]:
    """Score required + preferred skill match."""
    resume_skills_lower = set()
    for category_skills in resume.skills.values():
        for s in category_skills:
            resume_skills_lower.add(s.lower())
    # Also add technologies from work experience
    for exp in resume.work_experience:
        for t in exp.technologies:
            resume_skills_lower.add(t.lower())

    # Required skills
    required = [s.lower() for s in jd.required_skills]
    required_matches = [s for s in required if s in resume_skills_lower]
    required_pct = len(required_matches) / max(len(required), 1)

    # Preferred skills
    preferred = [s.lower() for s in jd.preferred_skills]
    preferred_matches = [s for s in preferred if s in resume_skills_lower]
    preferred_pct = len(preferred_matches) / max(len(preferred), 1)

    # Weight: 70% required, 30% preferred
    score = (required_pct * 70 + preferred_pct * 30)

    strengths = [f"Matches {len(required_matches)}/{len(required)} required skills"]
    gaps = [f"Missing: {s}" for s in required if s not in resume_skills_lower]

    explanation = f"Required: {len(required_matches)}/{len(required)}, Preferred: {len(preferred_matches)}/{len(preferred)}"
    return score, explanation, strengths[:2], gaps[:3]


def _score_tech_stack(resume: Resume, jd: JobDescription) -> tuple[float, str]:
    """Score tech stack alignment."""
    resume_tech = set()
    for category_skills in resume.skills.values():
        for s in category_skills:
            resume_tech.add(s.lower())
    for exp in resume.work_experience:
        for t in exp.technologies:
            resume_tech.add(t.lower())

    jd_tech = [t.lower() for t in jd.tech_stack]
    if not jd_tech:
        return 70.0, "No tech stack specified in JD"

    matches = [t for t in jd_tech if t in resume_tech]
    pct = len(matches) / len(jd_tech)

    score = pct * 100
    explanation = f"{len(matches)}/{len(jd_tech)} stack technologies match"
    return score, explanation


def _score_seniority_fit(resume: Resume, jd: JobDescription) -> tuple[float, str, list[str]]:
    """Score seniority level alignment."""
    level_order = {
        "intern": 0, "junior": 1, "mid": 2, "senior": 3,
        "staff": 4, "principal": 5, "lead": 3, "manager": 4,
        "director": 5, "vp": 6,
    }
    resume_level = level_order.get(resume.seniority_level.lower(), 2)
    jd_level = level_order.get(jd.seniority_level.lower(), 2)

    diff = abs(resume_level - jd_level)
    dealbreakers: list[str] = []

    if diff == 0:
        score = 100.0
        explanation = f"Perfect seniority match: {jd.seniority_level}"
    elif diff == 1:
        score = 75.0
        explanation = f"Close seniority fit: you're {resume.seniority_level}, role is {jd.seniority_level}"
    elif diff == 2:
        score = 40.0
        explanation = f"Seniority gap: you're {resume.seniority_level}, role is {jd.seniority_level}"
    else:
        score = 10.0
        explanation = f"Large seniority mismatch: you're {resume.seniority_level}, role is {jd.seniority_level}"
        dealbreakers.append(f"Seniority gap too large ({resume.seniority_level} vs {jd.seniority_level})")

    return score, explanation, dealbreakers


def _score_experience_years(resume: Resume, jd: JobDescription) -> tuple[float, str, list[str]]:
    """Score experience years match."""
    if jd.required_experience_years is None:
        return 70.0, "No experience requirement specified", []

    required = jd.required_experience_years
    actual = resume.total_yoe
    dealbreakers: list[str] = []

    if actual >= required:
        over = actual - required
        if over <= 3:
            score = 100.0
        elif over <= 6:
            score = 85.0  # Slightly overqualified
        else:
            score = 60.0  # Significantly overqualified
        explanation = f"{actual:.1f} YoE vs {required} required"
    else:
        shortfall = required - actual
        if shortfall <= 1:
            score = 70.0
            explanation = f"Slightly under: {actual:.1f} YoE vs {required} required"
        elif shortfall <= 3:
            score = 40.0
            explanation = f"Under-experienced: {actual:.1f} YoE vs {required} required"
        else:
            score = 10.0
            explanation = f"Significant gap: {actual:.1f} YoE vs {required} required"
            dealbreakers.append(f"Need {required} years, have {actual:.1f}")

    return score, explanation, dealbreakers


def _score_domain_overlap(resume: Resume, jd: JobDescription) -> tuple[float, str]:
    """Score domain/industry knowledge overlap."""
    resume_domain = resume.primary_domain.lower()
    jd_domains = [d.lower() for d in jd.domain_knowledge]

    if not jd_domains:
        # Infer from title
        title_lower = jd.title.lower()
        if "fintech" in title_lower or "payment" in title_lower:
            jd_domains = ["fintech"]
        elif "health" in title_lower:
            jd_domains = ["healthcare"]
        elif "e-commerce" in title_lower or "retail" in title_lower:
            jd_domains = ["e-commerce"]

    if not jd_domains:
        return 60.0, "No specific domain required"

    if resume_domain in jd_domains or any(resume_domain in d for d in jd_domains):
        return 90.0, f"Strong domain match: {resume_domain}"
    elif resume_domain == "general":
        return 50.0, "General background — no specific domain match"
    else:
        return 30.0, f"Domain mismatch: your {resume_domain} vs required {', '.join(jd_domains)}"


def _score_location_fit(resume: Resume, jd: JobDescription) -> tuple[float, str]:
    """Score location and remote policy fit."""
    remote = jd.remote_policy.lower()

    if remote in ("remote", "fully_remote"):
        return 100.0, "Fully remote — location flexible"

    if remote == "hybrid":
        return 80.0, "Hybrid — some in-office required"

    # Onsite — check location match
    resume_loc = (resume.contact.location or "").lower()
    jd_loc = jd.location.lower()

    if not jd_loc or not resume_loc:
        return 60.0, "Location unclear"

    # Simple city match
    resume_cities = set(re.findall(r"\b\w{3,}\b", resume_loc))
    jd_cities = set(re.findall(r"\b\w{3,}\b", jd_loc))

    if resume_cities & jd_cities:
        return 90.0, f"Location match: {jd.location}"
    else:
        return 30.0, f"Location mismatch: you're in {resume.contact.location}, role in {jd.location}"


def _score_role_type(resume: Resume, jd: JobDescription) -> tuple[float, str]:
    """Score role type alignment (backend, frontend, fullstack, etc.)."""
    # Infer resume role type from skills and experience
    resume_text = " ".join(
        s.lower() for skills in resume.skills.values() for s in skills
    )
    for exp in resume.work_experience:
        resume_text += " " + exp.title.lower()

    jd_role_raw = jd.infer_role_type().lower()

    # Normalize JD role to our simplified categories
    _ROLE_NORMALIZE = {
        "software_engineer_backend": "backend",
        "software_engineer_frontend": "frontend",
        "product_manager": "product_manager",
        "data_scientist": "data_scientist",
        "ml_engineer": "ml_engineer",
        "devops_sre": "devops_sre",
        "research_scientist": "research_scientist",
        "design_ux": "design_ux",
    }
    jd_role = _ROLE_NORMALIZE.get(jd_role_raw, jd_role_raw)

    # Simple heuristic
    role_keywords = {
        "backend": ["backend", "api", "server", "database", "microservice", "python", "go", "java", "node"],
        "frontend": ["frontend", "react", "vue", "angular", "css", "javascript", "typescript", "ui"],
        "fullstack": ["fullstack", "full-stack", "full stack"],
        "data_scientist": ["machine learning", "data science", "statistics", "pandas", "scikit"],
        "ml_engineer": ["tensorflow", "pytorch", "model", "ml", "deep learning"],
        "devops_sre": ["devops", "kubernetes", "docker", "terraform", "ci/cd", "infrastructure"],
    }

    resume_roles: set[str] = set()
    for role, keywords in role_keywords.items():
        if any(kw in resume_text for kw in keywords):
            resume_roles.add(role)

    if jd_role in resume_roles:
        return 90.0, f"Role type match: {jd_role}"
    elif "fullstack" in resume_roles:
        return 75.0, "Fullstack background — adaptable to role"
    elif resume_roles:
        return 40.0, f"Role type gap: your focus is {', '.join(resume_roles)}, role is {jd_role}"
    else:
        return 50.0, "Unable to determine role type alignment"


def _score_culture_fit(resume: Resume, jd: JobDescription) -> tuple[float, str]:
    """Score culture/values alignment (limited without more user data)."""
    if not jd.company_values:
        return 60.0, "No company values specified"

    # Basic heuristic — we can't deeply evaluate culture fit without user preferences
    # But we can check if the resume shows relevant signals
    resume_text = resume.raw_text.lower()
    matches = 0
    for value in jd.company_values[:5]:
        value_keywords = set(re.findall(r"\b\w{4,}\b", value.lower()))
        if any(kw in resume_text for kw in value_keywords):
            matches += 1

    pct = matches / max(len(jd.company_values[:5]), 1)
    score = 40 + pct * 60  # Base 40, up to 100

    return score, f"Culture signals: {matches}/{min(len(jd.company_values), 5)} values aligned"


# ── Main scorer ────────────────────────────────────────────────────────────

# Dimension weights (must sum to 1.0)
_WEIGHTS = {
    "Skill Match": 0.25,
    "Tech Stack": 0.15,
    "Seniority": 0.15,
    "Experience": 0.10,
    "Domain": 0.10,
    "Location": 0.10,
    "Role Type": 0.10,
    "Culture": 0.05,
}


def score_fit(resume: Resume, jd: JobDescription) -> FitResult:
    """
    Score how well a job matches the candidate profile.

    Args:
        resume: Candidate's parsed resume
        jd: Target job description

    Returns:
        FitResult with total score, dimension breakdown, and analysis
    """
    all_strengths: list[str] = []
    all_gaps: list[str] = []
    all_dealbreakers: list[str] = []

    # Score each dimension
    skill_score, skill_expl, skill_strengths, skill_gaps = _score_skill_match(resume, jd)
    all_strengths.extend(skill_strengths)
    all_gaps.extend(skill_gaps)

    tech_score, tech_expl = _score_tech_stack(resume, jd)
    seniority_score, seniority_expl, seniority_db = _score_seniority_fit(resume, jd)
    all_dealbreakers.extend(seniority_db)

    exp_score, exp_expl, exp_db = _score_experience_years(resume, jd)
    all_dealbreakers.extend(exp_db)

    domain_score, domain_expl = _score_domain_overlap(resume, jd)
    location_score, location_expl = _score_location_fit(resume, jd)
    role_score, role_expl = _score_role_type(resume, jd)
    culture_score, culture_expl = _score_culture_fit(resume, jd)

    # Build dimensions
    scores = {
        "Skill Match": (skill_score, skill_expl),
        "Tech Stack": (tech_score, tech_expl),
        "Seniority": (seniority_score, seniority_expl),
        "Experience": (exp_score, exp_expl),
        "Domain": (domain_score, domain_expl),
        "Location": (location_score, location_expl),
        "Role Type": (role_score, role_expl),
        "Culture": (culture_score, culture_expl),
    }

    dimensions: list[FitDimension] = []
    total = 0.0
    for name, (score, expl) in scores.items():
        weight = _WEIGHTS[name]
        weighted = score * weight
        total += weighted
        dimensions.append(FitDimension(
            name=name,
            score=round(score, 1),
            weight=weight,
            weighted_score=round(weighted, 1),
            explanation=expl,
        ))

    total = round(total, 1)

    # Strengths from high-scoring dimensions
    for dim in dimensions:
        if dim.score >= 80 and dim.name not in ("Culture",):
            all_strengths.append(f"{dim.name}: {dim.explanation}")

    # Gaps from low-scoring dimensions
    for dim in dimensions:
        if dim.score < 50 and dim.name not in ("Culture",):
            all_gaps.append(f"{dim.name}: {dim.explanation}")

    # Summary
    if total >= 80:
        summary = "Excellent fit — this role aligns strongly with your profile."
    elif total >= 65:
        summary = "Good fit — most dimensions align, with a few areas to address."
    elif total >= 50:
        summary = "Moderate fit — notable gaps exist but the role could still be a good stretch."
    else:
        summary = "Weak fit — significant mismatches in key areas."

    if all_dealbreakers:
        summary += f" Dealbreakers: {'; '.join(all_dealbreakers)}"

    return FitResult(
        total_score=total,
        dimensions=dimensions,
        match_summary=summary,
        strengths=list(dict.fromkeys(all_strengths))[:5],
        gaps=list(dict.fromkeys(all_gaps))[:5],
        dealbreakers=all_dealbreakers,
    )


async def score_fit_ai(resume: Resume, jd: JobDescription) -> FitResult:
    """
    Enhanced fit scorer: heuristic dimension scores enriched with Claude narrative.
    Falls back to pure heuristic if Claude is unavailable.
    """
    result = score_fit(resume, jd)
    try:
        return await _enrich_with_claude(resume, jd, result)
    except Exception:
        return result


async def _enrich_with_claude(resume: Resume, jd: JobDescription, result: FitResult) -> FitResult:
    """Ask Claude to generate a contextual match summary and insight-driven strengths/gaps."""
    from backend.agents.llm import ask_json

    system = """You are an expert career advisor analyzing how well a candidate matches a job.

Write insightful, specific analysis — not generic advice. Think like a recruiter who understands both the candidate and the role deeply.

Respond with JSON only:
{
  "match_summary": "2-3 sentences explaining the fit — specific to THIS candidate and THIS role, never a generic template",
  "strengths": ["specific strength with context", "specific strength 2", "specific strength 3"],
  "gaps": ["specific gap with context", "gap 2"],
  "quick_win": "One actionable thing the candidate can emphasize to close the gap"
}

Rules:
- match_summary must reference actual skills, titles, and company names from the data
- Be honest: if fit is low (<50), say so constructively; if high (>70), explain specifically WHY
- Strengths/gaps must be grounded in the data provided — no invented observations
- Maximum 3 strengths, 3 gaps"""

    score_breakdown = "\n".join(
        f"- {d.name}: {d.score:.0f}/100 ({d.explanation})"
        for d in result.dimensions
    )

    resume_skills: list[str] = []
    for skills_list in resume.skills.values():
        resume_skills.extend(skills_list)

    recent_role = ""
    if resume.work_experience:
        exp = resume.work_experience[0]
        recent_role = f"{exp.title} at {exp.company}"

    user = f"""CANDIDATE:
Name: {resume.contact.name or 'Candidate'}
Seniority: {resume.seniority_level} | {resume.total_yoe:.1f} years experience
Most recent role: {recent_role or 'N/A'}
Primary domain: {resume.primary_domain}
Key skills: {', '.join(resume_skills[:15])}

TARGET JOB:
Role: {jd.title or 'Unknown Role'} at {jd.company or 'Unknown Company'}
Location: {jd.location or 'Not specified'} ({jd.remote_policy or 'unknown remote policy'})
Seniority required: {jd.seniority_level or 'Not specified'}
Required skills: {', '.join(jd.required_skills[:10])}
Tech stack: {', '.join(jd.tech_stack[:8])}

DIMENSION SCORES (heuristic — use as ground truth, add narrative):
Overall: {result.total_score:.0f}/100
{score_breakdown}"""

    data = await ask_json(system, user, model="claude-haiku-4-5-20251001", max_tokens=600)

    enriched = copy.deepcopy(result)
    if isinstance(data, dict):
        if data.get("match_summary"):
            enriched.match_summary = data["match_summary"]
        if data.get("strengths"):
            enriched.strengths = [s for s in data["strengths"] if s][:3]
        if data.get("gaps"):
            enriched.gaps = [g for g in data["gaps"] if g][:3]

    return enriched
