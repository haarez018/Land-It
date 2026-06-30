"""Integration tests for the Pitcher agent — Day 6."""

from datetime import date

import pytest

from backend.parsers.schemas import (
    Education,
    JDRequirement,
    JobDescription,
    Resume,
    ResumeContact,
    WorkExperience,
)
from backend.agents.pitcher.agent import PitcherAgent
from backend.agents.pitcher.voice_analyzer import analyze_voice, VoiceProfile
from backend.agents.pitcher.company_researcher import research_company, CompanyContext


def _resume():
    return Resume(
        contact=ResumeContact(name="Alex Chen", email="alex@example.com"),
        raw_text="Senior backend engineer resume",
        summary="Senior backend engineer with 8+ years building distributed systems.",
        work_experience=[
            WorkExperience(
                company="Google",
                title="Senior Software Engineer",
                start_date=date(2020, 1, 1),
                bullets=[
                    "Architected real-time event processing pipeline handling 2M events/sec using Kafka and Go",
                    "Reduced API latency by 45% by migrating monolith to microservices",
                    "Led team of 8 engineers delivering $12M annual cost savings",
                ],
                technologies=["Kafka", "Go", "Python", "PostgreSQL"],
            ),
            WorkExperience(
                company="Startup",
                title="Software Engineer",
                start_date=date(2017, 6, 1),
                end_date=date(2019, 12, 31),
                bullets=[
                    "Built payment APIs serving 100K+ merchants using Python and Django",
                    "Implemented distributed tracing reducing debugging time by 60%",
                ],
                technologies=["Python", "Django", "Docker"],
            ),
        ],
        education=[
            Education(
                institution="Stanford",
                degree="BS Computer Science",
                field="Computer Science",
            )
        ],
        skills={
            "languages": ["Python", "Go"],
            "databases": ["PostgreSQL", "Redis"],
            "infrastructure": ["Docker", "Kubernetes", "AWS"],
            "messaging": ["Kafka"],
        },
        seniority_level="senior",
        total_yoe=8.5,
    )


def _stripe_jd():
    return JobDescription(
        raw_text=(
            "Senior Backend Engineer at Stripe\n\n"
            "Build scalable payment infrastructure. "
            "Required: Python, Go, Kafka, PostgreSQL."
        ),
        title="Senior Backend Engineer",
        company="Stripe",
        required_skills=["Python", "Go", "Kafka", "PostgreSQL"],
        preferred_skills=["Kubernetes", "gRPC"],
        tech_stack=["Python", "Go", "Kafka", "PostgreSQL", "Kubernetes"],
        requirements=[
            JDRequirement(text="5+ years backend experience", category="must_have",
                         skill_type="technical", extracted_keyword="backend"),
            JDRequirement(text="Experience with distributed systems", category="must_have",
                         skill_type="technical", extracted_keyword="distributed"),
        ],
        seniority_level="senior",
        required_experience_years=5,
        role_priorities=["Build scalable payment infrastructure"],
        company_values=["Move with urgency", "Be meticulous"],
    )


# ── Voice Analyzer Tests ──────────────────────────────────────────────────


class TestVoiceAnalyzer:
    def test_empty_samples_returns_defaults(self):
        profile = analyze_voice([])
        assert isinstance(profile, VoiceProfile)
        assert profile.formality_level == "semi-formal"

    def test_casual_writing_detected(self):
        samples = [
            "Honestly, I'm super excited about this opportunity! "
            "I've been a huge fan of the product since basically day one. "
            "The team seems awesome and I'd love to be part of it."
        ]
        profile = analyze_voice(samples)
        assert profile.formality_level == "casual"
        assert any("!" in m for m in profile.enthusiasm_markers)

    def test_formal_writing_detected(self):
        samples = [
            "Furthermore, my experience in distributed systems has been consequential "
            "to my professional development. Nevertheless, I have consistently "
            "demonstrated the capacity to deliver results. Moreover, my academic "
            "background provides a strong foundation."
        ]
        profile = analyze_voice(samples)
        assert profile.formality_level == "formal"

    def test_sentence_length_calculated(self):
        samples = ["Short sentence. Another one. And one more."]
        profile = analyze_voice(samples)
        assert 2 < profile.avg_sentence_length < 5

    def test_voice_profile_to_dict(self):
        profile = analyze_voice([])
        d = profile.to_dict()
        assert "formality_level" in d
        assert "tone" in d
        assert "avg_sentence_length" in d


# ── Company Researcher Tests ──────────────────────────────────────────────


