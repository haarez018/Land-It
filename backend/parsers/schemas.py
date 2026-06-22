"""Core Pydantic models: Resume, JobDescription, Application. Built from Section 3 of the spec."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def _new_id() -> str:
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Resume schema
# ---------------------------------------------------------------------------

class ResumeContact(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    location: Optional[str] = None
    portfolio: Optional[str] = None


class WorkExperience(BaseModel):
    company: str
    title: str
    start_date: date
    end_date: Optional[date] = None
    location: Optional[str] = None
    bullets: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    impact_metrics: list[str] = Field(default_factory=list)
    seniority_signals: list[str] = Field(default_factory=list)


class Education(BaseModel):
    institution: str
    degree: str
    field: str
    graduation_date: Optional[date] = None
    gpa: Optional[float] = None
    honors: list[str] = Field(default_factory=list)
    relevant_courses: list[str] = Field(default_factory=list)


class Project(BaseModel):
    name: str
    description: str
    technologies: list[str] = Field(default_factory=list)
    impact: Optional[str] = None
    url: Optional[str] = None
    github_url: Optional[str] = None


class Certification(BaseModel):
    name: str
    issuer: str
    date: Optional[date] = None
    expiry: Optional[date] = None
    credential_id: Optional[str] = None


class Resume(BaseModel):
    id: str = Field(default_factory=_new_id)
    user_id: str = ""
    raw_text: str = ""
    contact: ResumeContact
    summary: Optional[str] = None
    work_experience: list[WorkExperience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: dict[str, list[str]] = Field(default_factory=dict)
    projects: list[Project] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    publications: list[str] = Field(default_factory=list)
    awards: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    total_yoe: float = 0.0
    seniority_level: str = "mid"
    primary_domain: str = "general"
    parsed_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    embedding_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Job Description schema
# ---------------------------------------------------------------------------

class JDRequirement(BaseModel):
    text: str
    category: str  # "must_have" | "nice_to_have" | "bonus"
    skill_type: str  # "technical" | "soft" | "domain" | "tool"
    extracted_keyword: str


class JobDescription(BaseModel):
    id: str = Field(default_factory=_new_id)
    raw_text: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    remote_policy: str = "onsite"
    salary_range: Optional[tuple[int, int]] = None
    seniority_level: str = "mid"
    employment_type: str = "full_time"

    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    required_experience_years: Optional[int] = None
    required_education: Optional[str] = None

    requirements: list[JDRequirement] = Field(default_factory=list)

    tech_stack: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    domain_knowledge: list[str] = Field(default_factory=list)
    company_values: list[str] = Field(default_factory=list)
    role_priorities: list[str] = Field(default_factory=list)

    source: str = "manual"
    source_url: str = ""
    posted_date: Optional[str] = None
    scraped_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    embedding_id: Optional[str] = None
    fit_score: Optional[float] = None

    def infer_role_type(self) -> str:
        """Infer role type from title and tech stack for weight profile selection."""
        title_lower = self.title.lower()
        stack_lower = " ".join(self.tech_stack).lower()
        combined = f"{title_lower} {stack_lower}"

        if any(kw in title_lower for kw in ["product manager", "pm", "product lead"]):
            return "product_manager"
        if any(kw in title_lower for kw in ["data scientist", "data science"]):
            return "data_scientist"
        if any(kw in title_lower for kw in ["ml engineer", "machine learning", "ai engineer"]):
            return "ml_engineer"
        if any(kw in title_lower for kw in ["devops", "sre", "site reliability", "platform engineer"]):
            return "devops_sre"
        if any(kw in title_lower for kw in ["research scientist", "researcher"]):
            return "research_scientist"
        if any(kw in title_lower for kw in ["ux", "ui", "designer", "design"]):
            return "design_ux"
        if any(kw in combined for kw in ["react", "vue", "angular", "frontend", "front-end", "css", "ui engineer"]):
            return "software_engineer_frontend"
        if any(kw in combined for kw in ["backend", "back-end", "api", "microservices", "distributed"]):
            return "software_engineer_backend"

        return "software_engineer_backend"


# ---------------------------------------------------------------------------
# Application schema
# ---------------------------------------------------------------------------

class ApplicationStatus(str, Enum):
    DISCOVERED = "discovered"
    QUEUED = "queued"
    TAILORING = "tailoring"
    READY = "ready"
    SUBMITTED = "submitted"
    FOLLOWED_UP = "followed_up"
    PHONE_SCREEN = "phone_screen"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class Application(BaseModel):
    id: str = Field(default_factory=_new_id)
    user_id: str = ""
    job_id: str = ""
    job: JobDescription = Field(default_factory=JobDescription)

    base_resume_id: str = ""
    tailored_resume_id: Optional[str] = None
    cover_letter_id: Optional[str] = None

    status: ApplicationStatus = ApplicationStatus.DISCOVERED
    fit_score: float = 0.0
    ats_score_before: Optional[float] = None
    ats_score_after: Optional[float] = None

    applied_at: Optional[str] = None
    last_activity: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    next_followup_at: Optional[str] = None

    notes: list[str] = Field(default_factory=list)
    email_thread_id: Optional[str] = None
    interview_sessions: list[str] = Field(default_factory=list)

    planner_priority: int = 5
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
