"""
Salary Intelligence Module.

Heuristic salary estimator using base ranges, location multipliers,
company-stage multipliers, and skill premiums. No external APIs required —
pure arithmetic calibrated from 2024-2025 market data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from backend.parsers.schemas import Resume, JobDescription


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class SalaryEstimate:
    role_type: str
    seniority: str
    location: str
    company: str
    estimated_range: tuple[int, int]       # (low, high) USD/year
    estimated_midpoint: int
    user_position_in_range: str            # "below_mid" | "at_mid" | "above_mid"
    user_estimated_value: int
    premium_factors: list[str]             # "FAANG experience: +15%"
    discount_factors: list[str]            # "No cloud certs: -5%"
    negotiation_leverage: list[str]        # from Standout spike + credibility
    negotiation_talking_points: list[str]  # specific resume bullets to reference
    confidence: str                        # "high" | "medium" | "low"
    confidence_reason: str


# ── Base salary ranges (USD/year, 2024-2025 market averages) ──────────────

BASE_SALARY_RANGES: dict[tuple[str, str], tuple[int, int]] = {
    # software_engineer_backend
    ("software_engineer_backend", "junior"):          (85_000, 130_000),
    ("software_engineer_backend", "mid"):             (120_000, 175_000),
    ("software_engineer_backend", "senior"):          (160_000, 240_000),
    ("software_engineer_backend", "staff_principal"):  (220_000, 350_000),
    # software_engineer_frontend
    ("software_engineer_frontend", "junior"):          (80_000, 125_000),
    ("software_engineer_frontend", "mid"):             (115_000, 170_000),
    ("software_engineer_frontend", "senior"):          (155_000, 230_000),
    # ml_engineer
    ("ml_engineer", "junior"):                         (95_000, 145_000),
    ("ml_engineer", "mid"):                            (135_000, 200_000),
    ("ml_engineer", "senior"):                         (180_000, 280_000),
    ("ml_engineer", "staff_principal"):                (250_000, 400_000),
    # data_scientist
    ("data_scientist", "junior"):                      (80_000, 120_000),
    ("data_scientist", "mid"):                         (110_000, 165_000),
    ("data_scientist", "senior"):                      (150_000, 230_000),
    # product_manager
    ("product_manager", "mid"):                        (110_000, 165_000),
    ("product_manager", "senior"):                     (150_000, 230_000),
    ("product_manager", "staff_principal"):             (200_000, 320_000),
    # devops_sre
    ("devops_sre", "junior"):                          (85_000, 130_000),
    ("devops_sre", "mid"):                             (120_000, 180_000),
    ("devops_sre", "senior"):                          (165_000, 250_000),
    # design_ux
    ("design_ux", "mid"):                              (100_000, 150_000),
    ("design_ux", "senior"):                           (140_000, 210_000),
    # research_scientist
    ("research_scientist", "mid"):                     (120_000, 180_000),
    ("research_scientist", "senior"):                  (170_000, 270_000),
}

# ── Location multipliers ─────────────────────────────────────────────────────

LOCATION_MULTIPLIERS: dict[str, float] = {
    "san_francisco": 1.35,
    "new_york": 1.25,
    "seattle": 1.20,
    "los_angeles": 1.15,
    "boston": 1.15,
    "austin": 1.05,
    "denver": 1.00,
    "chicago": 1.05,
    "remote_us": 1.10,
    "london": 0.90,
    "berlin": 0.75,
    "toronto": 0.85,
    "bangalore": 0.35,
    "chennai": 0.30,
    "hyderabad": 0.32,
    "singapore": 0.95,
    "tokyo": 0.85,
    "sydney": 0.90,
    "default": 1.00,
}

# Fuzzy location aliases for matching free-form location strings
_LOCATION_ALIASES: dict[str, str] = {
    # San Francisco / Bay Area
    "san francisco": "san_francisco", "sf": "san_francisco", "bay area": "san_francisco",
    "palo alto": "san_francisco", "mountain view": "san_francisco", "menlo park": "san_francisco",
    "sunnyvale": "san_francisco", "cupertino": "san_francisco", "san jose": "san_francisco",
    "silicon valley": "san_francisco", "south bay": "san_francisco", "san mateo": "san_francisco",
    "redwood city": "san_francisco", "santa clara": "san_francisco", "oakland": "san_francisco",
    "berkeley": "san_francisco", "fremont": "san_francisco",
    # New York
    "new york": "new_york", "nyc": "new_york", "manhattan": "new_york", "brooklyn": "new_york",
    "new york city": "new_york", "queens": "new_york", "jersey city": "new_york",
    "hoboken": "new_york",
    # Seattle
    "seattle": "seattle", "bellevue": "seattle", "redmond": "seattle", "kirkland": "seattle",
    # Los Angeles
    "los angeles": "los_angeles", "la": "los_angeles", "santa monica": "los_angeles",
    "venice": "los_angeles", "culver city": "los_angeles", "pasadena": "los_angeles",
    "west hollywood": "los_angeles",
    # Boston
    "boston": "boston", "cambridge": "boston", "somerville": "boston",
    # Austin
    "austin": "austin", "round rock": "austin",
    # Denver
    "denver": "denver", "boulder": "denver",
    # Chicago
    "chicago": "chicago", "evanston": "chicago",
    # Remote
    "remote": "remote_us", "remote (us)": "remote_us", "us remote": "remote_us",
    "anywhere in the us": "remote_us", "united states (remote)": "remote_us",
    "remote - us": "remote_us",
    # International
    "london": "london", "city of london": "london",
    "berlin": "berlin", "munich": "berlin", "münchen": "berlin", "germany": "berlin",
    "toronto": "toronto", "vancouver": "toronto", "canada": "toronto", "waterloo": "toronto",
    "bangalore": "bangalore", "bengaluru": "bangalore", "bangalore, india": "bangalore",
    "bengaluru, india": "bangalore", "karnataka": "bangalore",
    "chennai": "chennai", "chennai, india": "chennai", "tamil nadu": "chennai",
    "hyderabad": "hyderabad", "hyderabad, india": "hyderabad", "telangana": "hyderabad",
    "singapore": "singapore",
    "tokyo": "tokyo", "japan": "tokyo",
    "sydney": "sydney", "melbourne": "sydney", "australia": "sydney",
}


def _match_location(location: str) -> str:
    """Fuzzy-match a free-form location string to a location key."""
    if not location:
        return "default"
    lower = location.lower().strip()

    # Direct key match
    if lower in LOCATION_MULTIPLIERS:
        return lower

    # Alias match
    for alias, key in _LOCATION_ALIASES.items():
        if alias in lower:
            return key

    return "default"


# ── Company stage multipliers ────────────────────────────────────────────────

COMPANY_STAGE_MULTIPLIERS: dict[str, float] = {
    "faang": 1.30,
    "unicorn": 1.15,
    "series_c_plus": 1.05,
    "series_a_b": 0.90,
    "seed": 0.75,
    "enterprise": 1.00,
    "consulting": 0.95,
    "default": 1.00,
}

_FAANG_NAMES = {
    "google", "alphabet", "meta", "facebook", "apple", "amazon", "microsoft",
    "netflix", "stripe", "airbnb", "uber", "linkedin", "salesforce", "nvidia",
    "openai", "anthropic", "deepmind", "databricks", "snowflake",
}

_UNICORN_SIGNALS = {"unicorn", "series d", "series e", "series f", "ipo", "pre-ipo"}
_STARTUP_SIGNALS = {"seed", "series a", "series b", "pre-seed", "early stage", "yc", "y combinator"}
_CONSULTING_NAMES = {"mckinsey", "bain", "bcg", "deloitte", "accenture", "boston consulting"}


def _infer_company_stage(company: str) -> str:
    """Infer company stage from company name."""
    if not company:
        return "default"
    lower = company.lower().strip()

    for name in _FAANG_NAMES:
        if name in lower:
            return "faang"

    for name in _CONSULTING_NAMES:
        if name in lower:
            return "consulting"

    for signal in _UNICORN_SIGNALS:
        if signal in lower:
            return "unicorn"

    for signal in _STARTUP_SIGNALS:
        if signal in lower:
            return "seed"

    return "default"


# ── Skill premiums ───────────────────────────────────────────────────────────

SKILL_PREMIUMS: dict[str, float] = {
    "rust": 0.08,
    "go": 0.05,
    "kubernetes": 0.06,
    "k8s": 0.06,
    "ml_ops": 0.07,
    "mlops": 0.07,
    "distributed_systems": 0.08,
    "distributed systems": 0.08,
    "security": 0.07,
    "cybersecurity": 0.07,
    "blockchain": 0.05,
    "ai": 0.10,
    "machine learning": 0.10,
    "deep learning": 0.10,
    "tensorflow": 0.06,
    "pytorch": 0.06,
    "system_design": 0.06,
    "system design": 0.06,
    "staff_plus_leadership": 0.12,
    "kafka": 0.04,
    "aws": 0.03,
    "gcp": 0.03,
}

# ── Tier 1 companies (for experience premium) ────────────────────────────────

_TIER1_COMPANIES = {
    "google", "meta", "facebook", "apple", "amazon", "microsoft", "netflix",
    "stripe", "airbnb", "uber", "linkedin", "salesforce", "nvidia",
    "openai", "anthropic", "deepmind", "databricks", "snowflake", "palantir",
    "coinbase", "figma", "notion", "vercel", "twilio",
}


# ── Main estimation function ─────────────────────────────────────────────────

def estimate_salary(
    resume: Resume,
    jd: JobDescription,
    standout_result=None,
) -> SalaryEstimate:
    """
    Estimate salary range and user's position within it.

    Algorithm:
      1. Base range from (role_type, seniority)
      2. Apply location multiplier
      3. Apply company stage multiplier
      4. Compute premium/discount factors from resume
      5. User estimated value = midpoint * (1 + net_premium)
      6. Position in range
      7. Negotiation leverage from standout
      8. Confidence assessment
    """
    # Step 1: Base range
    role_type = jd.infer_role_type()
    seniority = resume.seniority_level
    base_key = (role_type, seniority)

    if base_key not in BASE_SALARY_RANGES:
        # Fallback: try just the role with "mid"
        fallback_key = (role_type, "mid")
        if fallback_key in BASE_SALARY_RANGES:
            base_key = fallback_key
        else:
            base_key = ("software_engineer_backend", "mid")

    base_low, base_high = BASE_SALARY_RANGES[base_key]

    # Step 2: Location multiplier
    location_key = _match_location(jd.location)
    location_mult = LOCATION_MULTIPLIERS.get(location_key, 1.0)

    # Step 3: Company stage multiplier
    company_stage = _infer_company_stage(jd.company)
    stage_mult = COMPANY_STAGE_MULTIPLIERS.get(company_stage, 1.0)

    # Apply multipliers to range
    adj_low = int(base_low * location_mult * stage_mult)
    adj_high = int(base_high * location_mult * stage_mult)
    midpoint = (adj_low + adj_high) // 2

    # Step 4: Premium / discount factors
    premiums: list[str] = []
    discounts: list[str] = []
    net_premium = 0.0

    # 4a: Skill premiums
    all_skills_lower: set[str] = set()
    for category, skills_list in resume.skills.items():
        for s in skills_list:
            all_skills_lower.add(s.lower())
    # Also scan tech from work experience
    for exp in resume.work_experience:
        for tech in exp.technologies:
            all_skills_lower.add(tech.lower())

    skill_premium_total = 0.0
    matched_skills: list[str] = []
    for skill_key, premium_pct in SKILL_PREMIUMS.items():
        if skill_key in all_skills_lower:
            if skill_key not in matched_skills:
                matched_skills.append(skill_key)
                skill_premium_total += premium_pct
    # Cap skill premium at 25%
    skill_premium_total = min(skill_premium_total, 0.25)
    if skill_premium_total > 0:
        premiums.append(f"In-demand skills ({', '.join(matched_skills[:4])}): +{skill_premium_total:.0%}")
        net_premium += skill_premium_total

    # 4b: YoE vs seniority expectation
    _YOE_EXPECTATIONS = {
        "intern": 0, "junior": 1, "mid": 3, "senior": 6,
        "staff_principal": 10, "executive": 15,
    }
    expected_yoe = _YOE_EXPECTATIONS.get(seniority, 3)
    yoe_delta = resume.total_yoe - expected_yoe
    if yoe_delta >= 3:
        pct = min(yoe_delta * 0.02, 0.10)
        premiums.append(f"{resume.total_yoe:.0f} YoE ({yoe_delta:.0f}+ above level): +{pct:.0%}")
        net_premium += pct
    elif yoe_delta <= -2:
        pct = min(abs(yoe_delta) * 0.03, 0.12)
        discounts.append(f"Under-experienced for {seniority} level: -{pct:.0%}")
        net_premium -= pct

    # 4c: Tier 1 company experience
    has_tier1 = any(
        exp.company.lower() in _TIER1_COMPANIES
        for exp in resume.work_experience
    )
    if has_tier1:
        tier1_names = [
            exp.company for exp in resume.work_experience
            if exp.company.lower() in _TIER1_COMPANIES
        ]
        premiums.append(f"Tier 1 experience ({', '.join(tier1_names[:2])}): +15%")
        net_premium += 0.15

    # 4d: Career gaps
    gaps = _detect_career_gaps(resume)
    if gaps > 12:
        pct = min(gaps / 12 * 0.05, 0.12)
        discounts.append(f"Career gap ({gaps} months): -{pct:.0%}")
        net_premium -= pct
    elif gaps > 6:
        discounts.append(f"Short career gap ({gaps} months): -3%")
        net_premium -= 0.03

    # 4e: Education premium for research roles
    if role_type == "research_scientist":
        has_phd = any("phd" in e.degree.lower() or "ph.d" in e.degree.lower() for e in resume.education)
        if has_phd:
            premiums.append("PhD for research role: +10%")
            net_premium += 0.10
        elif any("master" in e.degree.lower() or "ms " in e.degree.lower() for e in resume.education):
            premiums.append("Master's for research role: +5%")
            net_premium += 0.05

    # 4f: Location premium note (informational)
    if location_mult != 1.0:
        direction = "adds" if location_mult > 1.0 else "reduces"
        pct_change = abs(location_mult - 1.0)
        premiums.append(f"Location ({location_key.replace('_', ' ').title()}) {direction} {pct_change:.0%} to base")

    # Step 5: User estimated value
    user_value = int(midpoint * (1 + net_premium))
    user_value = max(adj_low, min(user_value, int(adj_high * 1.15)))  # Cap within 115% of high

    # Step 6: Position in range
    if user_value < midpoint - (midpoint - adj_low) * 0.15:
        position = "below_mid"
    elif user_value > midpoint + (adj_high - midpoint) * 0.15:
        position = "above_mid"
    else:
        position = "at_mid"

    # Step 7: Negotiation leverage from standout
    negotiation_leverage: list[str] = []
    negotiation_talking_points: list[str] = []

    if standout_result is not None:
        # Extract spike info
        for dim in standout_result.dimension_scores:
            if dim.dimension_id == "spike_factor" and dim.raw_score >= 50:
                negotiation_leverage.append(
                    f"Your spike ({dim.explanation}) is rare at this level"
                )
            if dim.dimension_id == "credibility_anchors" and dim.raw_score >= 60:
                negotiation_leverage.append(
                    f"Strong credibility anchors ({dim.explanation}) give you leverage"
                )
            if dim.dimension_id == "outcome_density" and dim.raw_score >= 70:
                negotiation_leverage.append(
                    "High outcome density — every bullet proves value"
                )

    # Extract best bullets as talking points
    _METRIC_RE = re.compile(r"\$[\d,]+[KMBkmb]?|\d+[%]|\d+[xX]\b|\d+[KMBkmb]\+?\b")
    for exp in resume.work_experience[:2]:
        for bullet in exp.bullets[:3]:
            if _METRIC_RE.search(bullet):
                negotiation_talking_points.append(
                    f"Reference: \"{bullet[:100]}\" — quantified impact is compelling"
                )
                if len(negotiation_talking_points) >= 3:
                    break
        if len(negotiation_talking_points) >= 3:
            break

    if has_tier1:
        negotiation_leverage.append(
            "Tier 1 company experience gives strong positioning in negotiations"
        )

    # Step 8: Confidence
    if jd.salary_range:
        confidence = "high"
        confidence_reason = "JD includes a salary range — estimate can be validated"
    elif jd.company and location_key != "default":
        confidence = "medium"
        confidence_reason = f"Known company ({jd.company}) and location ({location_key}) — reasonable estimate"
    else:
        confidence = "low"
        confidence_reason = "Unknown company or location — estimate is approximate"

    return SalaryEstimate(
        role_type=role_type,
        seniority=seniority,
        location=location_key,
        company=jd.company,
        estimated_range=(adj_low, adj_high),
        estimated_midpoint=midpoint,
        user_position_in_range=position,
        user_estimated_value=user_value,
        premium_factors=premiums,
        discount_factors=discounts,
        negotiation_leverage=negotiation_leverage,
        negotiation_talking_points=negotiation_talking_points,
        confidence=confidence,
        confidence_reason=confidence_reason,
    )


def _detect_career_gaps(resume: Resume) -> int:
    """Detect career gaps in months. Returns the longest gap."""
    if len(resume.work_experience) < 2:
        return 0

    # Sort experiences by start_date descending (most recent first)
    sorted_exp = sorted(
        resume.work_experience,
        key=lambda e: e.start_date,
        reverse=True,
    )

    max_gap = 0
    for i in range(len(sorted_exp) - 1):
        current_start = sorted_exp[i].start_date
        prev_end = sorted_exp[i + 1].end_date or date.today()
        gap_days = (current_start - prev_end).days
        if gap_days > 0:
            gap_months = gap_days // 30
            max_gap = max(max_gap, gap_months)

    return max_gap
