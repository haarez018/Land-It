"""Onboarding endpoints — multi-step wizard for first-time users."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

router = APIRouter()


# ── In-memory store ──────────────────────────────────────────────────────────

class UserProfile:
    def __init__(self):
        self.user_id: str = uuid.uuid4().hex
        self.name: str = ""
        self.email: str = ""
        self.resume_id: str = ""
        self.target_roles: list[str] = []
        self.target_seniority: str = "mid"
        self.target_locations: list[str] = []
        self.remote_preference: str = "any"
        self.salary_expectation: tuple[int, int] = (0, 0)
        self.company_size_preference: list[str] = []
        self.weekly_application_goal: int = 5
        self.writing_samples: list[str] = []
        self.onboarding_completed: bool = False
        self.baseline_ats_score: float = 0.0
        self.baseline_standout_score: float = 0.0
        self.baseline_combined_score: float = 0.0
        self.created_at: str = datetime.now(UTC).isoformat()
        self._steps_done: set[str] = set()


_profile_store: dict[str, UserProfile] = {}

# Singleton — one profile for now (no auth); real impl would be per-user
_active_profile_id: str | None = None


def _get_or_create_profile() -> UserProfile:
    global _active_profile_id
    if _active_profile_id and _active_profile_id in _profile_store:
        return _profile_store[_active_profile_id]
    p = UserProfile()
    _profile_store[p.user_id] = p
    _active_profile_id = p.user_id
    return p


# ── Request/Response models ──────────────────────────────────────────────────

class ProfileRequest(BaseModel):
    name: str
    email: str
    target_roles: list[str] = []
    target_seniority: str = "mid"
    target_locations: list[str] = []
    remote_preference: str = "any"
    salary_min: int = 0
    salary_max: int = 0
    company_size_preference: list[str] = []
    weekly_goal: int = 5


class WritingSamplesRequest(BaseModel):
    samples: list[str]


class BaselineRequest(BaseModel):
    role_type: str = ""


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/profile")
async def create_profile(request: ProfileRequest):
    """Step 1/2: Create or update user profile with job search preferences."""
    p = _get_or_create_profile()
    p.name = request.name
    p.email = request.email
    p.target_roles = request.target_roles
    p.target_seniority = request.target_seniority
    p.target_locations = request.target_locations
    p.remote_preference = request.remote_preference
    p.salary_expectation = (request.salary_min, request.salary_max)
    p.company_size_preference = request.company_size_preference
    p.weekly_application_goal = request.weekly_goal
    p._steps_done.add("profile")

    return {
        "profile_id": p.user_id,
        "name": p.name,
        "target_roles": p.target_roles,
        "target_seniority": p.target_seniority,
        "status": "profile_saved",
    }


@router.post("/resume")
async def upload_resume(
    file: UploadFile = File(...),
):
    """Step 1: Upload resume as PDF or DOCX. Parses and stores it."""
    import tempfile
    from pathlib import Path

    p = _get_or_create_profile()

    if not file.filename:
        raise HTTPException(400, "No file provided")

    from backend.parsers.resume_parser import parse_resume

    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".pdf", ".docx", ".doc"):
        raise HTTPException(400, f"Unsupported file type: {suffix}. Upload a PDF or DOCX.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        resume = parse_resume(tmp_path)
    except Exception as e:
        raise HTTPException(422, f"Failed to parse resume: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    # Store in the resume store for reuse
    from backend.api.routes.resume import _resume_store
    _resume_store[resume.id] = resume
    p.resume_id = resume.id
    p._steps_done.add("resume")

    # Build summary
    skill_count = sum(len(v) for v in resume.skills.values())
    top_skills = []
    for cat_skills in resume.skills.values():
        top_skills.extend(cat_skills)
    top_skills = top_skills[:5]

    return {
        "resume_id": resume.id,
        "name": resume.contact.name,
        "total_yoe": resume.total_yoe,
        "seniority_level": resume.seniority_level,
        "primary_domain": resume.primary_domain,
        "skill_count": skill_count,
        "top_skills": top_skills,
        "work_experience_count": len(resume.work_experience),
    }


@router.post("/writing-samples")
async def submit_writing_samples(request: WritingSamplesRequest):
    """Step 3 (optional): Store writing samples for voice analysis."""
    from backend.agents.pitcher.voice_analyzer import analyze_voice

    p = _get_or_create_profile()
    p.writing_samples = request.samples
    p._steps_done.add("writing_samples")

    if request.samples:
        voice = analyze_voice(request.samples)
        return {
            "status": "samples_saved",
            "sample_count": len(request.samples),
            "voice_summary": {
                "tone": voice.tone,
                "formality_level": voice.formality_level,
                "avg_sentence_length": voice.avg_sentence_length,
            },
        }
    return {
        "status": "samples_saved",
        "sample_count": 0,
        "voice_summary": None,
    }


@router.post("/baseline-score")
async def run_baseline_score(request: BaselineRequest):
    """Step 4: Score resume against a generic JD for baseline."""
    from backend.api.routes.resume import _resume_store
    from backend.agents.tailor.agent import TailorAgent
    from backend.agents.tailor.generic_jds import get_generic_jd

    p = _get_or_create_profile()

    if not p.resume_id or p.resume_id not in _resume_store:
        raise HTTPException(400, "Upload a resume first (step 1)")

    resume = _resume_store[p.resume_id]

    role_type = request.role_type or (p.target_roles[0] if p.target_roles else "software_engineer_backend")
    seniority = p.target_seniority or resume.seniority_level

    generic_jd = get_generic_jd(role_type, seniority)

    agent = TailorAgent()
    dual = await agent.score_dual(resume, generic_jd, role_type=role_type, seniority=seniority)

    p.baseline_ats_score = dual.ats.total_score
    p.baseline_standout_score = dual.standout.total_score
    p.baseline_combined_score = dual.combined_score
    p._steps_done.add("baseline_score")

    return {
        "ats_score": dual.ats.total_score,
        "standout_score": dual.standout.total_score,
        "combined_score": dual.combined_score,
        "combined_grade": dual.combined_grade,
        "callback_probability": dual.callback_prediction.probability if dual.callback_prediction else None,
        "top_3_wins": dual.ats.top_3_wins + dual.standout.top_3_wins[:1],
        "top_3_issues": dual.ats.top_3_issues + dual.standout.top_3_issues[:1],
        "role_type": role_type,
        "seniority": seniority,
        "summary": dual.summary,
    }


@router.post("/complete")
async def complete_onboarding():
    """Step 5: Mark onboarding as complete."""
    p = _get_or_create_profile()
    p.onboarding_completed = True
    p._steps_done.add("complete")

    return {
        "status": "onboarding_complete",
        "profile_id": p.user_id,
        "name": p.name,
        "baseline_ats_score": p.baseline_ats_score,
        "baseline_standout_score": p.baseline_standout_score,
        "baseline_combined_score": p.baseline_combined_score,
        "onboarding_completed": True,
    }


@router.get("/status")
async def onboarding_status():
    """Check onboarding progress."""
    p = _get_or_create_profile()

    all_steps = ["profile", "resume", "writing_samples", "baseline_score", "complete"]
    steps_done = [s for s in all_steps if s in p._steps_done]
    steps_remaining = [s for s in all_steps if s not in p._steps_done]

    return {
        "completed": p.onboarding_completed,
        "steps_done": steps_done,
        "steps_remaining": steps_remaining,
        "profile_id": p.user_id,
    }