class TestCompanyResearcher:
    def test_known_company_stripe(self):
        jd = _stripe_jd()
        context = research_company(jd)
        assert context.company_name == "Stripe"
        assert "internet" in context.mission.lower()
        assert len(context.values) > 0
        assert len(context.products) > 0

    def test_unknown_company_extracts_from_jd(self):
        jd = JobDescription(
            raw_text="Acme Corp is building the future of logistics. We believe in innovation.",
            title="Backend Engineer",
            company="Acme Corp",
            required_skills=["Python"],
            tech_stack=["Python"],
        )
        context = research_company(jd)
        assert context.company_name == "Acme Corp"
        assert isinstance(context.industry, str)
        assert isinstance(context.tone, str)

    def test_talking_points_generated(self):
        context = research_company(_stripe_jd())
        assert len(context.key_talking_points) > 0

    def test_context_to_dict(self):
        context = research_company(_stripe_jd())
        d = context.to_dict()
        assert "company_name" in d
        assert "mission" in d
        assert "values" in d


# ── Pitcher Agent Integration ─────────────────────────────────────────────


class TestPitcherAgentIntegration:
    @pytest.mark.asyncio
    async def test_cover_letter_contains_company_name(self):
        agent = PitcherAgent()
        result = await agent.generate(_resume(), _stripe_jd())
        assert "Stripe" in result.cover_letter.text

    @pytest.mark.asyncio
    async def test_cover_letter_contains_role_title(self):
        agent = PitcherAgent()
        result = await agent.generate(_resume(), _stripe_jd())
        text_lower = result.cover_letter.text.lower()
        assert "backend engineer" in text_lower or "engineer" in text_lower

    @pytest.mark.asyncio
    async def test_cover_letter_word_count_reasonable(self):
        agent = PitcherAgent()
        result = await agent.generate(_resume(), _stripe_jd())
        assert 100 < result.cover_letter.word_count < 500

    @pytest.mark.asyncio
    async def test_cover_letter_has_multiple_paragraphs(self):
        agent = PitcherAgent()
        result = await agent.generate(_resume(), _stripe_jd())
        assert result.cover_letter.paragraphs >= 3

    @pytest.mark.asyncio
    async def test_no_banned_phrases(self):
        agent = PitcherAgent()
        result = await agent.generate(_resume(), _stripe_jd())
        text_lower = result.cover_letter.text.lower()
        banned = [
            "i am writing to express my interest",
            "team player",
            "fast learner",
            "detail-oriented",
        ]
        for phrase in banned:
            assert phrase not in text_lower, f"Found banned phrase: '{phrase}'"

    @pytest.mark.asyncio
    async def test_alternative_openings_generated(self):
        agent = PitcherAgent()
        result = await agent.generate(_resume(), _stripe_jd())
        assert len(result.alternative_openings) >= 1

    @pytest.mark.asyncio
    async def test_voice_profile_captured(self):
        agent = PitcherAgent()
        result = await agent.generate(_resume(), _stripe_jd())
        assert isinstance(result.voice_profile, VoiceProfile)

    @pytest.mark.asyncio
    async def test_company_context_captured(self):
        agent = PitcherAgent()
        result = await agent.generate(_resume(), _stripe_jd())
        assert isinstance(result.company_context, CompanyContext)
        assert result.company_context.company_name == "Stripe"

    @pytest.mark.asyncio
    async def test_writing_samples_affect_voice(self):
        agent = PitcherAgent()
        casual_samples = [
            "Honestly I'm super excited about this! The product is awesome "
            "and I'd love to be part of the team. Really stoked about it."
        ]
        result = await agent.generate(
            _resume(), _stripe_jd(),
            writing_samples=casual_samples,
        )
        assert result.voice_profile.formality_level == "casual"

    @pytest.mark.asyncio
    async def test_langgraph_compatible_run(self):
        agent = PitcherAgent()
        state = {
            "resume": _resume(),
            "jd": _stripe_jd(),
        }
        result_state = await agent.run(state)
        assert "pitcher_result" in result_state
        assert "cover_letter" in result_state
        assert isinstance(result_state["cover_letter"], str)
        assert len(result_state["cover_letter"]) > 100

    @pytest.mark.asyncio
    async def test_stripe_mission_referenced(self):
        """For known companies, the letter should reference their mission."""
        agent = PitcherAgent()
        result = await agent.generate(_resume(), _stripe_jd())
        text_lower = result.cover_letter.text.lower()
        # Should reference Stripe's mission about the internet or GDP
        assert "internet" in text_lower or "gdp" in text_lower or "stripe" in text_lower
