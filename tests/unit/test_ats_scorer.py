"""Unit tests for all 14 ATS scorer functions."""

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
from backend.agents.tailor.ats_scorer import (
    _clamp,
    _stem,
    keyword_density_scorer,
    skill_depth_scorer,
    tech_stack_scorer,
    experience_relevance_scorer,
    quantified_impact_scorer,
    action_verb_scorer,
    section_ordering_scorer,
    bullet_quality_scorer,
    ats_parsability_scorer,
    seniority_calibration_scorer,
    domain_knowledge_scorer,
    education_relevance_scorer,
    semantic_similarity_scorer,
    voice_alignment_scorer,
)


# ── Test fixtures ───────────────────────────────────────────────────────────


def _contact() -> ResumeContact:
    return ResumeContact(name="Alex Chen", email="alex@example.com", phone="555-1234")


def _make_resume(
    *,
    raw_text: str = "",
    summary: str | None = None,
    work_experience: list[WorkExperience] | None = None,
    education: list[Education] | None = None,
    skills: dict[str, list[str]] | None = None,
    seniority_level: str = "mid",
    total_yoe: float = 4.0,
    primary_domain: str = "general",
) -> Resume:
    return Resume(
        contact=_contact(),
        raw_text=raw_text
        or "EXPERIENCE\nSoftware Engineer at Acme Corp\nSKILLS\nPython\nEDUCATION\nBS Computer Science",
        summary=summary,
        work_experience=work_experience or [],
        education=education or [],
        skills=skills or {},
        seniority_level=seniority_level,
        total_yoe=total_yoe,
        primary_domain=primary_domain,
    )


_SENTINEL = object()


def _make_jd(
    *,
    raw_text: str = "",
    title: str = "Senior Backend Engineer",
    company: str = "Stripe",
    required_skills: list[str] | None | object = _SENTINEL,
    preferred_skills: list[str] | None | object = _SENTINEL,
    tech_stack: list[str] | None | object = _SENTINEL,
    requirements: list[JDRequirement] | None | object = _SENTINEL,
    seniority_level: str = "senior",
    required_experience_years: int | None = 5,
    required_education: str | None = None,
    role_priorities: list[str] | None | object = _SENTINEL,
) -> JobDescription:
    return JobDescription(
        raw_text=raw_text or "We need a senior backend engineer skilled in Python, Go, Kafka, PostgreSQL.",
        title=title,
        company=company,
        required_skills=["Python", "Go"] if required_skills is _SENTINEL else (required_skills or []),
        preferred_skills=["Kafka"] if preferred_skills is _SENTINEL else (preferred_skills or []),
        tech_stack=["Python", "Go", "Kafka", "PostgreSQL"] if tech_stack is _SENTINEL else (tech_stack or []),
        requirements=[] if requirements is _SENTINEL else (requirements or []),
        seniority_level=seniority_level,
        required_experience_years=required_experience_years,
        required_education=required_education,
        role_priorities=[] if role_priorities is _SENTINEL else (role_priorities or []),
    )


