"""
Generate before/after diffs between original and tailored resumes.

Produces structured diffs suitable for rendering in the frontend's
ResumeDiff component (react-diff-viewer-continued).
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Optional

from backend.parsers.schemas import Resume, WorkExperience
from .resume_rewriter import RewriteChange


@dataclass
class BulletDiff:
    """Diff for a single bullet point."""
    section: str  # e.g. "Work Experience / Google / Bullet 1"
    original: str
    rewritten: str
    diff_type: str  # "added" | "removed" | "changed" | "unchanged"


@dataclass
class SectionDiff:
    """Diff for an entire resume section."""
    section_name: str
    original_text: str
    rewritten_text: str
    bullet_diffs: list[BulletDiff] = field(default_factory=list)
    has_changes: bool = False


@dataclass
class ResumeDiff:
    """Complete diff between original and rewritten resume."""
    section_diffs: list[SectionDiff]
    total_changes: int
    changes_by_type: dict[str, int]  # {"added": N, "removed": N, "changed": N}
    unified_diff: str  # unified diff format for react-diff-viewer
    change_log: list[RewriteChange]  # from the rewriter
    score_before: Optional[float] = None
    score_after: Optional[float] = None


def _format_experience_text(experiences: list[WorkExperience]) -> str:
    """Format work experience list as readable text."""
    lines: list[str] = []
    for exp in experiences:
        lines.append(f"{exp.title} at {exp.company}")
        start = exp.start_date.strftime("%b %Y")
        end = exp.end_date.strftime("%b %Y") if exp.end_date else "Present"
        lines.append(f"{start} - {end}")
        for bullet in exp.bullets:
            lines.append(f"  - {bullet}")
        lines.append("")
    return "\n".join(lines)


def _format_skills_text(skills: dict[str, list[str]]) -> str:
    """Format skills dict as readable text."""
    lines: list[str] = []
    for category, items in skills.items():
        lines.append(f"{category.title()}: {', '.join(items)}")
    return "\n".join(lines)


def _format_resume_text(resume: Resume) -> str:
    """Format full resume as readable text for diff comparison."""
    sections: list[str] = []

    # Contact
    c = resume.contact
    sections.append(f"{c.name}")
    contact_parts = [c.email]
    if c.phone:
        contact_parts.append(c.phone)
    if c.location:
        contact_parts.append(c.location)
    sections.append(" | ".join(contact_parts))
    sections.append("")

    # Summary
    if resume.summary:
        sections.append("SUMMARY")
        sections.append(resume.summary)
        sections.append("")

    # Experience
    if resume.work_experience:
        sections.append("EXPERIENCE")
        sections.append(_format_experience_text(resume.work_experience))

    # Skills
    if resume.skills:
        sections.append("SKILLS")
        sections.append(_format_skills_text(resume.skills))
        sections.append("")

    # Education
    if resume.education:
        sections.append("EDUCATION")
        for edu in resume.education:
            line = f"{edu.degree}"
            if edu.field:
                line += f" in {edu.field}"
            line += f", {edu.institution}"
            if edu.graduation_date:
                line += f" ({edu.graduation_date.year})"
            sections.append(line)
            if edu.gpa:
                sections.append(f"  GPA: {edu.gpa}")
            if edu.honors:
                sections.append(f"  Honors: {', '.join(edu.honors)}")
        sections.append("")

    # Projects
    if resume.projects:
        sections.append("PROJECTS")
        for proj in resume.projects:
            sections.append(f"{proj.name}")
            sections.append(f"  {proj.description}")
            if proj.technologies:
                sections.append(f"  Technologies: {', '.join(proj.technologies)}")
        sections.append("")

    # Certifications
    if resume.certifications:
        sections.append("CERTIFICATIONS")
        for cert in resume.certifications:
            sections.append(f"{cert.name} — {cert.issuer}")
        sections.append("")

    return "\n".join(sections)


def generate_diff(
    original: Resume,
    rewritten: Resume,
    change_log: list[RewriteChange],
    *,
    score_before: Optional[float] = None,
    score_after: Optional[float] = None,
) -> ResumeDiff:
    """Generate a comprehensive diff between original and rewritten resumes."""

    original_text = _format_resume_text(original)
    rewritten_text = _format_resume_text(rewritten)

    # Generate unified diff
    unified = difflib.unified_diff(
        original_text.splitlines(keepends=True),
        rewritten_text.splitlines(keepends=True),
        fromfile="Original Resume",
        tofile="Tailored Resume",
        lineterm="",
    )
    unified_diff = "\n".join(unified)

    # Build section-level diffs
    section_diffs: list[SectionDiff] = []

    # Summary diff
    orig_summary = original.summary or ""
    new_summary = rewritten.summary or ""
    if orig_summary != new_summary:
        section_diffs.append(SectionDiff(
            section_name="Summary",
            original_text=orig_summary,
            rewritten_text=new_summary,
            has_changes=True,
        ))

    # Experience diffs
    for orig_exp, new_exp in zip(original.work_experience, rewritten.work_experience):
        bullet_diffs: list[BulletDiff] = []
        has_changes = False

        # Compare bullets
        max_bullets = max(len(orig_exp.bullets), len(new_exp.bullets))
        for i in range(max_bullets):
            orig_bullet = orig_exp.bullets[i] if i < len(orig_exp.bullets) else ""
            new_bullet = new_exp.bullets[i] if i < len(new_exp.bullets) else ""

            if orig_bullet == new_bullet:
                diff_type = "unchanged"
            elif not orig_bullet:
                diff_type = "added"
                has_changes = True
            elif not new_bullet:
                diff_type = "removed"
                has_changes = True
            else:
                diff_type = "changed"
                has_changes = True

            bullet_diffs.append(BulletDiff(
                section=f"Work Experience / {orig_exp.company} / Bullet {i+1}",
                original=orig_bullet,
                rewritten=new_bullet,
                diff_type=diff_type,
            ))

        section_diffs.append(SectionDiff(
            section_name=f"Experience — {orig_exp.company}",
            original_text="\n".join(f"- {b}" for b in orig_exp.bullets),
            rewritten_text="\n".join(f"- {b}" for b in new_exp.bullets),
            bullet_diffs=bullet_diffs,
            has_changes=has_changes,
        ))

    # Skills diff
    orig_skills = _format_skills_text(original.skills)
    new_skills = _format_skills_text(rewritten.skills)
    if orig_skills != new_skills:
        section_diffs.append(SectionDiff(
            section_name="Skills",
            original_text=orig_skills,
            rewritten_text=new_skills,
            has_changes=True,
        ))

    # Count changes by type
    changes_by_type = {"added": 0, "removed": 0, "changed": 0}
    for sd in section_diffs:
        for bd in sd.bullet_diffs:
            if bd.diff_type in changes_by_type:
                changes_by_type[bd.diff_type] += 1
    # Count section-level changes that aren't bullet-level
    for sd in section_diffs:
        if sd.has_changes and not sd.bullet_diffs:
            changes_by_type["changed"] += 1

    total_changes = sum(changes_by_type.values())

    return ResumeDiff(
        section_diffs=section_diffs,
        total_changes=total_changes,
        changes_by_type=changes_by_type,
        unified_diff=unified_diff,
        change_log=change_log,
        score_before=score_before,
        score_after=score_after,
    )
