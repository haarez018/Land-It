"""Cover letter generation endpoints — Pitcher agent."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth_deps import get_current_user_id
from backend.parsers.jd_parser import parse_jd
from backend.parsers.schemas import Resume
from backend.api.routes.resume import load_user_resume

router = APIRouter()


# ── Request / Response Models ──────────────────────────────────────────────


class GenerateLetterRequest(BaseModel):
    resume_id: str
    jd_text: str
    writing_samples: list[str] = []


class VoiceProfileResponse(BaseModel):
    avg_sentence_length: float
    formality_level: str
    characteristic_phrases: list[str]
    punctuation_style: str
    enthusiasm_markers: list[str]
    hedging_frequency: str
    storytelling_style: str
    tone: str
    vocabulary_complexity: str


class CompanyContextResponse(BaseModel):
    company_name: str
    mission: str
    values: list[str]
    products: list[str]
    culture_signals: list[str]
    industry: str
    tone: str
    key_talking_points: list[str]


class CoverLetterResponse(BaseModel):
    text: str
    word_count: int
    paragraphs: int
    company_name: str
    role_title: str
    voice_match_score: float
    company_personalization_score: float
    requirements_addressed: list[str]
    verification_notes: list[str]


class PitcherResponse(BaseModel):
    cover_letter: CoverLetterResponse
    voice_profile: VoiceProfileResponse
    company_context: CompanyContextResponse
    alternative_openings: list[str]


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.post("/generate", response_model=PitcherResponse)
async def generate_cover_letter(
    request: GenerateLetterRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Generate a personalized cover letter for a resume + JD."""
    resume = load_user_resume(request.resume_id, user_id)
    jd = parse_jd(request.jd_text)

    from backend.agents.pitcher.agent import PitcherAgent

    agent = PitcherAgent()
    result = await agent.generate(
        resume, jd, writing_samples=request.writing_samples or []
    )

    cl = result.cover_letter
    vp = result.voice_profile
    cc = result.company_context

    return PitcherResponse(
        cover_letter=CoverLetterResponse(
            text=cl.text,
            word_count=cl.word_count,
            paragraphs=cl.paragraphs,
            company_name=cl.company_name,
            role_title=cl.role_title,
            voice_match_score=cl.voice_match_score,
            company_personalization_score=cl.company_personalization_score,
            requirements_addressed=cl.requirements_addressed,
            verification_notes=cl.verification_notes,
        ),
        voice_profile=VoiceProfileResponse(
            avg_sentence_length=vp.avg_sentence_length,
            formality_level=vp.formality_level,
            characteristic_phrases=vp.characteristic_phrases,
            punctuation_style=vp.punctuation_style,
            enthusiasm_markers=vp.enthusiasm_markers,
            hedging_frequency=vp.hedging_frequency,
            storytelling_style=vp.storytelling_style,
            tone=vp.tone,
            vocabulary_complexity=vp.vocabulary_complexity,
        ),
        company_context=CompanyContextResponse(
            company_name=cc.company_name,
            mission=cc.mission,
            values=cc.values,
            products=cc.products,
            culture_signals=cc.culture_signals,
            industry=cc.industry,
            tone=cc.tone,
            key_talking_points=cc.key_talking_points,
        ),
        alternative_openings=result.alternative_openings,
    )


@router.post("/voice-analyze", response_model=VoiceProfileResponse)
async def analyze_voice_endpoint(samples: list[str]):
    """Analyze writing samples to extract voice profile."""
    from backend.agents.pitcher.voice_analyzer import analyze_voice

    voice = analyze_voice(samples)
    return VoiceProfileResponse(
        avg_sentence_length=voice.avg_sentence_length,
        formality_level=voice.formality_level,
        characteristic_phrases=voice.characteristic_phrases,
        punctuation_style=voice.punctuation_style,
        enthusiasm_markers=voice.enthusiasm_markers,
        hedging_frequency=voice.hedging_frequency,
        storytelling_style=voice.storytelling_style,
        tone=voice.tone,
        vocabulary_complexity=voice.vocabulary_complexity,
    )