# Shared rich resume fixture for integration-style tests
SENIOR_BACKEND_RESUME = _make_resume(
    raw_text=(
        "alex@example.com | 555-1234\n\nSUMMARY\n"
        "Senior backend engineer with 8+ years of experience building scalable "
        "distributed systems using Python, Go, and Kafka.\n\n"
        "EXPERIENCE\n"
        "Senior Software Engineer at Google\nJan 2020 - Present\n"
        "Architected a real-time event processing pipeline handling 2M events/sec using Kafka and Go\n"
        "Reduced API latency by 45% by migrating monolith to microservices architecture\n"
        "Led team of 8 engineers delivering $12M annual cost savings through infrastructure optimization\n"
        "Designed PostgreSQL schema supporting 50M+ records with sub-10ms query times\n\n"
        "Software Engineer at Stripe\nJun 2017 - Dec 2019\n"
        "Built payment processing APIs serving 100K+ merchants using Python and Django\n"
        "Implemented distributed tracing reducing debugging time by 60%\n"
        "Deployed Docker containers on Kubernetes for zero-downtime releases\n\n"
        "SKILLS\nPython, Go, Kafka, PostgreSQL, Docker, Kubernetes, Redis, AWS, gRPC\n\n"
        "EDUCATION\nBS Computer Science, Stanford University, 2017\nGPA: 3.8, Magna Cum Laude"
    ),
    summary="Senior backend engineer with 8+ years of experience building scalable distributed systems using Python, Go, and Kafka.",
    work_experience=[
        WorkExperience(
            company="Google",
            title="Senior Software Engineer",
            start_date=date(2020, 1, 1),
            end_date=None,
            bullets=[
                "Architected a real-time event processing pipeline handling 2M events/sec using Kafka and Go",
                "Reduced API latency by 45% by migrating monolith to microservices architecture",
                "Led team of 8 engineers delivering $12M annual cost savings through infrastructure optimization",
                "Designed PostgreSQL schema supporting 50M+ records with sub-10ms query times",
            ],
            technologies=["Kafka", "Go", "Python", "PostgreSQL", "gRPC"],
            impact_metrics=["2M events/sec", "45% latency reduction", "$12M savings"],
        ),
        WorkExperience(
            company="Stripe",
            title="Software Engineer",
            start_date=date(2017, 6, 1),
            end_date=date(2019, 12, 31),
            bullets=[
                "Built payment processing APIs serving 100K+ merchants using Python and Django",
                "Implemented distributed tracing reducing debugging time by 60%",
                "Deployed Docker containers on Kubernetes for zero-downtime releases",
            ],
            technologies=["Python", "Django", "Docker", "Kubernetes"],
            impact_metrics=["100K+ merchants", "60% reduction"],
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

STRIPE_BACKEND_JD = _make_jd(
    raw_text=(
        "Senior Backend Engineer at Stripe\n\n"
        "We are looking for a Senior Backend Engineer to build scalable payment "
        "infrastructure. You will design distributed systems processing billions "
        "of transactions. Required: 5+ years backend experience, Python, Go, "
        "Kafka, PostgreSQL. Nice to have: Kubernetes, gRPC, AWS. "
        "Domain: fintech, payments, transactions, compliance. "
        "BS in Computer Science or equivalent required."
    ),
    title="Senior Backend Engineer",
    company="Stripe",
    required_skills=["Python", "Go", "Kafka", "PostgreSQL"],
    preferred_skills=["Kubernetes", "gRPC", "AWS"],
    tech_stack=["Python", "Go", "Kafka", "PostgreSQL", "Kubernetes", "gRPC"],
    requirements=[
        JDRequirement(text="5+ years backend experience", category="must_have", skill_type="technical", extracted_keyword="backend"),
        JDRequirement(text="Python proficiency", category="must_have", skill_type="technical", extracted_keyword="Python"),
        JDRequirement(text="Experience with distributed systems", category="must_have", skill_type="technical", extracted_keyword="distributed systems"),
        JDRequirement(text="Kubernetes experience", category="nice_to_have", skill_type="tool", extracted_keyword="Kubernetes"),
    ],
    seniority_level="senior",
    required_experience_years=5,
    required_education="BS Computer Science",
    role_priorities=["Build scalable payment infrastructure", "Design distributed systems", "Process billions of transactions"],
)


# ── Helper tests ────────────────────────────────────────────────────────────


class TestHelpers:
    def test_clamp_within_bounds(self):
        assert _clamp(50.0) == 50.0

    def test_clamp_below_zero(self):
        assert _clamp(-10.0) == 0.0

    def test_clamp_above_hundred(self):
        assert _clamp(120.0) == 100.0

    def test_stem_removes_suffix(self):
        assert _stem("engineering") == "engineer"

    def test_stem_short_word_untouched(self):
        assert _stem("go") == "go"

    def test_stem_no_match(self):
        assert _stem("python") == "python"


# ── 1. Keyword Density ─────────────────────────────────────────────────────


class TestKeywordDensityScorer:
    @pytest.mark.asyncio
    async def test_high_match_scores_high(self):
        score, expl, issues, suggestions = await keyword_density_scorer(
            SENIOR_BACKEND_RESUME, STRIPE_BACKEND_JD
        )
        assert score >= 70, f"Senior resume vs matched JD should score high, got {score}"
        assert "required" in expl.lower()

    @pytest.mark.asyncio
    async def test_missing_keywords_flagged(self):
        resume = _make_resume(
            raw_text="I am a designer who works with Figma and Sketch",
            skills={"design": ["Figma", "Sketch"]},
        )
        score, expl, issues, _ = await keyword_density_scorer(resume, STRIPE_BACKEND_JD)
        assert score < 50, f"Irrelevant resume should score low, got {score}"
        assert any("missing" in i.lower() or "Missing" in i for i in issues)

    @pytest.mark.asyncio
    async def test_no_jd_keywords_returns_neutral(self):
        jd = _make_jd(required_skills=[], preferred_skills=[], requirements=[])
        score, _, _, _ = await keyword_density_scorer(SENIOR_BACKEND_RESUME, jd)
        assert score == 75.0

    @pytest.mark.asyncio
    async def test_stuffing_penalty(self):
        resume = _make_resume(
            raw_text="python python python python python python python go kafka postgresql",
            skills={"lang": ["Python"]},
        )
        jd = _make_jd(required_skills=["python"], preferred_skills=["go"])
        score, _, issues, _ = await keyword_density_scorer(resume, jd)
        assert any("stuffing" in i.lower() for i in issues)


# ── 2. Skill Depth ─────────────────────────────────────────────────────────


class TestSkillDepthScorer:
    @pytest.mark.asyncio
    async def test_demonstrated_skills_score_higher(self):
        score, expl, _, _ = await skill_depth_scorer(
            SENIOR_BACKEND_RESUME, STRIPE_BACKEND_JD
        )
        assert score >= 60, f"Demonstrated skills should score high, got {score}"
        assert "demonstrated" in expl.lower()

    @pytest.mark.asyncio
    async def test_skills_only_listed_get_partial_credit(self):
        resume = _make_resume(
            raw_text="SKILLS\nPython, Go\nEXPERIENCE\nDid nothing relevant",
            skills={"languages": ["Python", "Go"]},
            work_experience=[
                WorkExperience(
                    company="X", title="Eng", start_date=date(2022, 1, 1),
                    bullets=["Managed team meetings and schedules"],
                )
            ],
        )
        jd = _make_jd(required_skills=["Python", "Go"], preferred_skills=[], tech_stack=["Python", "Go"])
        score, _, issues, _ = await skill_depth_scorer(resume, jd)
        assert any("listed" in i.lower() for i in issues)

    @pytest.mark.asyncio
    async def test_missing_skills_flagged(self):
        resume = _make_resume(raw_text="I know HTML only", skills={"web": ["HTML"]})
        jd = _make_jd(required_skills=["Rust", "C++"], preferred_skills=[], tech_stack=["Rust", "C++"])
        score, _, issues, _ = await skill_depth_scorer(resume, jd)
        assert score < 30
        assert any("missing" in i.lower() or "not found" in i.lower() for i in issues)

    @pytest.mark.asyncio
    async def test_no_target_skills_returns_neutral(self):
        jd = _make_jd(required_skills=[], preferred_skills=[], tech_stack=[])
        score, _, _, _ = await skill_depth_scorer(SENIOR_BACKEND_RESUME, jd)
        assert score == 70.0

    @pytest.mark.asyncio
    async def test_quantified_skill_gets_bonus(self):
        resume = _make_resume(
            raw_text="Reduced latency by 40% using Python",
            work_experience=[
                WorkExperience(
                    company="X", title="Eng", start_date=date(2022, 1, 1),
                    bullets=["Reduced latency by 40% using Python"],
                    technologies=["Python"],
                )
            ],
            skills={"lang": ["Python"]},
        )
        jd = _make_jd(required_skills=["Python"], preferred_skills=[], tech_stack=["Python"])
        score, _, _, _ = await skill_depth_scorer(resume, jd)
        assert score == 100.0


# ── 3. Tech Stack ──────────────────────────────────────────────────────────


class TestTechStackScorer:
    @pytest.mark.asyncio
    async def test_full_match_scores_high(self):
        score, expl, _, _ = await tech_stack_scorer(
            SENIOR_BACKEND_RESUME, STRIPE_BACKEND_JD
        )
        assert score >= 80, f"Full stack match should be high, got {score}"
        assert "exact" in expl.lower()

    @pytest.mark.asyncio
    async def test_category_match_gives_partial_credit(self):
        resume = _make_resume(
            raw_text="Built API with Flask",
            skills={"backend": ["Flask"]},
            work_experience=[
                WorkExperience(
                    company="X", title="Eng", start_date=date(2022, 1, 1),
                    bullets=["Built API with Flask"],
                    technologies=["Flask"],
                )
            ],
        )
        jd = _make_jd(tech_stack=["Django"], required_skills=[], preferred_skills=[])
        score, _, issues, _ = await tech_stack_scorer(resume, jd)
        assert 50 <= score <= 70

    @pytest.mark.asyncio
    async def test_completely_missing_tech(self):
        resume = _make_resume(raw_text="I only know Cobol", skills={"legacy": ["COBOL"]})
        jd = _make_jd(tech_stack=["Rust", "Elixir", "NATS"])
        score, _, issues, _ = await tech_stack_scorer(resume, jd)
        assert score < 40

    @pytest.mark.asyncio
    async def test_empty_jd_stack_returns_neutral(self):
        jd = _make_jd(tech_stack=[])
        score, _, _, _ = await tech_stack_scorer(SENIOR_BACKEND_RESUME, jd)
        assert score == 75.0


# ── 4. Experience Relevance ────────────────────────────────────────────────


class TestExperienceRelevanceScorer:
    @pytest.mark.asyncio
    async def test_relevant_experience_scores_well(self):
        score, expl, _, _ = await experience_relevance_scorer(
            SENIOR_BACKEND_RESUME, STRIPE_BACKEND_JD
        )
        # Keyword-overlap proxy is naturally low for long texts; >= 10 is meaningful
        assert score >= 10, f"Relevant experience should score above baseline, got {score}"

    @pytest.mark.asyncio
    async def test_no_requirements_returns_neutral(self):
        jd = _make_jd(requirements=[], role_priorities=[])
        score, _, _, _ = await experience_relevance_scorer(SENIOR_BACKEND_RESUME, jd)
        assert score == 60.0

    @pytest.mark.asyncio
    async def test_irrelevant_experience_scores_low(self):
        resume = _make_resume(
            raw_text="Managed retail store inventory",
            work_experience=[
                WorkExperience(
                    company="Target", title="Store Manager", start_date=date(2020, 1, 1),
                    bullets=["Managed daily retail operations and customer service schedules"],
                )
            ],
        )
        score, _, _, _ = await experience_relevance_scorer(resume, STRIPE_BACKEND_JD)
        assert score < 40


# ── 5. Quantified Impact ──────────────────────────────────────────────────


class TestQuantifiedImpactScorer:
    @pytest.mark.asyncio
    async def test_metrics_rich_resume_scores_high(self):
        score, expl, _, _ = await quantified_impact_scorer(
            SENIOR_BACKEND_RESUME, STRIPE_BACKEND_JD
        )
        assert score >= 50, f"Metrics-rich resume should score high, got {score}"
        assert "metrics" in expl.lower()

    @pytest.mark.asyncio
    async def test_no_bullets_returns_low(self):
        resume = _make_resume(raw_text="nothing here")
        score, _, issues, _ = await quantified_impact_scorer(resume, STRIPE_BACKEND_JD)
        assert score == 20.0
        assert any("no bullets" in i.lower() for i in issues)

    @pytest.mark.asyncio
    async def test_currency_metric_detected(self):
        resume = _make_resume(
            work_experience=[
                WorkExperience(
                    company="X", title="Eng", start_date=date(2022, 1, 1),
                    bullets=["Saved $500K annually by optimizing infrastructure"],
                )
            ],
            seniority_level="mid",
        )
        score, _, _, _ = await quantified_impact_scorer(resume, STRIPE_BACKEND_JD)
        assert score > 20

    @pytest.mark.asyncio
    async def test_percentage_metric_detected(self):
        resume = _make_resume(
            work_experience=[
                WorkExperience(
                    company="X", title="Eng", start_date=date(2022, 1, 1),
                    bullets=["Improved test coverage by 35%"],
                )
            ],
            seniority_level="mid",
        )
        score, _, _, _ = await quantified_impact_scorer(resume, STRIPE_BACKEND_JD)
        assert score > 20

    @pytest.mark.asyncio
    async def test_seniority_benchmark_penalty(self):
        resume = _make_resume(
            work_experience=[
                WorkExperience(
                    company="X", title="Sr Eng", start_date=date(2020, 1, 1),
                    bullets=["Worked on backend systems", "Maintained databases"],
                )
            ],
            seniority_level="senior",
        )
        score, _, issues, _ = await quantified_impact_scorer(resume, STRIPE_BACKEND_JD)
        assert any("senior" in i.lower() or "metrics" in i.lower() for i in issues)


# ── 6. Action Verb Strength ───────────────────────────────────────────────


class TestActionVerbScorer:
    @pytest.mark.asyncio
    async def test_strong_verbs_score_high(self):
        resume = _make_resume(
            work_experience=[
                WorkExperience(
                    company="X", title="Eng", start_date=date(2022, 1, 1),
                    bullets=[
                        "Architected a new microservices platform",
                        "Spearheaded migration to cloud infrastructure",
                        "Pioneered real-time data processing pipeline",
                    ],
                )
            ],
        )
        score, _, _, _ = await action_verb_scorer(resume, STRIPE_BACKEND_JD)
        assert score >= 85, f"Tier-1 verbs should score high, got {score}"

    @pytest.mark.asyncio
    async def test_weak_verbs_score_low(self):
        resume = _make_resume(
            work_experience=[
                WorkExperience(
                    company="X", title="Eng", start_date=date(2022, 1, 1),
                    bullets=[
                        "Helped with backend tasks",
                        "Assisted in deploying code",
                        "Participated in code reviews",
                        "Was responsible for testing",
                    ],
                )
            ],
        )
        score, _, issues, _ = await action_verb_scorer(resume, STRIPE_BACKEND_JD)
        assert score < 50, f"Tier-4 verbs should score low, got {score}"
        assert any("weak" in i.lower() or "Tier 4" in i for i in issues)

    @pytest.mark.asyncio
    async def test_no_bullets_returns_neutral(self):
        resume = _make_resume()
        score, _, _, _ = await action_verb_scorer(resume, STRIPE_BACKEND_JD)
        assert score == 50.0

    @pytest.mark.asyncio
    async def test_mixed_verbs_average(self):
        resume = _make_resume(
            work_experience=[
                WorkExperience(
                    company="X", title="Eng", start_date=date(2022, 1, 1),
                    bullets=[
                        "Architected the backend system",     # Tier 1
                        "Built a REST API",                    # Tier 2
                        "Managed CI/CD pipeline",              # Tier 3
                        "Helped fix production bugs",          # Tier 4
                    ],
                )
            ],
        )
        score, expl, _, _ = await action_verb_scorer(resume, STRIPE_BACKEND_JD)
        assert 50 <= score <= 80
        assert "Tier" in expl


# ── 7. Section Ordering ───────────────────────────────────────────────────


class TestSectionOrderingScorer:
    @pytest.mark.asyncio
    async def test_optimal_order_scores_high(self):
        resume = _make_resume(
            raw_text="EXPERIENCE\n...\nSKILLS\n...\nPROJECTS\n...\nEDUCATION\n...",
            seniority_level="senior",
        )
        jd = _make_jd(title="Senior Backend Engineer")
        score, _, _, _ = await section_ordering_scorer(resume, jd)
        assert score >= 80

    @pytest.mark.asyncio
    async def test_intern_education_first_preferred(self):
        resume = _make_resume(
            raw_text="EDUCATION\n...\nPROJECTS\n...\nSKILLS\n...\nEXPERIENCE\n...",
            seniority_level="intern",
        )
        jd = _make_jd(title="Software Engineering Intern")
        score, _, _, _ = await section_ordering_scorer(resume, jd)
        assert score >= 80

    @pytest.mark.asyncio
    async def test_no_sections_detected_returns_neutral(self):
        resume = _make_resume(raw_text="Just a blob of text with no headings at all nothing")
        jd = _make_jd()
        score, _, _, _ = await section_ordering_scorer(resume, jd)
        assert score == 70.0


# ── 8. Bullet Quality ─────────────────────────────────────────────────────


class TestBulletQualityScorer:
    @pytest.mark.asyncio
    async def test_high_quality_bullets(self):
        score, expl, _, _ = await bullet_quality_scorer(
            SENIOR_BACKEND_RESUME, STRIPE_BACKEND_JD
        )
        assert score >= 55, f"Well-structured bullets should score decent, got {score}"

    @pytest.mark.asyncio
    async def test_no_bullets_returns_low(self):
        resume = _make_resume()
        score, _, issues, _ = await bullet_quality_scorer(resume, STRIPE_BACKEND_JD)
        assert score == 30.0
        assert any("no" in i.lower() for i in issues)

    @pytest.mark.asyncio
    async def test_very_short_bullets_penalized(self):
        resume = _make_resume(
            work_experience=[
                WorkExperience(
                    company="X", title="Eng", start_date=date(2022, 1, 1),
                    bullets=["Did stuff", "Wrote code", "Fixed bug"],
                )
            ],
        )
        score, _, issues, _ = await bullet_quality_scorer(resume, STRIPE_BACKEND_JD)
        assert score < 60

    @pytest.mark.asyncio
    async def test_car_format_rewarded(self):
        resume = _make_resume(
            work_experience=[
                WorkExperience(
                    company="X", title="Eng", start_date=date(2022, 1, 1),
                    bullets=[
                        "Designed a caching layer for the API, reducing latency by 40% and saving $200K annually",
                        "Built a monitoring dashboard for production, enabling 5x faster incident response across the team",
                    ],
                )
            ],
        )
        score, _, _, _ = await bullet_quality_scorer(resume, STRIPE_BACKEND_JD)
        assert score >= 50


# ── 9. ATS Parsability ────────────────────────────────────────────────────


class TestATSParsabilityScorer:
    @pytest.mark.asyncio
    async def test_well_structured_resume_scores_high(self):
        score, _, _, _ = await ats_parsability_scorer(
            SENIOR_BACKEND_RESUME, STRIPE_BACKEND_JD
        )
        assert score >= 70, f"Well-structured resume should parse well, got {score}"

    @pytest.mark.asyncio
    async def test_table_layout_penalized(self):
        resume = _make_resume(
            raw_text="alex@example.com\nEXPERIENCE\nSkill1\tLevel1\tYears1\nSkill2\tLevel2\tYears2\n"
                     "Skill3\tLevel3\tYears3\nSkill4\tLevel4\tYears4\nSKILLS\n",
        )
        score, _, issues, _ = await ats_parsability_scorer(resume, STRIPE_BACKEND_JD)
        assert any("table" in i.lower() or "column" in i.lower() for i in issues)

    @pytest.mark.asyncio
    async def test_missing_email_penalized(self):
        resume = _make_resume(
            raw_text="EXPERIENCE\nSoftware Engineer at Acme\nSKILLS\nPython\nEDUCATION\nBS CS"
        )
        score, _, issues, _ = await ats_parsability_scorer(resume, STRIPE_BACKEND_JD)
        assert any("email" in i.lower() for i in issues)

    @pytest.mark.asyncio
    async def test_inconsistent_dates_penalized(self):
        resume = _make_resume(
            raw_text="alex@example.com\nEXPERIENCE\n"
                     "Engineer at X: 01/2020 - Present\n"
                     "Engineer at Y: January 2018 - December 2019\n"
                     "SKILLS\nPython\nEDUCATION\nBS CS"
        )
        score, _, issues, _ = await ats_parsability_scorer(resume, STRIPE_BACKEND_JD)
        assert any("date" in i.lower() for i in issues)

    @pytest.mark.asyncio
    async def test_tiny_text_penalized(self):
        resume = _make_resume(raw_text="Hello")
        score, _, issues, _ = await ats_parsability_scorer(resume, STRIPE_BACKEND_JD)
        assert score < 80
        assert any("little text" in i.lower() or "parsing" in i.lower() for i in issues)

    @pytest.mark.asyncio
    async def test_unicode_heavy_penalized(self):
        bad_chars = "★" * 30  # Stars
        resume = _make_resume(
            raw_text=f"alex@example.com\nEXPERIENCE\n{bad_chars}\nSKILLS\nPython"
        )
        score, _, issues, _ = await ats_parsability_scorer(resume, STRIPE_BACKEND_JD)
        assert any("special" in i.lower() or "unicode" in i.lower() for i in issues)


# ── 10. Seniority Calibration ─────────────────────────────────────────────


class TestSeniorityCalibrationScorer:
    @pytest.mark.asyncio
    async def test_exact_match_scores_perfect(self):
        score, _, _, _ = await seniority_calibration_scorer(
            SENIOR_BACKEND_RESUME, STRIPE_BACKEND_JD
        )
        assert score >= 80, f"Matching seniority should score high, got {score}"

    @pytest.mark.asyncio
    async def test_one_level_gap_decent(self):
        resume = _make_resume(seniority_level="mid", total_yoe=4.0)
        jd = _make_jd(seniority_level="senior", required_experience_years=5)
        score, _, _, _ = await seniority_calibration_scorer(resume, jd)
        assert 60 <= score <= 90

    @pytest.mark.asyncio
    async def test_large_gap_penalized(self):
        resume = _make_resume(seniority_level="intern", total_yoe=0.5)
        jd = _make_jd(seniority_level="staff_principal", required_experience_years=10)
        score, _, issues, _ = await seniority_calibration_scorer(resume, jd)
        assert score < 40

    @pytest.mark.asyncio
    async def test_overqualified_penalized(self):
        resume = _make_resume(seniority_level="executive", total_yoe=20.0)
        jd = _make_jd(seniority_level="junior", required_experience_years=2)
        score, _, issues, _ = await seniority_calibration_scorer(resume, jd)
        assert score < 50

    @pytest.mark.asyncio
    async def test_yoe_shortfall_penalized(self):
        resume = _make_resume(seniority_level="senior", total_yoe=2.0)
        jd = _make_jd(seniority_level="senior", required_experience_years=8)
        score, _, issues, _ = await seniority_calibration_scorer(resume, jd)
        assert any("yoe" in i.lower() or "experience" in i.lower() for i in issues)


# ── 11. Domain Knowledge ──────────────────────────────────────────────────


class TestDomainKnowledgeScorer:
    @pytest.mark.asyncio
    async def test_matching_domain_scores_high(self):
        resume = _make_resume(
            raw_text="Built payment processing system, handled PCI compliance, managed transactions ledger",
        )
        jd = _make_jd(
            raw_text="Fintech company seeking engineer for payments and compliance work",
        )
        score, _, _, _ = await domain_knowledge_scorer(resume, jd)
        assert score >= 80

    @pytest.mark.asyncio
    async def test_no_domain_in_jd_returns_neutral(self):
        jd = _make_jd(raw_text="We need a software engineer. That is all.")
        score, _, _, _ = await domain_knowledge_scorer(SENIOR_BACKEND_RESUME, jd)
        assert score == 75.0

    @pytest.mark.asyncio
    async def test_mismatched_domain_scores_low(self):
        resume = _make_resume(
            raw_text="Developed educational learning management system for students and curriculum tracking",
        )
        jd = _make_jd(
            raw_text="Fintech payments company building banking and trading infrastructure",
        )
        score, _, issues, _ = await domain_knowledge_scorer(resume, jd)
        assert score < 70

    @pytest.mark.asyncio
    async def test_multiple_domain_overlap(self):
        resume = _make_resume(
            raw_text="Built AI/ML models for healthcare diagnosis using deep learning and NLP transformers",
        )
        jd = _make_jd(
            raw_text="AI healthtech startup building machine learning NLP diagnosis platform",
        )
        score, _, _, _ = await domain_knowledge_scorer(resume, jd)
        assert score >= 80


# ── 12. Education Relevance ───────────────────────────────────────────────


class TestEducationRelevanceScorer:
    @pytest.mark.asyncio
    async def test_relevant_degree_scores_well(self):
        score, _, _, _ = await education_relevance_scorer(
            SENIOR_BACKEND_RESUME, STRIPE_BACKEND_JD
        )
        assert score >= 60

    @pytest.mark.asyncio
    async def test_no_education_requirement_returns_neutral(self):
        jd = _make_jd(required_education=None, requirements=[])
        score, _, _, _ = await education_relevance_scorer(SENIOR_BACKEND_RESUME, jd)
        assert score == 75.0

    @pytest.mark.asyncio
    async def test_no_education_on_resume_penalized(self):
        resume = _make_resume(education=[])
        jd = _make_jd(required_education="BS Computer Science")
        score, _, issues, _ = await education_relevance_scorer(resume, jd)
        assert score == 30.0

    @pytest.mark.asyncio
    async def test_masters_scores_higher_than_bachelors(self):
        resume_ms = _make_resume(
            education=[
                Education(
                    institution="MIT", degree="MS Computer Science",
                    field="Computer Science", gpa=3.9,
                )
            ],
        )
        resume_bs = _make_resume(
            education=[
                Education(
                    institution="MIT", degree="BS Computer Science",
                    field="Computer Science", gpa=3.9,
                )
            ],
        )
        jd = _make_jd(required_education="MS or PhD preferred")
        score_ms, _, _, _ = await education_relevance_scorer(resume_ms, jd)
        score_bs, _, _, _ = await education_relevance_scorer(resume_bs, jd)
        assert score_ms > score_bs

    @pytest.mark.asyncio
    async def test_honors_and_coursework_boost(self):
        resume_plain = _make_resume(
            education=[
                Education(
                    institution="MIT", degree="BS Computer Science",
                    field="Computer Science",
                )
            ],
        )
        resume_rich = _make_resume(
            education=[
                Education(
                    institution="MIT", degree="BS Computer Science",
                    field="Computer Science", gpa=3.8,
                    honors=["Summa Cum Laude"],
                    relevant_courses=["Distributed Systems", "Databases"],
                )
            ],
        )
        jd = _make_jd(required_education="BS Computer Science")
        score_plain, _, _, _ = await education_relevance_scorer(resume_plain, jd)
        score_rich, _, _, _ = await education_relevance_scorer(resume_rich, jd)
        assert score_rich > score_plain


# ── 13. Semantic Similarity ───────────────────────────────────────────────


class TestSemanticSimilarityScorer:
    @pytest.mark.asyncio
    async def test_matching_text_scores_high(self):
        score, expl, _, _ = await semantic_similarity_scorer(
            SENIOR_BACKEND_RESUME, STRIPE_BACKEND_JD
        )
        assert score >= 30, f"Matching resume/JD should have some overlap, got {score}"
        assert "similarity" in expl.lower()

    @pytest.mark.asyncio
    async def test_completely_different_text_scores_low(self):
        resume = _make_resume(
            raw_text="Studied marine biology and underwater ecosystems coral reef conservation",
            summary="Marine biologist studying coral reefs",
        )
        jd = _make_jd(
            raw_text="Senior backend engineer building distributed payment systems Python Go Kafka",
        )
        score, _, _, _ = await semantic_similarity_scorer(resume, jd)
        assert score < 30

    @pytest.mark.asyncio
    async def test_weak_summary_flagged(self):
        resume = _make_resume(
            raw_text="Python Go Kafka backend distributed systems",
            summary="I like cats and enjoy hiking on weekends",
            work_experience=[
                WorkExperience(
                    company="X", title="Eng", start_date=date(2022, 1, 1),
                    bullets=["Built Python APIs using Go and Kafka"],
                )
            ],
        )
        jd = _make_jd(
            raw_text="Backend engineer for distributed systems with Python, Go, Kafka",
            role_priorities=["Build backend systems", "Scale infrastructure"],
        )
        score, _, issues, _ = await semantic_similarity_scorer(resume, jd)
        assert any("summary" in i.lower() for i in issues)


# ── 14. Voice Alignment ──────────────────────────────────────────────────


class TestVoiceAlignmentScorer:
    @pytest.mark.asyncio
    async def test_coherent_career_scores_well(self):
        score, expl, _, _ = await voice_alignment_scorer(
            SENIOR_BACKEND_RESUME, STRIPE_BACKEND_JD
        )
        assert score >= 65

    @pytest.mark.asyncio
    async def test_yoe_mismatch_penalized(self):
        resume = _make_resume(
            summary="Engineer with 15+ years of experience",
            total_yoe=3.0,
            work_experience=[
                WorkExperience(
                    company="X", title="Eng", start_date=date(2022, 1, 1),
                    bullets=["Built APIs"],
                    technologies=["Python"],
                )
            ],
        )
        score, _, issues, _ = await voice_alignment_scorer(resume, STRIPE_BACKEND_JD)
        assert any("years" in i.lower() or "yoe" in i.lower() for i in issues)

    @pytest.mark.asyncio
    async def test_career_progression_boosts_score(self):
        resume = _make_resume(
            work_experience=[
                WorkExperience(
                    company="X", title="Director of Engineering",
                    start_date=date(2022, 1, 1),
                    bullets=["Led the engineering org"],
                    technologies=["Python"],
                ),
                WorkExperience(
                    company="Y", title="Senior Engineer",
                    start_date=date(2020, 1, 1), end_date=date(2021, 12, 31),
                    bullets=["Built backend systems"],
                    technologies=["Python"],
                ),
                WorkExperience(
                    company="Z", title="Software Engineer",
                    start_date=date(2018, 1, 1), end_date=date(2019, 12, 31),
                    bullets=["Wrote code"],
                    technologies=["Python"],
                ),
            ],
        )
        score, _, _, _ = await voice_alignment_scorer(resume, STRIPE_BACKEND_JD)
        assert score >= 70

    @pytest.mark.asyncio
    async def test_empty_resume_gets_baseline(self):
        resume = _make_resume()
        score, _, _, _ = await voice_alignment_scorer(resume, STRIPE_BACKEND_JD)
        assert 60 <= score <= 80


# ── Integration: full scoring pipeline ─────────────────────────────────────


class TestFullScoringPipeline:
    @pytest.mark.asyncio
    async def test_all_scorers_return_valid_tuple(self):
        """Every scorer returns (float, str, list, list) in range 0-100."""
        scorers = [
            keyword_density_scorer,
            skill_depth_scorer,
            tech_stack_scorer,
            experience_relevance_scorer,
            quantified_impact_scorer,
            action_verb_scorer,
            section_ordering_scorer,
            bullet_quality_scorer,
            ats_parsability_scorer,
            seniority_calibration_scorer,
            domain_knowledge_scorer,
            education_relevance_scorer,
            semantic_similarity_scorer,
            voice_alignment_scorer,
        ]
        for scorer in scorers:
            result = await scorer(SENIOR_BACKEND_RESUME, STRIPE_BACKEND_JD)
            assert isinstance(result, tuple), f"{scorer.__name__} didn't return tuple"
            assert len(result) == 4, f"{scorer.__name__} tuple length != 4"
            score, expl, issues, suggestions = result
            assert isinstance(score, float), f"{scorer.__name__} score not float"
            assert 0 <= score <= 100, f"{scorer.__name__} score {score} out of range"
            assert isinstance(expl, str), f"{scorer.__name__} explanation not str"
            assert isinstance(issues, list), f"{scorer.__name__} issues not list"
            assert isinstance(suggestions, list), f"{scorer.__name__} suggestions not list"

    @pytest.mark.asyncio
    async def test_scorer_engine_integration(self):
        """The scorer_engine.score_resume() runs all 14 and produces a valid result."""
        from backend.agents.tailor.weightage.scorer_engine import score_resume

        result = await score_resume(SENIOR_BACKEND_RESUME, STRIPE_BACKEND_JD)
        assert 0 <= result.total_score <= 100
        assert result.letter_grade in [
            "A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F"
        ]
        assert len(result.dimension_scores) == 14
        assert result.role_type == "software_engineer_backend"
        assert result.seniority_level == "senior"
        assert result.predicted_ats_pass == (result.total_score >= 70)
        assert len(result.weights_used) == 14
        assert abs(sum(result.weights_used.values()) - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_senior_resume_beats_irrelevant(self):
        """Relevant resume should score higher than irrelevant one."""
        from backend.agents.tailor.weightage.scorer_engine import score_resume

        good_result = await score_resume(SENIOR_BACKEND_RESUME, STRIPE_BACKEND_JD)

        irrelevant_resume = _make_resume(
            raw_text="I am a marine biologist studying coral reefs",
            summary="Marine biologist",
            work_experience=[
                WorkExperience(
                    company="Ocean Lab", title="Research Intern",
                    start_date=date(2023, 6, 1),
                    bullets=["Collected water samples for reef analysis"],
                )
            ],
            education=[
                Education(
                    institution="UC Santa Cruz",
                    degree="BS Marine Biology",
                    field="Marine Biology",
                )
            ],
            skills={"science": ["Scuba Diving", "Water Analysis"]},
            seniority_level="intern",
            total_yoe=0.3,
        )
        bad_result = await score_resume(irrelevant_resume, STRIPE_BACKEND_JD)

        assert good_result.total_score > bad_result.total_score, (
            f"Senior backend ({good_result.total_score}) should beat "
            f"marine biologist ({bad_result.total_score}) for Stripe Backend JD"
        )
