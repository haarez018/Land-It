"""Demo endpoint: pre-loaded resume + JD scoring, plus a rich data seeder for demos."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from backend.auth_deps import get_current_user_id
from backend.db import get_db
from backend.fixtures.demo_data import DEMO_RESUME_TEXT, DEMO_JD_TEXT
from backend.parsers.resume_parser import parse_resume_text
from backend.parsers.jd_parser import parse_jd
from backend.agents.tailor.agent import TailorAgent, DualScoreResult
from backend.agents.scout.salary_intel import estimate_salary, SalaryEstimate

router = APIRouter()

_DEMO_TAG = "demo_seeded"


def _hex() -> str:
    return uuid.uuid4().hex


def _now_minus(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _build_resume(name: str, email: str, title: str, summary: str, skills: dict, experiences: list) -> dict:
    return {
        "id": _hex(),
        "user_id": None,  # replaced at insert time
        "raw_text": f"{name}\n{email}\n{title}\n{summary}",
        "contact": {
            "name": name, "email": email, "phone": "+1-555-0100",
            "linkedin": f"linkedin.com/in/{name.lower().replace(' ', '')}",
            "github": f"github.com/{name.lower().replace(' ', '')}",
            "location": "San Francisco, CA",
        },
        "summary": summary,
        "work_experience": experiences,
        "education": [{
            "institution": "University of California, Berkeley",
            "degree": "Bachelor of Science",
            "field": "Computer Science",
            "graduation_date": "2018-05-15",
            "gpa": 3.7,
            "honors": ["Summa Cum Laude"],
            "relevant_courses": ["Algorithms", "Machine Learning", "Distributed Systems"],
        }],
        "skills": skills,
        "projects": [],
        "certifications": [],
        "publications": [],
        "awards": [],
        "languages": ["English"],
        "total_yoe": 6.0,
        "seniority_level": "senior",
        "primary_domain": title.lower().split()[0],
        "parsed_at": _now_minus(30),
        "embedding_id": None,
    }


_RESUME_FIXTURES = [
    _build_resume(
        name="Alex Chen",
        email="alex.chen@email.com",
        title="Senior Software Engineer",
        summary=(
            "Senior backend engineer with 6+ years building high-scale Python/FastAPI services "
            "on AWS. Led 3 system redesigns that each cut p99 latency by >40%."
        ),
        skills={
            "languages": ["Python", "Go", "TypeScript", "SQL"],
            "frameworks": ["FastAPI", "Django", "gRPC", "React"],
            "tools": ["AWS", "Kubernetes", "Terraform", "PostgreSQL", "Redis", "Kafka"],
        },
        experiences=[
            {
                "company": "Stripe", "title": "Senior Software Engineer",
                "start_date": "2021-03-01", "end_date": None, "location": "San Francisco, CA",
                "bullets": [
                    "Reduced payment processing latency by 42% by rearchitecting the auth service with event sourcing",
                    "Built real-time fraud detection pipeline processing 50K TPS with <10ms p99",
                    "Led team of 5 engineers shipping 3 major product features per quarter",
                ],
                "technologies": ["Python", "Go", "Kafka", "PostgreSQL"],
                "impact_metrics": ["42% latency reduction", "50K TPS", "5-person team"],
                "seniority_signals": ["led", "architected", "reduced"],
            },
            {
                "company": "Airbnb", "title": "Software Engineer",
                "start_date": "2018-07-01", "end_date": "2021-02-28", "location": "San Francisco, CA",
                "bullets": [
                    "Shipped search ranking improvements that increased booking conversion by 8%",
                    "Migrated 3 monolithic services to microservices, cutting deploy time from 45 to 8 minutes",
                ],
                "technologies": ["Python", "Java", "AWS", "MySQL"],
                "impact_metrics": ["8% conversion lift", "45→8 min deploy"],
                "seniority_signals": ["shipped", "migrated"],
            },
        ],
    ),
    _build_resume(
        name="Sarah Johnson",
        email="sarah.johnson@email.com",
        title="Senior Product Manager",
        summary=(
            "Product leader with 7 years turning complex B2B problems into loved products. "
            "Shipped 12 major features with average NPS lift of +18."
        ),
        skills={
            "methods": ["Agile", "OKRs", "Jobs-to-be-Done", "A/B Testing"],
            "tools": ["Jira", "Figma", "Mixpanel", "SQL", "Tableau"],
            "domains": ["B2B SaaS", "Developer Tools", "Fintech"],
        },
        experiences=[
            {
                "company": "Notion", "title": "Senior Product Manager",
                "start_date": "2020-09-01", "end_date": None, "location": "San Francisco, CA",
                "bullets": [
                    "Owned the databases product area; grew DAU from 200K to 1.2M in 18 months",
                    "Defined and shipped Notion AI, which became #1 feature request within 2 months of launch",
                    "Ran 40+ discovery interviews per quarter to validate roadmap decisions",
                ],
                "technologies": ["SQL", "Mixpanel", "Figma"],
                "impact_metrics": ["200K→1.2M DAU", "#1 feature launch"],
                "seniority_signals": ["owned", "defined", "shipped"],
            },
        ],
    ),
    _build_resume(
        name="Marcus Williams",
        email="marcus.williams@email.com",
        title="Senior Data Scientist",
        summary=(
            "ML engineer and data scientist with 5 years shipping production models. "
            "Published 2 papers at NeurIPS. Specializes in NLP and recommendation systems."
        ),
        skills={
            "languages": ["Python", "R", "SQL", "Scala"],
            "frameworks": ["PyTorch", "TensorFlow", "scikit-learn", "Spark", "Hugging Face"],
            "tools": ["Databricks", "MLflow", "AWS SageMaker", "dbt", "Airflow"],
        },
        experiences=[
            {
                "company": "Databricks", "title": "Senior Data Scientist",
                "start_date": "2020-01-01", "end_date": None, "location": "San Francisco, CA",
                "bullets": [
                    "Built LLM fine-tuning pipeline reducing hallucination rate by 31% on enterprise Q&A tasks",
                    "Designed recommendation engine increasing feature adoption by 22%",
                    "Published research on sparse attention at NeurIPS 2023",
                ],
                "technologies": ["Python", "PyTorch", "Spark", "MLflow"],
                "impact_metrics": ["31% hallucination reduction", "22% adoption lift"],
                "seniority_signals": ["built", "designed", "published"],
            },
        ],
    ),
]

_JOB_FIXTURES = [
    # Backend Engineering
    {"company": "Google", "title": "Senior Software Engineer, Infrastructure", "location": "Mountain View, CA",
     "required_skills": ["Python", "Go", "Distributed Systems", "Kubernetes"], "seniority": "senior",
     "salary_low": 180000, "salary_high": 280000, "domain": "software_engineer_backend"},
    {"company": "Meta", "title": "Software Engineer E5, Core Systems", "location": "Menlo Park, CA",
     "required_skills": ["C++", "Python", "System Design", "MySQL"], "seniority": "senior",
     "salary_low": 200000, "salary_high": 320000, "domain": "software_engineer_backend"},
    {"company": "Amazon", "title": "Senior SDE, AWS Compute", "location": "Seattle, WA",
     "required_skills": ["Java", "AWS", "Microservices", "Distributed Systems"], "seniority": "senior",
     "salary_low": 160000, "salary_high": 240000, "domain": "software_engineer_backend"},
    {"company": "Stripe", "title": "Staff Engineer, Payments", "location": "San Francisco, CA",
     "required_skills": ["Python", "Ruby", "Go", "Kafka", "PostgreSQL"], "seniority": "staff",
     "salary_low": 220000, "salary_high": 350000, "domain": "software_engineer_backend"},
    {"company": "Airbnb", "title": "Senior Software Engineer, Search", "location": "San Francisco, CA",
     "required_skills": ["Java", "Python", "Elasticsearch", "Machine Learning"], "seniority": "senior",
     "salary_low": 175000, "salary_high": 260000, "domain": "software_engineer_backend"},
    # Product Management
    {"company": "Salesforce", "title": "Senior Product Manager, Einstein AI", "location": "San Francisco, CA",
     "required_skills": ["Product Strategy", "AI/ML", "B2B SaaS", "SQL"], "seniority": "senior",
     "salary_low": 160000, "salary_high": 220000, "domain": "product_manager"},
    {"company": "HubSpot", "title": "Group Product Manager, CRM", "location": "Remote",
     "required_skills": ["Product Management", "CRM", "Analytics", "Agile"], "seniority": "senior",
     "salary_low": 150000, "salary_high": 200000, "domain": "product_manager"},
    {"company": "Notion", "title": "Product Manager, Collaboration", "location": "San Francisco, CA",
     "required_skills": ["Product Management", "User Research", "B2B", "Figma"], "seniority": "mid",
     "salary_low": 130000, "salary_high": 180000, "domain": "product_manager"},
    {"company": "Linear", "title": "Senior Product Manager", "location": "Remote",
     "required_skills": ["Developer Tools", "Product Strategy", "SQL", "User Research"], "seniority": "senior",
     "salary_low": 155000, "salary_high": 210000, "domain": "product_manager"},
    {"company": "Figma", "title": "Staff Product Manager, Enterprise", "location": "San Francisco, CA",
     "required_skills": ["Enterprise SaaS", "Product Management", "Stakeholder Management"], "seniority": "staff",
     "salary_low": 180000, "salary_high": 250000, "domain": "product_manager"},
    # Data Science / ML
    {"company": "OpenAI", "title": "Research Engineer, Applied ML", "location": "San Francisco, CA",
     "required_skills": ["Python", "PyTorch", "LLMs", "RLHF", "Distributed Training"], "seniority": "senior",
     "salary_low": 250000, "salary_high": 400000, "domain": "data_scientist"},
    {"company": "Anthropic", "title": "Research Engineer, Alignment", "location": "San Francisco, CA",
     "required_skills": ["Python", "PyTorch", "ML Safety", "Transformers"], "seniority": "senior",
     "salary_low": 240000, "salary_high": 380000, "domain": "data_scientist"},
    {"company": "Databricks", "title": "Staff Data Scientist", "location": "San Francisco, CA",
     "required_skills": ["Python", "PySpark", "MLflow", "SQL", "Statistical Modeling"], "seniority": "staff",
     "salary_low": 200000, "salary_high": 300000, "domain": "data_scientist"},
    {"company": "Scale AI", "title": "Senior ML Engineer", "location": "San Francisco, CA",
     "required_skills": ["Python", "PyTorch", "Data Pipelines", "Labeling Systems"], "seniority": "senior",
     "salary_low": 180000, "salary_high": 270000, "domain": "data_scientist"},
    {"company": "DeepMind", "title": "Research Scientist", "location": "London, UK",
     "required_skills": ["Python", "JAX", "Reinforcement Learning", "Publications"], "seniority": "senior",
     "salary_low": 160000, "salary_high": 280000, "domain": "data_scientist"},
]

_cached_demo_result: Optional[dict] = None


async def _compute_demo_score() -> dict:
    global _cached_demo_result
    if _cached_demo_result is not None:
        return _cached_demo_result

    resume = parse_resume_text(DEMO_RESUME_TEXT)
    jd = parse_jd(DEMO_JD_TEXT)

    agent = TailorAgent()
    dual: DualScoreResult = await agent.score_dual(
        resume, jd,
        role_type="software_engineer_backend",
        seniority="senior",
        company="google",
    )

    salary: SalaryEstimate = estimate_salary(resume, jd)

    from backend.api.routes.resume import (
        ScoreResponse, DimensionScoreResponse,
        StandoutScoreResponse, StandoutDimensionScoreResponse,
        DualScoreResponse, CallbackPredictionResponse,
    )

    ats_resp = ScoreResponse(
        total_score=dual.ats.total_score,
        letter_grade=dual.ats.letter_grade,
        dimension_scores=[
            DimensionScoreResponse(
                dimension_id=d.dimension_id, dimension_name=d.dimension_name,
                raw_score=d.raw_score, weighted_score=d.weighted_score,
                weight=d.weight, explanation=d.explanation,
                issues=d.issues, suggestions=d.suggestions, priority=d.priority,
            ) for d in dual.ats.dimension_scores
        ],
        top_3_issues=dual.ats.top_3_issues,
        top_3_wins=dual.ats.top_3_wins,
        predicted_ats_pass=dual.ats.predicted_ats_pass,
        role_type=dual.ats.role_type,
        seniority_level=dual.ats.seniority_level,
        weights_used=dual.ats.weights_used,
    )

    standout_resp = StandoutScoreResponse(
        total_score=dual.standout.total_score,
        letter_grade=dual.standout.letter_grade,
        dimension_scores=[
            StandoutDimensionScoreResponse(
                dimension_id=d.dimension_id, dimension_name=d.dimension_name,
                raw_score=d.raw_score, weighted_score=d.weighted_score,
                weight=d.weight, explanation=d.explanation,
                issues=d.issues, suggestions=d.suggestions, priority=d.priority,
            ) for d in dual.standout.dimension_scores
        ],
        top_3_issues=dual.standout.top_3_issues,
        top_3_wins=dual.standout.top_3_wins,
        spike_detected=dual.standout.spike_detected,
        role_type=dual.standout.role_type,
        seniority_level=dual.standout.seniority_level,
        weights_used=dual.standout.weights_used,
        amplification_tips=dual.standout.amplification_tips,
    )

    callback_resp = None
    if dual.callback_prediction:
        p = dual.callback_prediction
        callback_resp = CallbackPredictionResponse(
            probability=p.probability,
            confidence_interval=p.confidence_interval,
            confidence_level=p.confidence_level,
            top_positive_factors=p.top_positive_factors,
            top_negative_factors=p.top_negative_factors,
            vs_average_applicant=p.vs_average_applicant,
            score_needed_for_50pct=p.score_needed_for_50pct,
            fixes_for_10pct_boost=p.fixes_for_10pct_boost,
            role_type=p.role_type,
            seniority_level=p.seniority_level,
            combined_score=p.combined_score,
            base_rate=p.base_rate,
        )

    dual_resp = DualScoreResponse(
        ats_score=ats_resp,
        standout_score=standout_resp,
        combined_score=dual.combined_score,
        combined_grade=dual.combined_grade,
        total_dimensions=dual.total_dimensions,
        summary=dual.summary,
        callback_prediction=callback_resp,
    )

    salary_resp = {
        "role_type": salary.role_type,
        "seniority": salary.seniority,
        "location": salary.location,
        "company": salary.company,
        "estimated_range": list(salary.estimated_range),
        "estimated_midpoint": salary.estimated_midpoint,
        "user_position_in_range": salary.user_position_in_range,
        "user_estimated_value": salary.user_estimated_value,
        "premium_factors": salary.premium_factors,
        "discount_factors": salary.discount_factors,
        "negotiation_leverage": salary.negotiation_leverage,
        "negotiation_talking_points": salary.negotiation_talking_points,
        "confidence": salary.confidence,
        "confidence_reason": salary.confidence_reason,
    }

    _cached_demo_result = {
        "dual_score": dual_resp.model_dump(),
        "salary": salary_resp,
        "demo_resume_text": DEMO_RESUME_TEXT,
        "demo_jd_text": DEMO_JD_TEXT,
    }

    return _cached_demo_result


@router.get("/score")
async def demo_score():
    """Score the pre-loaded demo resume against the demo JD. Cached after first call."""
    return await _compute_demo_score()


# ── Rich data seeder ──────────────────────────────────────────────────────────

@router.post("/seed")
async def seed_demo_data(user_id: str = Depends(get_current_user_id)):
    """
    Seed rich demo data for this user: 3 resumes, 15 jobs, 12 applications.
    Safe to call multiple times — creates new records each time under the same user.
    """
    db = get_db()

    # 1. Insert 3 resumes
    resume_ids: list[str] = []
    for tmpl in _RESUME_FIXTURES:
        record = {**tmpl, "user_id": user_id, "data": {**tmpl, "user_id": user_id}}
        rid = tmpl["id"]
        resume_ids.append(rid)
        db.table("resumes").upsert({"id": rid, "user_id": user_id, "data": record, "filename": f"{tmpl['contact']['name'].lower().replace(' ', '_')}.pdf", "tags": [_DEMO_TAG]}).execute()

    # 2. Insert 15 jobs
    job_ids: list[str] = []
    for j in _JOB_FIXTURES:
        jid = _hex()
        job_ids.append(jid)
        jd_data = {
            "id": jid,
            "raw_text": f"{j['title']} at {j['company']}. Required: {', '.join(j['required_skills'])}.",
            "title": j["title"],
            "company": j["company"],
            "location": j["location"],
            "remote_policy": "remote" if j["location"] == "Remote" else "hybrid",
            "salary_range": [j["salary_low"], j["salary_high"]],
            "seniority_level": j["seniority"],
            "employment_type": "full_time",
            "required_skills": j["required_skills"],
            "preferred_skills": [],
            "tech_stack": j["required_skills"][:3],
            "requirements": [{"text": s, "category": "must_have", "skill_type": "technical", "extracted_keyword": s} for s in j["required_skills"]],
            "role_type": j["domain"],
            "fit_score": None,
        }
        db.table("jobs").upsert({"id": jid, "user_id": user_id, "data": jd_data, "tags": [_DEMO_TAG]}).execute()

    # 3. Insert 12 applications with varied statuses and callback probabilities
    _APP_CONFIGS = [
        (0, 0, "submitted", 0.68, 0.79, 1, 0.72),
        (0, 1, "interviewing", 0.71, 0.83, 1, 0.81),
        (0, 2, "offer", 0.75, 0.88, 1, 0.91),
        (0, 3, "rejected", 0.58, 0.61, 2, 0.35),
        (0, 4, "phone_screen", 0.65, 0.74, 1, 0.62),
        (1, 5, "submitted", 0.72, 0.80, 1, 0.69),
        (1, 6, "interviewing", 0.69, 0.82, 1, 0.78),
        (1, 7, "rejected", 0.55, 0.58, 2, 0.28),
        (1, 8, "offer", 0.78, 0.90, 1, 0.88),
        (2, 10, "submitted", 0.73, 0.85, 1, 0.74),
        (2, 11, "interviewing", 0.77, 0.89, 1, 0.85),
        (2, 12, "rejected", 0.60, 0.65, 2, 0.32),
    ]

    app_ids: list[str] = []
    for resume_idx, job_idx, status, score_before, score_after, priority, callback_prob in _APP_CONFIGS:
        if job_idx >= len(job_ids):
            continue
        aid = _hex()
        app_ids.append(aid)
        db.table("applications").insert({
            "id": aid,
            "user_id": user_id,
            "job_id": job_ids[job_idx],
            "status": status,
            "fit_score": round(score_after * 100, 1),
            "ats_score_before": round(score_before * 100, 1),
            "ats_score_after": round(score_after * 100, 1),
            "priority": priority,
            "notes": f"Demo application — {status.replace('_', ' ')}",
            "follow_up_due": None,
            "submitted_at": _now_minus(14 - job_idx),
            "callback_probability": callback_prob,
            "tags": [_DEMO_TAG],
        }).execute()

    return {
        "seeded": True,
        "resumes": len(resume_ids),
        "jobs": len(job_ids),
        "applications": len(app_ids),
    }


@router.delete("/reset")
async def reset_demo_data(user_id: str = Depends(get_current_user_id)):
    """
    Delete all demo-seeded records for this user.
    Resumes, jobs, and applications tagged with the demo tag are removed.
    """
    db = get_db()
    errors = []

    try:
        db.table("applications").delete().eq("user_id", user_id).contains("tags", [_DEMO_TAG]).execute()
    except Exception as e:
        errors.append(f"applications: {e}")
    try:
        db.table("jobs").delete().eq("user_id", user_id).contains("tags", [_DEMO_TAG]).execute()
    except Exception as e:
        errors.append(f"jobs: {e}")
    try:
        db.table("resumes").delete().eq("user_id", user_id).contains("tags", [_DEMO_TAG]).execute()
    except Exception as e:
        errors.append(f"resumes: {e}")

    if errors:
        raise HTTPException(500, f"Partial reset failures: {'; '.join(errors)}")

    return {"reset": True}
