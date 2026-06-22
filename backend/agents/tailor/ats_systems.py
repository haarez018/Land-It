"""ATS System-Specific Optimization: profiles for 6 major ATS platforms."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.parsers.schemas import Resume


@dataclass
class ATSProfile:
    name: str
    company_example: str
    parsing_quirks: list[str]
    format_recommendations: list[str]
    header_preferences: dict[str, str]
    date_format: str
    skills_parsing: str
    max_file_size_mb: int
    preferred_format: str
    known_issues: list[str]


ATS_PROFILES: dict[str, ATSProfile] = {
    "greenhouse": ATSProfile(
        name="Greenhouse", company_example="Stripe, Airbnb, GitLab",
        parsing_quirks=["Strips formatting", "Tables parsed row-by-row", "Multi-column layouts break", "Headers/footers ignored"],
        format_recommendations=["Single-column layout", "No tables or text boxes", "Standard section headings", "Bullet points OK"],
        header_preferences={"experience": "Experience", "education": "Education", "skills": "Skills", "summary": "Summary", "projects": "Projects"},
        date_format="Month YYYY", skills_parsing="comma_separated", max_file_size_mb=5, preferred_format="pdf",
        known_issues=["Long URLs truncated", "Special characters sometimes garbled"],
    ),
    "lever": ATSProfile(
        name="Lever", company_example="Netflix, Shopify",
        parsing_quirks=["Excellent PDF parsing", "Two-column OK", "Extracts skills from entire doc", "Creative headings work"],
        format_recommendations=["PDF preferred", "Two-column OK but single safer", "Standard or creative headings both work"],
        header_preferences={"experience": "Professional Experience", "education": "Education", "skills": "Technical Skills", "summary": "About"},
        date_format="Month YYYY", skills_parsing="section_based", max_file_size_mb=10, preferred_format="pdf",
        known_issues=["Very long resumes may timeout"],
    ),
    "workday": ATSProfile(
        name="Workday", company_example="Amazon, Walmart, Target",
        parsing_quirks=["Worst parser of major ATS", "Misidentifies sections", "Dates must be exact format", "Two-column completely breaks"],
        format_recommendations=["MUST use single-column", "Standard section headings exactly", "MM/YYYY date format", "DOCX often better than PDF"],
        header_preferences={"experience": "Work Experience", "education": "Education", "skills": "Skills", "summary": "Professional Summary"},
        date_format="MM/YYYY", skills_parsing="comma_separated", max_file_size_mb=5, preferred_format="docx",
        known_issues=["Bullets parsed as separate lines", "Company/title frequently swapped", "Phone format strict"],
    ),
    "taleo": ATSProfile(
        name="Taleo (Oracle)", company_example="Banks, Government, Enterprise",
        parsing_quirks=["Legacy parser", "Very structured format required", "Keyword matching is literal", "No synonym awareness"],
        format_recommendations=["Plain formatting", "Standard headings/fonts", "Keywords must match JD exactly", "No creative sections"],
        header_preferences={"experience": "Professional Experience", "education": "Education", "skills": "Technical Skills", "summary": "Objective"},
        date_format="MM/YYYY", skills_parsing="one_per_line", max_file_size_mb=2, preferred_format="docx",
        known_issues=["PDF parsing unreliable", "Unicode causes failures"],
    ),
    "icims": ATSProfile(
        name="iCIMS", company_example="Target, UPS, mid-market",
        parsing_quirks=["Moderate quality", "Standard layouts OK", "Creative designs struggle"],
        format_recommendations=["Standard single-column", "PDF or DOCX both work", "Conservative formatting"],
        header_preferences={"experience": "Experience", "education": "Education", "skills": "Skills", "summary": "Summary"},
        date_format="Month YYYY", skills_parsing="comma_separated", max_file_size_mb=5, preferred_format="both",
        known_issues=[],
    ),
    "ashby": ATSProfile(
        name="Ashby", company_example="Notion, Linear, Vercel",
        parsing_quirks=["Modern, excellent parser", "Handles creative layouts", "AI-powered extraction", "Semantic skill extraction"],
        format_recommendations=["Most formats work", "PDF preferred", "Creative formatting OK"],
        header_preferences={"experience": "Experience", "education": "Education", "skills": "Skills", "summary": "About Me"},
        date_format="Month YYYY", skills_parsing="section_based", max_file_size_mb=10, preferred_format="pdf",
        known_issues=[],
    ),
}

COMPANY_ATS_MAP: dict[str, str] = {
    "stripe": "greenhouse", "airbnb": "greenhouse", "gitlab": "greenhouse",
    "figma": "greenhouse", "notion": "greenhouse", "datadog": "greenhouse",
    "cloudflare": "greenhouse", "plaid": "greenhouse", "brex": "greenhouse",
    "coinbase": "greenhouse", "instacart": "greenhouse", "doordash": "greenhouse",
    "netflix": "lever", "shopify": "lever", "twitch": "lever",
    "amazon": "workday", "walmart": "workday", "target": "workday",
    "jpmorgan": "workday", "bank of america": "workday", "deloitte": "workday",
    "pwc": "workday", "accenture": "workday", "microsoft": "workday",
    "oracle": "taleo", "ibm": "taleo",
    "ups": "icims",
    "vercel": "ashby", "linear": "ashby", "ramp": "ashby",
}


def get_ats_for_company(company: str) -> ATSProfile | None:
    key = COMPANY_ATS_MAP.get(company.lower().strip())
    return ATS_PROFILES.get(key) if key else None


def get_ats_recommendations(resume: Resume, company: str) -> dict:
    profile = get_ats_for_company(company)
    if not profile:
        return {"ats_detected": None, "recommendations": ["Unknown ATS — use conservative formatting"]}

    recommendations: list[str] = list(profile.format_recommendations)

    # Check date format
    has_mm_yyyy = bool(re.search(r"\d{1,2}/\d{4}", resume.raw_text))
    has_month_yyyy = bool(re.search(r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}", resume.raw_text))
    if profile.date_format == "MM/YYYY" and has_month_yyyy and not has_mm_yyyy:
        recommendations.append(f"Switch to {profile.date_format} date format for {profile.name}")
    elif profile.date_format == "Month YYYY" and has_mm_yyyy and not has_month_yyyy:
        recommendations.append(f"Switch to {profile.date_format} date format for {profile.name}")

    return {
        "ats_detected": profile.name,
        "company_examples": profile.company_example,
        "recommendations": recommendations,
        "format_recommendation": profile.preferred_format,
        "known_issues": profile.known_issues,
        "header_preferences": profile.header_preferences,
    }
