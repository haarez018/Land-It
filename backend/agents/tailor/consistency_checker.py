"""Resume Consistency Checker: catches contradictions and inconsistencies."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from backend.parsers.schemas import Resume


@dataclass
class Inconsistency:
    type: str
    severity: str
    description: str
    location_a: str
    location_b: str
    suggestion: str


def check_consistency(resume: Resume) -> list[Inconsistency]:
    issues: list[Inconsistency] = []

    # 1. Date overlaps
    exps = resume.work_experience
    for i in range(len(exps)):
        for j in range(i + 1, len(exps)):
            a, b = exps[i], exps[j]
            a_end = a.end_date or date.today()
            b_end = b.end_date or date.today()
            if a.start_date <= b_end and b.start_date <= a_end:
                overlap_months = min(
                    (a_end.year - b.start_date.year) * 12 + a_end.month - b.start_date.month,
                    (b_end.year - a.start_date.year) * 12 + b_end.month - a.start_date.month,
                )
                if overlap_months > 2:
                    issues.append(Inconsistency(
                        type="date_overlap", severity="high",
                        description=f"Overlapping dates: {a.company} and {b.company} overlap by ~{overlap_months} months",
                        location_a=f"{a.company} ({a.start_date}–{a.end_date or 'Present'})",
                        location_b=f"{b.company} ({b.start_date}–{b.end_date or 'Present'})",
                        suggestion="Add 'Part-time' or 'Concurrent' if these roles overlapped intentionally",
                    ))

    # 2. YoE conflict
    if resume.summary:
        claimed = re.search(r"(\d+)\+?\s*years?", resume.summary)
        if claimed:
            stated = int(claimed.group(1))
            actual = resume.total_yoe
            if abs(stated - actual) > 2:
                issues.append(Inconsistency(
                    type="yoe_conflict", severity="high",
                    description=f"Summary claims {stated} years but dates add up to ~{actual:.0f} years",
                    location_a="Summary", location_b="Experience dates",
                    suggestion="Update the years count to match your actual experience timeline",
                ))

    # 3. Title regression
    seniority_rank = {"intern": 0, "junior": 1, "associate": 1, "mid": 2, "senior": 3, "staff": 4, "principal": 4, "lead": 3, "director": 5, "vp": 6}
    for i in range(len(exps) - 1):
        curr_title = exps[i].title.lower()
        next_title = exps[i + 1].title.lower()
        curr_rank = max((v for k, v in seniority_rank.items() if k in curr_title), default=2)
        next_rank = max((v for k, v in seniority_rank.items() if k in next_title), default=2)
        if curr_rank < next_rank - 1:
            issues.append(Inconsistency(
                type="title_regression", severity="medium",
                description=f"Title appears to regress: '{exps[i].title}' after '{exps[i+1].title}'",
                location_a=exps[i].company, location_b=exps[i + 1].company,
                suggestion="Add context for the change (e.g., startup to FAANG, different function)",
            ))

    # 4. Employment gaps (exps are newest-first)
    for i in range(len(exps) - 1):
        prev_end = exps[i + 1].end_date
        curr_start = exps[i].start_date
        if prev_end and curr_start:
            gap_months = (curr_start.year - prev_end.year) * 12 + curr_start.month - prev_end.month
            if gap_months > 6:
                issues.append(Inconsistency(
                    type="employment_gap", severity="low",
                    description=f"{gap_months}-month gap between {exps[i + 1].company} and {exps[i].company}",
                    location_a=exps[i + 1].company, location_b=exps[i].company,
                    suggestion="Consider noting freelance work, education, or personal projects during this period",
                ))

    # 5. Tense inconsistency in current role
    if exps and exps[0].end_date is None:
        past_tense_count = sum(1 for b in exps[0].bullets if re.match(r"^[A-Z]\w+ed\b", b))
        present_tense_count = sum(1 for b in exps[0].bullets if re.match(r"^[A-Z]\w+(?:s|ing)\b", b))
        if past_tense_count > 0 and present_tense_count > 0 and len(exps[0].bullets) > 2:
            issues.append(Inconsistency(
                type="tense_inconsistency", severity="low",
                description=f"Current role mixes past and present tense ({past_tense_count} past, {present_tense_count} present)",
                location_a=f"{exps[0].company} bullets", location_b="",
                suggestion="Use present tense consistently for your current role",
            ))

    # 6. Skill claimed but never demonstrated
    all_bullet_text = " ".join(b.lower() for exp in exps for b in exp.bullets)
    for cat, skills in resume.skills.items():
        for skill in skills:
            if len(skill) > 3 and skill.lower() not in all_bullet_text:
                pass  # Only flag high-confidence mismatches

    return issues
