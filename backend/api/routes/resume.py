"""Resume upload, parsing, scoring, and tailoring endpoints."""

import tempfile
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.auth_deps import get_current_user_id
from backend.db import get_db
from backend.parsers.resume_parser import parse_resume
from backend.parsers.jd_parser import parse_jd
from backend.parsers.schemas import Resume, JobDescription

router = APIRouter()

# JD cache — session-scoped, non-sensitive
_jd_store: dict[str, JobDescription] = {}


# ── Supabase helpers (exported so other routes can use them) ─────────────────

def load_user_resume(resume_id: str, user_id: str) -> Resume:
    """Fetch a resume from Supabase. Raises 404 if not found or not owned by user."""
    resp = (
        get_db().table("resumes")
        .select("data")
        .eq("id", resume_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(404, "Resume not found")
    return Resume.model_validate(resp.data[0]["data"])


def save_user_resume(resume: Resume, user_id: str, filename: str = "") -> None:
    """Upsert a resume into Supabase."""
    get_db().table("resumes").upsert({
        "id": resume.id,
        "user_id": user_id,
        "data": resume.model_dump(),
        "filename": filename,
    }).execute()


# ── Upload ───────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=Resume)
async def upload_resume(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
):
    if not file.filename:
        raise HTTPException(400, "No file provided")

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

    save_user_resume(resume, user_id, filename=file.filename or "")
    return resume


@router.get("/{resume_id}", response_model=Resume)
async def get_resume(resume_id: str, user_id: str = Depends(get_current_user_id)):
    return load_user_resume(resume_id, user_id)


# ── Scoring ─────────────────────────────────────────────────────────────────


class ScoreRequest(BaseModel):
    jd_text: str
    role_type: Optional[str] = None
    seniority: Optional[str] = None


class DimensionScoreResponse(BaseModel):
    dimension_id: str
    dimension_name: str
    raw_score: float
    weighted_score: float
    weight: float
    explanation: str
    issues: list[str]
    suggestions: list[str]
    priority: str


class ScoreResponse(BaseModel):
    total_score: float
    letter_grade: str
    dimension_scores: list[DimensionScoreResponse]
    top_3_issues: list[str]
    top_3_wins: list[str]
    predicted_ats_pass: bool
    role_type: str
    seniority_level: str
    weights_used: dict[str, float]


@router.post("/{resume_id}/score", response_model=ScoreResponse)
async def score_resume_endpoint(
    resume_id: str,
    request: ScoreRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Score a resume against a JD using the 14-dimension ATS scorer."""
    resume = load_user_resume(resume_id, user_id)
    jd = parse_jd(request.jd_text)
    _jd_store[jd.id] = jd

    from backend.agents.tailor.weightage.scorer_engine import score_resume
    result = await score_resume(resume, jd, role_type=request.role_type, seniority=request.seniority)

    return ScoreResponse(
        total_score=result.total_score,
        letter_grade=result.letter_grade,
        dimension_scores=[
            DimensionScoreResponse(
                dimension_id=d.dimension_id, dimension_name=d.dimension_name,
                raw_score=d.raw_score, weighted_score=d.weighted_score,
                weight=d.weight, explanation=d.explanation,
                issues=d.issues, suggestions=d.suggestions, priority=d.priority,
            )
            for d in result.dimension_scores
        ],
        top_3_issues=result.top_3_issues,
        top_3_wins=result.top_3_wins,
        predicted_ats_pass=result.predicted_ats_pass,
        role_type=result.role_type,
        seniority_level=result.seniority_level,
        weights_used=result.weights_used,
    )


# ── Tailoring ───────────────────────────────────────────────────────────────


class TailorRequest(BaseModel):
    jd_text: str
    skip_passes: list[str] = []


class ChangeLogEntry(BaseModel):
    section: str
    original: str
    rewritten: str
    reason: str
    dimension_improved: list[str]
    confidence: str
    requires_verification: bool


class TailorResponse(BaseModel):
    score_before: float
    score_after: float
    improvement: float
    letter_grade_before: str
    letter_grade_after: str
    predicted_ats_pass: bool
    change_log: list[ChangeLogEntry]
    passes_applied: list[str]
    sections_reordered: bool
    summary_rewritten: bool
    unified_diff: str
    total_changes: int
    changes_by_type: dict[str, int]
    rewritten_resume: Resume


@router.post("/{resume_id}/tailor", response_model=TailorResponse)
async def tailor_resume(
    resume_id: str,
    request: TailorRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Run the full tailor pipeline: score → 6-pass rewrite → re-score → diff."""
    resume = load_user_resume(resume_id, user_id)
    jd = parse_jd(request.jd_text)
    _jd_store[jd.id] = jd

    from backend.agents.tailor.agent import TailorAgent
    agent = TailorAgent()
    skip = set(request.skip_passes) if request.skip_passes else None
    result = await agent.tailor(resume, jd, skip_passes=skip)

    save_user_resume(result.rewritten_resume, user_id)

    return TailorResponse(
        score_before=result.score_before.total_score,
        score_after=result.score_after.total_score,
        improvement=result.improvement,
        letter_grade_before=result.score_before.letter_grade,
        letter_grade_after=result.score_after.letter_grade,
        predicted_ats_pass=result.score_after.predicted_ats_pass,
        change_log=[
            ChangeLogEntry(
                section=c.section, original=c.original, rewritten=c.rewritten,
                reason=c.reason, dimension_improved=c.dimension_improved,
                confidence=c.confidence, requires_verification=c.requires_verification,
            )
            for c in result.rewrite_result.change_log
        ],
        passes_applied=result.rewrite_result.passes_applied,
        sections_reordered=result.rewrite_result.sections_reordered,
        summary_rewritten=result.rewrite_result.summary_rewritten,
        unified_diff=result.diff.unified_diff,
        total_changes=result.diff.total_changes,
        changes_by_type=result.diff.changes_by_type,
        rewritten_resume=result.rewritten_resume,
    )


# ── Standout Scoring ──────────────────────────────────────────────────────


class StandoutDimensionScoreResponse(BaseModel):
    dimension_id: str
    dimension_name: str
    raw_score: float
    weighted_score: float
    weight: float
    explanation: str
    issues: list[str]
    suggestions: list[str]
    priority: str


class StandoutScoreResponse(BaseModel):
    total_score: float
    letter_grade: str
    dimension_scores: list[StandoutDimensionScoreResponse]
    top_3_issues: list[str]
    top_3_wins: list[str]
    spike_detected: bool
    role_type: str
    seniority_level: str
    weights_used: dict[str, float]
    amplification_tips: list[str]


@router.post("/{resume_id}/score/standout", response_model=StandoutScoreResponse)
async def score_standout_endpoint(
    resume_id: str,
    request: ScoreRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Score a resume on the 8 Standout (human-impression) dimensions."""
    resume = load_user_resume(resume_id, user_id)
    jd = parse_jd(request.jd_text)
    _jd_store[jd.id] = jd

    from backend.agents.tailor.standout.engine import score_standout
    result = await score_standout(resume, jd, role_type=request.role_type, seniority=request.seniority)

    return StandoutScoreResponse(
        total_score=result.total_score,
        letter_grade=result.letter_grade,
        dimension_scores=[
            StandoutDimensionScoreResponse(
                dimension_id=d.dimension_id, dimension_name=d.dimension_name,
                raw_score=d.raw_score, weighted_score=d.weighted_score,
                weight=d.weight, explanation=d.explanation,
                issues=d.issues, suggestions=d.suggestions, priority=d.priority,
            )
            for d in result.dimension_scores
        ],
        top_3_issues=result.top_3_issues,
        top_3_wins=result.top_3_wins,
        spike_detected=result.spike_detected,
        role_type=result.role_type,
        seniority_level=result.seniority_level,
        weights_used=result.weights_used,
        amplification_tips=result.amplification_tips,
    )


# ── Dual Score (22-dimension) ─────────────────────────────────────────────


class CallbackPredictionResponse(BaseModel):
    probability: float
    confidence_interval: tuple[float, float]
    confidence_level: str
    top_positive_factors: list[str]
    top_negative_factors: list[str]
    vs_average_applicant: float
    score_needed_for_50pct: float
    fixes_for_10pct_boost: list[str]
    role_type: str
    seniority_level: str
    combined_score: float
    base_rate: float


class DualScoreResponse(BaseModel):
    ats_score: ScoreResponse
    standout_score: StandoutScoreResponse
    combined_score: float
    combined_grade: str
    total_dimensions: int
    summary: str
    callback_prediction: Optional[CallbackPredictionResponse] = None


@router.post("/{resume_id}/score/dual", response_model=DualScoreResponse)
async def dual_score_endpoint(
    resume_id: str,
    request: ScoreRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Score a resume on all 22 dimensions: 14 ATS + 8 Standout."""
    resume = load_user_resume(resume_id, user_id)
    jd = parse_jd(request.jd_text)
    _jd_store[jd.id] = jd

    from backend.agents.tailor.agent import TailorAgent
    agent = TailorAgent()
    result = await agent.score_dual(resume, jd, role_type=request.role_type, seniority=request.seniority)

    return DualScoreResponse(
        ats_score=ScoreResponse(
            total_score=result.ats.total_score, letter_grade=result.ats.letter_grade,
            dimension_scores=[
                DimensionScoreResponse(
                    dimension_id=d.dimension_id, dimension_name=d.dimension_name,
                    raw_score=d.raw_score, weighted_score=d.weighted_score,
                    weight=d.weight, explanation=d.explanation,
                    issues=d.issues, suggestions=d.suggestions, priority=d.priority,
                )
                for d in result.ats.dimension_scores
            ],
            top_3_issues=result.ats.top_3_issues, top_3_wins=result.ats.top_3_wins,
            predicted_ats_pass=result.ats.predicted_ats_pass,
            role_type=result.ats.role_type, seniority_level=result.ats.seniority_level,
            weights_used=result.ats.weights_used,
        ),
        standout_score=StandoutScoreResponse(
            total_score=result.standout.total_score, letter_grade=result.standout.letter_grade,
            dimension_scores=[
                StandoutDimensionScoreResponse(
                    dimension_id=d.dimension_id, dimension_name=d.dimension_name,
                    raw_score=d.raw_score, weighted_score=d.weighted_score,
                    weight=d.weight, explanation=d.explanation,
                    issues=d.issues, suggestions=d.suggestions, priority=d.priority,
                )
                for d in result.standout.dimension_scores
            ],
            top_3_issues=result.standout.top_3_issues, top_3_wins=result.standout.top_3_wins,
            spike_detected=result.standout.spike_detected,
            role_type=result.standout.role_type, seniority_level=result.standout.seniority_level,
            weights_used=result.standout.weights_used,
            amplification_tips=result.standout.amplification_tips,
        ),
        combined_score=result.combined_score,
        combined_grade=result.combined_grade,
        total_dimensions=result.total_dimensions,
        summary=result.summary,
        callback_prediction=CallbackPredictionResponse(
            probability=result.callback_prediction.probability,
            confidence_interval=result.callback_prediction.confidence_interval,
            confidence_level=result.callback_prediction.confidence_level,
            top_positive_factors=result.callback_prediction.top_positive_factors,
            top_negative_factors=result.callback_prediction.top_negative_factors,
            vs_average_applicant=result.callback_prediction.vs_average_applicant,
            score_needed_for_50pct=result.callback_prediction.score_needed_for_50pct,
            fixes_for_10pct_boost=result.callback_prediction.fixes_for_10pct_boost,
            role_type=result.callback_prediction.role_type,
            seniority_level=result.callback_prediction.seniority_level,
            combined_score=result.callback_prediction.combined_score,
            base_rate=result.callback_prediction.base_rate,
        ) if result.callback_prediction else None,
    )


# ── Callback Prediction ───────────────────────────────────────────────────


@router.post("/{resume_id}/predict-callback", response_model=CallbackPredictionResponse)
async def predict_callback_endpoint(
    resume_id: str,
    request: ScoreRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Predict interview callback probability using the 22-dimension dual score."""
    resume = load_user_resume(resume_id, user_id)
    jd = parse_jd(request.jd_text)
    _jd_store[jd.id] = jd

    from backend.agents.tailor.agent import TailorAgent
    agent = TailorAgent()
    dual = await agent.score_dual(resume, jd, role_type=request.role_type, seniority=request.seniority)

    pred = dual.callback_prediction
    if pred is None:
        raise HTTPException(500, "Callback prediction not available")

    return CallbackPredictionResponse(
        probability=pred.probability,
        confidence_interval=pred.confidence_interval,
        confidence_level=pred.confidence_level,
        top_positive_factors=pred.top_positive_factors,
        top_negative_factors=pred.top_negative_factors,
        vs_average_applicant=pred.vs_average_applicant,
        score_needed_for_50pct=pred.score_needed_for_50pct,
        fixes_for_10pct_boost=pred.fixes_for_10pct_boost,
        role_type=pred.role_type,
        seniority_level=pred.seniority_level,
        combined_score=pred.combined_score,
        base_rate=pred.base_rate,
    )


# ── A/B Testing ───────────────────────────────────────────────────────────


class ABTestRequest(BaseModel):
    resume_b_text: str
    jd_text: str
    role_type: Optional[str] = None
    seniority: Optional[str] = None


class DimensionComparisonResponse(BaseModel):
    dimension_id: str
    dimension_name: str
    score_a: float
    score_b: float
    delta: float
    winner: str
    weight: float
    weighted_impact: float


class MergeSuggestionResponse(BaseModel):
    section: str
    recommendation: str
    reason: str


class ABTestResponse(BaseModel):
    version_a_id: str
    version_b_id: str
    jd_id: str
    version_a_ats: float
    version_b_ats: float
    version_a_standout: float
    version_b_standout: float
    version_a_combined: float
    version_b_combined: float
    version_a_callback: float
    version_b_callback: float
    overall_winner: str
    win_margin: float
    dimension_comparisons: list[DimensionComparisonResponse]
    a_advantages: list[str]
    b_advantages: list[str]
    merge_suggestions: list[MergeSuggestionResponse]
    recommendation: str
    role_type: str
    seniority_level: str


@router.post("/{resume_id}/ab-test", response_model=ABTestResponse)
async def ab_test_endpoint(
    resume_id: str,
    request: ABTestRequest,
    user_id: str = Depends(get_current_user_id),
):
    """A/B test two resume versions against the same JD on all 22 dimensions."""
    version_a = load_user_resume(resume_id, user_id)

    from backend.parsers.resume_parser import parse_resume_text
    version_b = parse_resume_text(request.resume_b_text)

    jd = parse_jd(request.jd_text)
    _jd_store[jd.id] = jd

    from backend.agents.tailor.ab_testing import ab_test_resumes
    result = await ab_test_resumes(version_a, version_b, jd, role_type=request.role_type, seniority=request.seniority)

    return ABTestResponse(
        version_a_id=result.version_a_id, version_b_id=result.version_b_id, jd_id=result.jd_id,
        version_a_ats=result.version_a_ats, version_b_ats=result.version_b_ats,
        version_a_standout=result.version_a_standout, version_b_standout=result.version_b_standout,
        version_a_combined=result.version_a_combined, version_b_combined=result.version_b_combined,
        version_a_callback=result.version_a_callback, version_b_callback=result.version_b_callback,
        overall_winner=result.overall_winner, win_margin=result.win_margin,
        dimension_comparisons=[
            DimensionComparisonResponse(
                dimension_id=c.dimension_id, dimension_name=c.dimension_name,
                score_a=c.score_a, score_b=c.score_b, delta=c.delta,
                winner=c.winner, weight=c.weight, weighted_impact=c.weighted_impact,
            ) for c in result.dimension_comparisons
        ],
        a_advantages=result.a_advantages, b_advantages=result.b_advantages,
        merge_suggestions=[
            MergeSuggestionResponse(section=m.section, recommendation=m.recommendation, reason=m.reason)
            for m in result.merge_suggestions
        ],
        recommendation=result.recommendation,
        role_type=result.role_type, seniority_level=result.seniority_level,
    )


# ── Skill Gap Analysis ────────────────────────────────────────────────────


class SkillGapResponse(BaseModel):
    skill: str
    category: str
    jd_context: str
    score_impact: float
    difficulty: str
    suggestion: str


class SkillGapAnalysisResponse(BaseModel):
    total_gaps: int
    critical_gaps: list[SkillGapResponse]
    recommended_gaps: list[SkillGapResponse]
    bonus_gaps: list[SkillGapResponse]
    matched_skills: list[str]
    match_percentage: float
    total_potential_score_gain: float
    top_3_highest_impact_gaps: list[SkillGapResponse]
    quick_wins: list[str]
    short_term: list[str]
    long_term: list[str]


class SkillGapRequest(BaseModel):
    jd_text: str


@router.post("/{resume_id}/skill-gaps", response_model=SkillGapAnalysisResponse)
async def skill_gap_endpoint(
    resume_id: str,
    request: SkillGapRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Analyze skill gaps between a resume and a JD."""
    resume = load_user_resume(resume_id, user_id)
    jd = parse_jd(request.jd_text)

    from backend.agents.tailor.skill_gap import analyze_skill_gaps
    result = analyze_skill_gaps(resume, jd)

    def _gap_resp(g):
        return SkillGapResponse(
            skill=g.skill, category=g.category, jd_context=g.jd_context,
            score_impact=g.score_impact, difficulty=g.difficulty, suggestion=g.suggestion,
        )

    return SkillGapAnalysisResponse(
        total_gaps=result.total_gaps,
        critical_gaps=[_gap_resp(g) for g in result.critical_gaps],
        recommended_gaps=[_gap_resp(g) for g in result.recommended_gaps],
        bonus_gaps=[_gap_resp(g) for g in result.bonus_gaps],
        matched_skills=result.matched_skills,
        match_percentage=result.match_percentage,
        total_potential_score_gain=result.total_potential_score_gain,
        top_3_highest_impact_gaps=[_gap_resp(g) for g in result.top_3_highest_impact_gaps],
        quick_wins=result.quick_wins,
        short_term=result.short_term,
        long_term=result.long_term,
    )


# ── Batch Scoring ─────────────────────────────────────────────────────────


class BatchScoreEntryResponse(BaseModel):
    jd_id: str
    jd_title: str
    jd_company: str
    ats_score: float
    standout_score: float
    combined_score: float
    callback_probability: float
    tier: str
    top_gap: str
    company_profile_used: str


class BatchScoreResultResponse(BaseModel):
    resume_id: str
    entries: list[BatchScoreEntryResponse]
    best_fit: Optional[BatchScoreEntryResponse] = None
    worst_fit: Optional[BatchScoreEntryResponse] = None
    highest_callback: Optional[BatchScoreEntryResponse] = None
    avg_combined_score: float
    avg_callback_probability: float
    common_gaps: list[str]
    strongest_dimension_overall: str
    weakest_dimension_overall: str
    recommendation: str


class BatchScoreRequest(BaseModel):
    jd_texts: list[str]


@router.post("/{resume_id}/batch-score", response_model=BatchScoreResultResponse)
async def batch_score_endpoint(
    resume_id: str,
    request: BatchScoreRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Score a resume against multiple JDs simultaneously."""
    if len(request.jd_texts) > 10:
        raise HTTPException(400, "Maximum 10 JDs per batch")

    resume = load_user_resume(resume_id, user_id)
    jds = [parse_jd(text) for text in request.jd_texts]

    from backend.agents.tailor.batch_scorer import batch_score
    result = await batch_score(resume, jds)

    def _entry(e):
        return BatchScoreEntryResponse(
            jd_id=e.jd_id, jd_title=e.jd_title, jd_company=e.jd_company,
            ats_score=e.ats_score, standout_score=e.standout_score,
            combined_score=e.combined_score, callback_probability=e.callback_probability,
            tier=e.tier, top_gap=e.top_gap, company_profile_used=e.company_profile_used,
        )

    return BatchScoreResultResponse(
        resume_id=result.resume_id,
        entries=[_entry(e) for e in result.entries],
        best_fit=_entry(result.best_fit) if result.best_fit else None,
        worst_fit=_entry(result.worst_fit) if result.worst_fit else None,
        highest_callback=_entry(result.highest_callback) if result.highest_callback else None,
        avg_combined_score=result.avg_combined_score,
        avg_callback_probability=result.avg_callback_probability,
        common_gaps=result.common_gaps,
        strongest_dimension_overall=result.strongest_dimension_overall,
        weakest_dimension_overall=result.weakest_dimension_overall,
        recommendation=result.recommendation,
    )


# ── Version History ───────────────────────────────────────────────────────


class ResumeVersionResponse(BaseModel):
    version_id: str
    resume_id: str
    version_number: int
    created_at: str
    source: str
    target_jd_id: Optional[str] = None
    target_company: Optional[str] = None
    ats_score: float
    standout_score: float
    combined_score: float
    callback_probability: float
    tier: str
    change_summary: str
    changes_made: int


class ImprovementTrendResponse(BaseModel):
    versions: int
    first_score: float
    latest_score: float
    improvement: float
    trend: str


@router.get("/{resume_id}/versions", response_model=list[ResumeVersionResponse])
async def get_versions(resume_id: str, user_id: str = Depends(get_current_user_id)):
    """Get all saved versions of a resume with their scores."""
    load_user_resume(resume_id, user_id)  # ownership check
    from backend.memory.version_store import version_store
    versions = version_store.get_versions(resume_id)
    return [
        ResumeVersionResponse(
            version_id=v.version_id, resume_id=v.resume_id,
            version_number=v.version_number, created_at=v.created_at,
            source=v.source, target_jd_id=v.target_jd_id,
            target_company=v.target_company, ats_score=v.ats_score,
            standout_score=v.standout_score, combined_score=v.combined_score,
            callback_probability=v.callback_probability, tier=v.tier,
            change_summary=v.change_summary, changes_made=v.changes_made,
        )
        for v in versions
    ]


@router.get("/{resume_id}/versions/trend", response_model=ImprovementTrendResponse)
async def get_version_trend(resume_id: str, user_id: str = Depends(get_current_user_id)):
    """Get improvement trend data for a resume's version history."""
    load_user_resume(resume_id, user_id)  # ownership check
    from backend.memory.version_store import version_store
    trend = version_store.get_improvement_trend(resume_id)
    return ImprovementTrendResponse(
        versions=trend.versions, first_score=trend.first_score,
        latest_score=trend.latest_score, improvement=trend.improvement,
        trend=trend.trend,
    )


@router.get("/{resume_id}/score/{jd_id}")
async def get_cached_score(
    resume_id: str,
    jd_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get a previously computed score. Returns 404 if not cached."""
    resume = load_user_resume(resume_id, user_id)
    if jd_id not in _jd_store:
        raise HTTPException(404, "JD not found — score first using POST /{resume_id}/score")

    jd = _jd_store[jd_id]
    from backend.agents.tailor.weightage.scorer_engine import score_resume
    result = await score_resume(resume, jd)

    return ScoreResponse(
        total_score=result.total_score, letter_grade=result.letter_grade,
        dimension_scores=[
            DimensionScoreResponse(
                dimension_id=d.dimension_id, dimension_name=d.dimension_name,
                raw_score=d.raw_score, weighted_score=d.weighted_score,
                weight=d.weight, explanation=d.explanation,
                issues=d.issues, suggestions=d.suggestions, priority=d.priority,
            )
            for d in result.dimension_scores
        ],
        top_3_issues=result.top_3_issues, top_3_wins=result.top_3_wins,
        predicted_ats_pass=result.predicted_ats_pass,
        role_type=result.role_type, seniority_level=result.seniority_level,
        weights_used=result.weights_used,
    )
