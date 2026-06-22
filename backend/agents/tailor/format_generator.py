"""Multi-Format Resume Generator: same resume in 5 different formats."""

from __future__ import annotations

from dataclasses import dataclass

from backend.parsers.schemas import Resume, JobDescription


@dataclass
class FormattedResume:
    format_type: str
    format_name: str
    content: str
    word_count: int
    sections: list[str]


RESUME_FORMATS: dict[str, dict] = {
    "standard_pdf": {
        "name": "Standard PDF",
        "use_case": "Job applications via ATS",
        "sections": ["contact", "summary", "experience", "skills", "education", "projects"],
        "max_pages": 2,
    },
    "linkedin_optimized": {
        "name": "LinkedIn Profile",
        "use_case": "LinkedIn About + Experience",
        "sections": ["headline", "about", "experience", "skills"],
        "max_chars_about": 2600,
    },
    "one_page_summary": {
        "name": "One-Page Executive Summary",
        "use_case": "Networking events, quick shares",
        "sections": ["contact", "headline", "top_3_achievements", "key_skills"],
        "max_pages": 1,
    },
    "technical_cv": {
        "name": "Technical CV",
        "use_case": "Research, academic, technical deep-dive",
        "sections": ["contact", "summary", "publications", "experience", "projects", "skills", "education"],
        "max_pages": 4,
    },
    "portfolio_narrative": {
        "name": "Portfolio Narrative",
        "use_case": "Personal website, portfolio page",
        "sections": ["intro_story", "key_projects", "skills_visual", "contact"],
        "format": "markdown",
    },
}


def _build_standard(resume: Resume) -> str:
    parts: list[str] = []
    c = resume.contact
    parts.append(f"{c.name}\n{c.email}" + (f" | {c.phone}" if c.phone else "") + (f" | {c.location}" if c.location else ""))
    if resume.summary:
        parts.append(f"\nPROFESSIONAL SUMMARY\n{resume.summary}")
    parts.append("\nEXPERIENCE")
    for exp in resume.work_experience:
        parts.append(f"\n{exp.company} — {exp.title}")
        for b in exp.bullets:
            parts.append(f"  - {b}")
    parts.append("\nSKILLS")
    for cat, skills in resume.skills.items():
        parts.append(f"{cat}: {', '.join(skills)}")
    if resume.education:
        parts.append("\nEDUCATION")
        for edu in resume.education:
            parts.append(f"{edu.institution} — {edu.degree} {edu.field}")
    return "\n".join(parts)


def _build_linkedin(resume: Resume) -> str:
    headline = f"{resume.seniority_level.replace('_', ' ').title()} {resume.primary_domain.title()} Engineer"
    top_skills = []
    for sl in resume.skills.values():
        top_skills.extend(sl[:5])
    headline += f" | {' · '.join(top_skills[:5])}"

    about = resume.summary or ""
    if resume.work_experience:
        exp = resume.work_experience[0]
        about += f"\n\nCurrently at {exp.company}, where I {exp.bullets[0].lower() if exp.bullets else 'build great software'}."

    return f"HEADLINE\n{headline}\n\nABOUT\n{about}\n\nKEY SKILLS\n{', '.join(top_skills[:50])}"


def _build_one_page(resume: Resume) -> str:
    parts: list[str] = [f"{resume.contact.name} — {resume.seniority_level.replace('_', ' ').title()}\n{resume.contact.email}"]
    top_bullets: list[str] = []
    for exp in resume.work_experience:
        for b in exp.bullets:
            if any(c.isdigit() for c in b):
                top_bullets.append(b)
    parts.append("\nTOP ACHIEVEMENTS")
    for b in top_bullets[:3]:
        parts.append(f"  - {b}")
    all_skills: list[str] = []
    for sl in resume.skills.values():
        all_skills.extend(sl)
    parts.append(f"\nKEY SKILLS: {', '.join(all_skills[:15])}")
    return "\n".join(parts)


def _build_technical_cv(resume: Resume) -> str:
    parts = [_build_standard(resume)]
    if resume.publications:
        parts.append("\nPUBLICATIONS")
        for pub in resume.publications:
            parts.append(f"  - {pub}")
    if resume.projects:
        parts.append("\nPROJECTS")
        for proj in resume.projects:
            parts.append(f"  {proj.name}: {proj.description[:100]}")
    return "\n".join(parts)


def _build_portfolio(resume: Resume) -> str:
    name = resume.contact.name
    parts = [f"# {name}\n"]
    parts.append(resume.summary or f"Engineer with {resume.total_yoe:.0f} years of experience.")
    parts.append("\n## Featured Work\n")
    for exp in resume.work_experience[:2]:
        parts.append(f"### {exp.company}\n")
        for b in exp.bullets[:3]:
            parts.append(f"- {b}")
    return "\n".join(parts)


_BUILDERS = {
    "standard_pdf": _build_standard,
    "linkedin_optimized": _build_linkedin,
    "one_page_summary": _build_one_page,
    "technical_cv": _build_technical_cv,
    "portfolio_narrative": _build_portfolio,
}


def generate_format(resume: Resume, format_type: str) -> FormattedResume:
    if format_type not in RESUME_FORMATS:
        format_type = "standard_pdf"
    builder = _BUILDERS[format_type]
    content = builder(resume)
    meta = RESUME_FORMATS[format_type]
    return FormattedResume(
        format_type=format_type,
        format_name=meta["name"],
        content=content,
        word_count=len(content.split()),
        sections=meta.get("sections", []),
    )
