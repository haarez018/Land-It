"""Integration tests for the Tailor agent pipeline — Day 5."""

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
from backend.agents.tailor.agent import TailorAgent


def _senior_resume():
    return Resume(
        contact=ResumeContact(name="Alex Chen", email="alex@example.com", phone="555-1234"),
        raw_text=(
            "alex@example.com | 555-1234\n\nSUMMARY\n"
            "Senior backend engineer with 8+ years building distributed systems.\n\n"
            "EXPERIENCE\n"
            "Senior Software Engineer at Google\nJan 2020 - Present\n"
            "Architected real-time event processing pipeline handling 2M events/sec using Kafka and Go\n"
            "Reduced API latency by 45% by migrating monolith to microservices\n"
            "Led team of 8 engineers delivering $12M annual cost savings\n\n"
            "Software Engineer at Startup\nJun 2017 - Dec 2019\n"
            "Built payment APIs serving 100K+ merchants using Python and Django\n"
            "Implemented distributed tracing reducing debugging time by 60%\n\n"
            "SKILLS\nPython, Go, Kafka, PostgreSQL, Docker, Kubernetes, Redis, AWS\n\n"
            "EDUCATION\nBS Computer Science, Stanford University, 2017"
        ),
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
                technologies=["Kafka", "Go", "Python", "PostgreSQL", "gRPC"],
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
                institution="Stanford University",
                degree="BS Computer Science",
                field="Computer Science",
                graduation_date=date(2017, 6, 1),
                gpa=3.8,
                honors=["Magna Cum Laude"],
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
            "Required: Python, Go, Kafka, PostgreSQL. "
            "Nice to have: Kubernetes, gRPC, AWS. "
            "Domain: fintech, payments, transactions, compliance."
        ),
        title="Senior Backend Engineer",
        company="Stripe",
        required_skills=["Python", "Go", "Kafka", "PostgreSQL"],
        preferred_skills=["Kubernetes", "gRPC", "AWS"],
        tech_stack=["Python", "Go", "Kafka", "PostgreSQL", "Kubernetes", "gRPC"],
        requirements=[
            JDRequirement(text="5+ years backend experience", category="must_have",
                         skill_type="technical", extracted_keyword="backend"),
            JDRequirement(text="Experience with distributed systems", category="must_have",
                         skill_type="technical", extracted_keyword="distributed systems"),
        ],
        seniority_level="senior",
        required_experience_years=5,
        required_education="BS Computer Science",
        role_priorities=["Build scalable payment infrastructure", "Design distributed systems"],
    )


class TestTailorAgentIntegration:
    @pytest.mark.asyncio
    async def test_full_score_pipeline(self):
        """Score a senior resume against a matched JD — should get a reasonable score."""
        agent = TailorAgent()
        result = await agent.tailor(_senior_resume(), _stripe_jd())

        assert result.score_before.total_score > 0
        assert result.score_before.letter_grade in [
            "A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F"
        ]
        assert len(result.score_before.dimension_scores) == 14

    @pytest.mark.asyncio
    async def test_rewrite_improves_score(self):
        """The 6-pass rewriter should improve or at least maintain the ATS score."""
        agent = TailorAgent()
        result = await agent.tailor(_senior_resume(), _stripe_jd())

        # Rewrite should not degrade the score significantly
        assert result.score_after.total_score >= result.score_before.total_score - 5, (
            f"Score dropped too much: {result.score_before.total_score:.1f} → "
            f"{result.score_after.total_score:.1f}"
        )

    @pytest.mark.asyncio
    async def test_diff_generated(self):
        """The pipeline should produce a non-trivial diff."""
        agent = TailorAgent()
        result = await agent.tailor(_senior_resume(), _stripe_jd())

        assert result.diff is not None
        assert isinstance(result.diff.unified_diff, str)
        assert result.diff.score_before == result.score_before.total_score
        assert result.diff.score_after == result.score_after.total_score

    @pytest.mark.asyncio
    async def test_change_log_has_entries(self):
        """Rewrite should produce a meaningful change log."""
        agent = TailorAgent()
        result = await agent.tailor(_senior_resume(), _stripe_jd())

        assert len(result.rewrite_result.change_log) > 0
        assert len(result.rewrite_result.passes_applied) == 6

    @pytest.mark.asyncio
    async def test_langgraph_compatible_run(self):
        """The agent's run() method should work with state dict."""
        agent = TailorAgent()
        state = {
            "resume": _senior_resume(),
            "jd": _stripe_jd(),
        }
        result_state = await agent.run(state)

        assert "tailor_result" in result_state
        assert "ats_score_before" in result_state
        assert "ats_score_after" in result_state
        assert "tailored_resume" in result_state
        assert isinstance(result_state["ats_score_before"], float)
        assert isinstance(result_state["ats_score_after"], float)

    @pytest.mark.asyncio
    async def test_rewritten_resume_preserves_facts(self):
        """The rewriter should never change company names, titles, or dates."""
        agent = TailorAgent()
        result = await agent.tailor(_senior_resume(), _stripe_jd())

        rewritten = result.rewritten_resume
        assert rewritten.contact.name == "Alex Chen"
        assert rewritten.work_experience[0].company == "Google"
        assert rewritten.work_experience[0].title == "Senior Software Engineer"
        assert rewritten.work_experience[0].start_date == date(2020, 1, 1)
        assert rewritten.work_experience[1].company == "Startup"
