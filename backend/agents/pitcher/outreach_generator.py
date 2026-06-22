"""Cold Outreach Generator: personalized LinkedIn DMs and emails to hiring managers."""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.parsers.schemas import Resume


@dataclass
class OutreachMessage:
    channel: str
    recipient_type: str
    subject: str | None
    body: str
    tone: str
    word_count: int
    company_reference: str | None = None
    role_reference: str | None = None


OUTREACH_TEMPLATES: dict[str, dict] = {
    "linkedin_hiring_manager": {
        "max_words": 150,
        "structure": ["Hook: reference their work/company", "Bridge: connect your experience", "Ask: low-commitment request"],
        "rules": ["Never open with 'I hope this finds you well'", "Reference specific team/product", "Make the ask easy"],
    },
    "linkedin_engineer": {
        "max_words": 120,
        "structure": ["Compliment their work", "Brief context on you", "Ask about team culture"],
    },
    "email_recruiter": {
        "max_words": 200,
        "structure": ["Subject: role + credential", "Interest in specific role", "2-3 bullet achievements", "Availability"],
    },
}


def _extract_top_achievement(resume: Resume) -> str:
    for exp in resume.work_experience:
        for bullet in exp.bullets:
            if any(c.isdigit() for c in bullet) and len(bullet) > 30:
                return bullet[:120]
    return f"{resume.total_yoe:.0f} years building {resume.primary_domain} systems"


def _build_linkedin_dm(resume: Resume, company: str, role: str, recipient_type: str) -> str:
    achievement = _extract_top_achievement(resume)
    name = resume.contact.name.split()[0] if resume.contact.name else "Hi"

    if recipient_type == "hiring_manager":
        return (
            f"Hi — I noticed {company}'s {role} opening and was impressed by what your team "
            f"is building. My background aligns closely: {achievement}. "
            f"Would you be open to a 15-minute chat about the role? Happy to share more context."
        )
    else:
        return (
            f"Hi! I came across your work at {company} and really liked what the team is doing. "
            f"I'm a {resume.seniority_level} {resume.primary_domain} engineer exploring roles — "
            f"would love to hear what the technical challenges look like on your team."
        )


def _build_email(resume: Resume, company: str, role: str) -> tuple[str, str]:
    achievement = _extract_top_achievement(resume)
    subject = f"{role} — {resume.contact.name} | {resume.seniority_level.replace('_', ' ').title()}"
    body = (
        f"Hi,\n\n"
        f"I'm writing to express interest in the {role} position at {company}. "
        f"Here's why I'd be a strong fit:\n\n"
        f"- {achievement}\n"
        f"- {resume.total_yoe:.0f} years of experience in {resume.primary_domain}\n"
        f"- Currently at {resume.work_experience[0].company if resume.work_experience else 'a top company'}\n\n"
        f"I'd welcome the chance to discuss how my experience aligns with your team's needs. "
        f"Available for a call this week.\n\n"
        f"Best,\n{resume.contact.name}"
    )
    return subject, body


def generate_outreach(
    resume: Resume,
    target_company: str,
    target_role: str,
    channel: str = "linkedin",
    recipient_type: str = "hiring_manager",
) -> OutreachMessage:
    if channel == "email":
        subject, body = _build_email(resume, target_company, target_role)
        return OutreachMessage(
            channel="email", recipient_type="recruiter", subject=subject,
            body=body, tone="professional", word_count=len(body.split()),
            company_reference=target_company, role_reference=target_role,
        )

    body = _build_linkedin_dm(resume, target_company, target_role, recipient_type)
    return OutreachMessage(
        channel="linkedin", recipient_type=recipient_type, subject=None,
        body=body, tone="professional", word_count=len(body.split()),
        company_reference=target_company, role_reference=target_role,
    )
