"""Unit tests for all 8 Standout Engine scorer functions."""

from datetime import date

import pytest

from backend.parsers.schemas import (
    Education,
    JobDescription,
    Resume,
    ResumeContact,
    WorkExperience,
    Project,
)
from backend.agents.tailor.standout.scorers import (
    spike_factor_scorer,
    trajectory_scorer,
    builder_ratio_scorer,
    outcome_density_scorer,
    narrative_pull_scorer,
    uniqueness_index_scorer,
    credibility_anchors_scorer,
    first_impression_scorer,
    _all_bullets,
    _recent_bullets,
    _BUILDER_VERBS,
    _MAINTAINER_VERBS,
)


# ── Test fixtures ─────────────────────────────────────────────────────────────


def _contact(**overrides) -> ResumeContact:
    defaults = dict(name="Alex Chen", email="alex@example.com", linkedin="linkedin.com/in/alex")
    defaults.update(overrides)
    return ResumeContact(**defaults)


def _make_resume(
    *,
    raw_text: str = "",
    summary: str | None = None,
    work_experience: list[WorkExperience] | None = None,
    education: list[Education] | None = None,
    skills: dict[str, list[str]] | None = None,
    seniority_level: str = "mid",
    total_yoe: float = 5.0,
    primary_domain: str = "backend",
    contact: ResumeContact | None = None,
    projects: list[Project] | None = None,
) -> Resume:
    return Resume(
        contact=contact or _contact(),
        raw_text=raw_text or "Software Engineer with 5 years experience",
        summary=summary,
        work_experience=work_experience or [],
        education=education or [],
        skills=skills or {},
        seniority_level=seniority_level,
        total_yoe=total_yoe,
        primary_domain=primary_domain,
        projects=projects or [],
    )


def _make_jd(
    *,
    title: str = "Senior Backend Engineer",
    company: str = "Stripe",
    required_skills: list[str] | None = None,
    tech_stack: list[str] | None = None,
) -> JobDescription:
    return JobDescription(
        raw_text="We need a senior backend engineer.",
        title=title,
        company=company,
        required_skills=required_skills or ["Python", "Go"],
        tech_stack=tech_stack or ["Python", "Go", "PostgreSQL"],
    )


def _work(
    company: str = "Acme Corp",
    title: str = "Software Engineer",
    start: str = "2020-01-01",
    end: str | None = None,
    bullets: list[str] | None = None,
    technologies: list[str] | None = None,
    location: str | None = None,
) -> WorkExperience:
    return WorkExperience(
        company=company,
        title=title,
        start_date=date.fromisoformat(start),
        end_date=date.fromisoformat(end) if end else None,
        bullets=bullets or [],
        technologies=technologies or [],
        location=location,
    )


def _edu(
    institution: str = "MIT",
    degree: str = "BS",
    field: str = "Computer Science",
    honors: list[str] | None = None,
) -> Education:
    return Education(
        institution=institution,
        degree=degree,
        field=field,
        honors=honors or [],
    )


# ── Spike Factor ──────────────────────────────────────────────────────────────


class TestSpikeFactorScorer:
    @pytest.mark.asyncio
    async def test_big_scale_metric_awards_points(self):
        resume = _make_resume(
            work_experience=[_work(bullets=["Scaled platform to 5M users globally"])],
            raw_text="Scaled platform to 5M users globally",
        )
        score, explanation, issues, suggestions = await spike_factor_scorer(resume, _make_jd())
        assert score >= 20
        assert "spike" in explanation.lower() or "Scale" in explanation

    @pytest.mark.asyncio
    async def test_prestigious_company_adds_spike(self):
        resume = _make_resume(
            work_experience=[_work(company="Google", bullets=["Built search infra"])],
            raw_text="Software Engineer at Google",
        )
        score, explanation, issues, suggestions = await spike_factor_scorer(resume, _make_jd())
        assert score >= 15
        assert "google" in explanation.lower()

    @pytest.mark.asyncio
    async def test_patent_publication_award(self):
        resume = _make_resume(
            raw_text="Holder of US Patent #1234. Published in IEEE. Winner of best paper award.",
            work_experience=[_work(bullets=["Research"])],
        )
        score, *_ = await spike_factor_scorer(resume, _make_jd())
        assert score >= 30  # patent + publication + award

    @pytest.mark.asyncio
    async def test_no_spikes_returns_low_score(self):
        resume = _make_resume(
            work_experience=[_work(bullets=["Worked on features", "Attended meetings"])],
            raw_text="Worked on features. Attended meetings.",
        )
        score, explanation, issues, suggestions = await spike_factor_scorer(resume, _make_jd())
        assert score < 30
        assert len(issues) > 0
        assert len(suggestions) > 0

    @pytest.mark.asyncio
    async def test_score_capped_at_100(self):
        resume = _make_resume(
            work_experience=[
                _work(company="Google", bullets=["Scaled to 10M users", "Generated $50M revenue"]),
                _work(company="Meta", bullets=["Served 1B requests/day"]),
            ],
            raw_text="Patent holder. Award winner. Published research. Google Meta 10M users $50M revenue 1B requests",
        )
        score, *_ = await spike_factor_scorer(resume, _make_jd())
        assert score <= 100


# ── Trajectory Signal ─────────────────────────────────────────────────────────


class TestTrajectoryScorer:
    @pytest.mark.asyncio
    async def test_clear_upward_trajectory(self):
        resume = _make_resume(
            work_experience=[
                _work(title="Staff Engineer", start="2023-01-01"),
                _work(title="Senior Engineer", start="2020-01-01", end="2022-12-31"),
                _work(title="Software Engineer", start="2017-01-01", end="2019-12-31"),
            ],
            total_yoe=7,
        )
        score, explanation, issues, suggestions = await trajectory_scorer(resume, _make_jd())
        assert score >= 65
        assert "level-up" in explanation.lower() or "promotion" in explanation.lower()

    @pytest.mark.asyncio
    async def test_flat_trajectory_scores_lower(self):
        resume = _make_resume(
            work_experience=[
                _work(title="Software Engineer", start="2021-01-01"),
                _work(title="Software Engineer", start="2018-01-01", end="2020-12-31"),
                _work(title="Software Engineer", start="2015-01-01", end="2017-12-31"),
            ],
            total_yoe=9,
        )
        score, explanation, issues, suggestions = await trajectory_scorer(resume, _make_jd())
        assert score < 65

    @pytest.mark.asyncio
    async def test_single_role_gives_limited_signal(self):
        resume = _make_resume(
            work_experience=[_work(title="Engineer", start="2022-01-01")],
            total_yoe=2,
        )
        score, explanation, *_ = await trajectory_scorer(resume, _make_jd())
        assert score <= 50
        assert "not enough" in explanation.lower() or "only one" in explanation.lower()

    @pytest.mark.asyncio
    async def test_downward_move_penalized(self):
        resume = _make_resume(
            work_experience=[
                _work(title="Software Engineer", start="2022-01-01"),
                _work(title="Senior Engineer", start="2019-01-01", end="2021-12-31"),
            ],
            total_yoe=5,
        )
        score, _, issues, _ = await trajectory_scorer(resume, _make_jd())
        assert any("step-down" in i.lower() for i in issues)


# ── Builder Ratio ─────────────────────────────────────────────────────────────


class TestBuilderRatioScorer:
    @pytest.mark.asyncio
    async def test_high_builder_ratio(self):
        bullets = [
            "Built a real-time data pipeline processing 1M events/day",
            "Designed and shipped microservices architecture",
            "Created CI/CD pipeline reducing deploy time by 80%",
            "Launched customer-facing dashboard used by 10K users",
            "Architected event-driven system handling 500K events/hour",
        ]
        resume = _make_resume(work_experience=[_work(bullets=bullets)])
        score, explanation, issues, suggestions = await builder_ratio_scorer(resume, _make_jd())
        assert score >= 70
        assert "100%" in explanation or "80%" in explanation

    @pytest.mark.asyncio
    async def test_high_maintainer_ratio(self):
        bullets = [
            "Managed production deployments",
            "Maintained legacy codebase",
            "Supported on-call rotations",
            "Monitored system health dashboards",
            "Assisted with bug fixes",
        ]
        resume = _make_resume(work_experience=[_work(bullets=bullets)])
        score, explanation, issues, suggestions = await builder_ratio_scorer(resume, _make_jd())
        assert score < 50
        assert len(issues) > 0

    @pytest.mark.asyncio
    async def test_no_bullets_returns_low_score(self):
        resume = _make_resume(work_experience=[_work(bullets=[])])
        score, explanation, *_ = await builder_ratio_scorer(resume, _make_jd())
        assert score <= 30

    @pytest.mark.asyncio
    async def test_mixed_ratio(self):
        bullets = [
            "Built microservices architecture",
            "Managed team standups",
            "Designed API contracts",
            "Maintained CI/CD pipeline",
        ]
        resume = _make_resume(work_experience=[_work(bullets=bullets)])
        score, explanation, *_ = await builder_ratio_scorer(resume, _make_jd())
        assert 40 <= score <= 80


# ── Outcome Density ───────────────────────────────────────────────────────────


class TestOutcomeDensityScorer:
    @pytest.mark.asyncio
    async def test_high_outcome_density(self):
        bullets = [
            "Reduced API latency by 40% through caching layer",
            "Increased revenue by $2M through conversion optimization",
            "Shipped new onboarding flow resulting in 25% user growth",
            "Delivered data pipeline processing 5M events/day",
        ]
        resume = _make_resume(
            work_experience=[_work(bullets=bullets)],
            seniority_level="senior",
        )
        score, explanation, issues, suggestions = await outcome_density_scorer(resume, _make_jd())
        assert score >= 70
        assert "100%" in explanation or "4/4" in explanation

    @pytest.mark.asyncio
    async def test_low_outcome_density(self):
        bullets = [
            "Worked on backend services",
            "Participated in code reviews",
            "Attended sprint planning meetings",
            "Used Jira for task management",
        ]
        resume = _make_resume(
            work_experience=[_work(bullets=bullets)],
            seniority_level="senior",
        )
        score, explanation, issues, suggestions = await outcome_density_scorer(resume, _make_jd())
        assert score < 50
        assert len(issues) > 0

    @pytest.mark.asyncio
    async def test_no_bullets(self):
        resume = _make_resume(work_experience=[_work(bullets=[])])
        score, *_ = await outcome_density_scorer(resume, _make_jd())
        assert score <= 20

    @pytest.mark.asyncio
    async def test_junior_has_lower_target(self):
        # 1 out of 4 = 25%, which should be OK for junior
        bullets = [
            "Reduced page load time by 30%",
            "Wrote unit tests",
            "Fixed UI bugs",
            "Updated documentation",
        ]
        resume = _make_resume(
            work_experience=[_work(bullets=bullets)],
            seniority_level="junior",
        )
        score, *_ = await outcome_density_scorer(resume, _make_jd())
        assert score >= 40  # 25% density meets junior target


# ── Narrative Pull ────────────────────────────────────────────────────────────


class TestNarrativePullScorer:
    @pytest.mark.asyncio
    async def test_strong_narrative(self):
        resume = _make_resume(
            summary="Backend engineer with 8 years scaling payment systems from $10M to $500M ARR. Specialized in distributed systems and real-time processing.",
            work_experience=[
                _work(title="Staff Engineer", technologies=["Go", "Kafka"]),
                _work(title="Senior Engineer", technologies=["Python", "PostgreSQL"]),
            ],
            primary_domain="backend",
        )
        score, explanation, issues, suggestions = await narrative_pull_scorer(resume, _make_jd())
        assert score >= 60

    @pytest.mark.asyncio
    async def test_generic_summary_penalized(self):
        resume = _make_resume(
            summary="Passionate, hard worker and team player seeking a challenging position. Self-motivated and detail-oriented fast learner.",
            work_experience=[_work()],
        )
        score, _, issues, suggestions = await narrative_pull_scorer(resume, _make_jd())
        assert score < 55
        assert any("generic" in i.lower() for i in issues)

    @pytest.mark.asyncio
    async def test_no_summary_penalized(self):
        resume = _make_resume(summary=None, work_experience=[_work()])
        score, _, issues, _ = await narrative_pull_scorer(resume, _make_jd())
        assert any("summary" in i.lower() or "hook" in i.lower() for i in issues)

    @pytest.mark.asyncio
    async def test_summary_with_metric_boosted(self):
        resume = _make_resume(
            summary="Reduced infrastructure costs by 40% across 3 product lines",
            work_experience=[_work()],
        )
        score, _, _, _ = await narrative_pull_scorer(resume, _make_jd())
        # Should get boost from metric in summary
        resume_no_metric = _make_resume(
            summary="Worked on infrastructure across product lines",
            work_experience=[_work()],
        )
        score_no_metric, *_ = await narrative_pull_scorer(resume_no_metric, _make_jd())
        assert score > score_no_metric


# ── Uniqueness Index ──────────────────────────────────────────────────────────


class TestUniquenessIndexScorer:
    @pytest.mark.asyncio
    async def test_side_projects_boost(self):
        resume = _make_resume(
            raw_text="Contributed to several open source projects on GitHub. Built a personal side project with 500 stars.",
            work_experience=[_work()],
        )
        score, _, _, _ = await uniqueness_index_scorer(resume, _make_jd())
        assert score >= 50

    @pytest.mark.asyncio
    async def test_publications_boost(self):
        resume = _make_resume(
            raw_text="Published paper at NeurIPS 2023. Spoke at PyCon conference.",
            work_experience=[_work()],
        )
        score, explanation, _, _ = await uniqueness_index_scorer(resume, _make_jd())
        assert score >= 55
        assert "publication" in explanation.lower() or "conference" in explanation.lower()

    @pytest.mark.asyncio
    async def test_founding_experience_boost(self):
        resume = _make_resume(
            raw_text="Co-founder of a YC-backed startup. Bootstrapped to $1M ARR.",
            work_experience=[_work()],
        )
        score, _, _, _ = await uniqueness_index_scorer(resume, _make_jd())
        assert score >= 55

    @pytest.mark.asyncio
    async def test_no_uniqueness_signals(self):
        resume = _make_resume(
            raw_text="Standard software engineer with Python and JavaScript skills.",
            work_experience=[_work()],
            skills={},
        )
        score, _, issues, suggestions = await uniqueness_index_scorer(resume, _make_jd())
        assert score < 50
        assert len(issues) > 0 or len(suggestions) > 0

    @pytest.mark.asyncio
    async def test_multi_location_experience(self):
        resume = _make_resume(
            raw_text="Diverse experience",
            work_experience=[
                _work(location="San Francisco, CA"),
                _work(location="London, UK"),
            ],
        )
        score, explanation, _, _ = await uniqueness_index_scorer(resume, _make_jd())
        assert "location" in explanation.lower() or score >= 45


# ── Credibility Anchors ───────────────────────────────────────────────────────


class TestCredibilityAnchorsScorer:
    @pytest.mark.asyncio
    async def test_prestigious_company(self):
        resume = _make_resume(
            work_experience=[_work(company="Google")],
            raw_text="Software Engineer at Google",
        )
        score, explanation, _, _ = await credibility_anchors_scorer(resume, _make_jd())
        assert score >= 15
        assert "google" in explanation.lower()

    @pytest.mark.asyncio
    async def test_prestigious_university(self):
        resume = _make_resume(
            education=[_edu(institution="Stanford University")],
            raw_text="BS from Stanford University",
        )
        score, explanation, _, _ = await credibility_anchors_scorer(resume, _make_jd())
        assert score >= 15
        assert "stanford" in explanation.lower()

    @pytest.mark.asyncio
    async def test_certifications_boost(self):
        resume = _make_resume(
            raw_text="AWS Certified Solutions Architect. Kubernetes CKA certified.",
        )
        score, _, _, _ = await credibility_anchors_scorer(resume, _make_jd())
        assert score >= 8

    @pytest.mark.asyncio
    async def test_patent_and_publication(self):
        resume = _make_resume(
            raw_text="US Patent #1234567. Published in arxiv and ACM proceedings.",
        )
        score, explanation, _, _ = await credibility_anchors_scorer(resume, _make_jd())
        assert score >= 20

    @pytest.mark.asyncio
    async def test_no_anchors(self):
        resume = _make_resume(
            work_experience=[_work(company="Smallco Inc")],
            education=[_edu(institution="State Community College", field="General Studies")],
            raw_text="Software developer at Smallco Inc. State Community College.",
        )
        score, _, issues, suggestions = await credibility_anchors_scorer(resume, _make_jd())
        assert score < 30
        assert len(issues) > 0

    @pytest.mark.asyncio
    async def test_honors_add_points(self):
        resume = _make_resume(
            education=[_edu(institution="MIT", honors=["summa cum laude", "Phi Beta Kappa"])],
            raw_text="BS from MIT, summa cum laude",
        )
        score, explanation, _, _ = await credibility_anchors_scorer(resume, _make_jd())
        assert score >= 20  # MIT + honors

    @pytest.mark.asyncio
    async def test_score_capped_at_100(self):
        resume = _make_resume(
            work_experience=[_work(company="Google"), _work(company="Meta")],
            education=[_edu(institution="Stanford University", honors=["magna cum laude"])],
            raw_text=(
                "Google Meta Stanford Patent holder. Published in journal. "
                "AWS Certified. Kubernetes CKA. Winner of hackathon award. "
                "Open source github 500 stars. Fellowship recipient."
            ),
        )
        score, *_ = await credibility_anchors_scorer(resume, _make_jd())
        assert score <= 100


# ── First Impression ──────────────────────────────────────────────────────────


class TestFirstImpressionScorer:
    @pytest.mark.asyncio
    async def test_strong_first_impression(self):
        resume = _make_resume(
            contact=_contact(name="Alex Chen", linkedin="linkedin.com/in/alex"),
            summary="Staff Engineer with 10 years scaling payment systems. Reduced checkout latency by 60%.",
            work_experience=[
                _work(
                    company="Stripe",
                    title="Staff Engineer",
                    bullets=[
                        "Architected real-time fraud detection saving $50M annually",
                        "Led migration to event-driven architecture serving 10M transactions/day",
                    ],
                ),
            ],
            total_yoe=10,
        )
        score, explanation, _, _ = await first_impression_scorer(resume, _make_jd())
        assert score >= 70

    @pytest.mark.asyncio
    async def test_weak_first_impression(self):
        resume = _make_resume(
            contact=_contact(name="", linkedin=None),
            summary=None,
            work_experience=[
                _work(
                    company="Unknown Corp",
                    title="Developer",
                    bullets=["Worked on stuff", "Did things"],
                ),
            ],
            total_yoe=0,
        )
        score, _, issues, suggestions = await first_impression_scorer(resume, _make_jd())
        assert score < 50
        assert len(issues) >= 2

    @pytest.mark.asyncio
    async def test_long_summary_penalized(self):
        long_summary = " ".join(["word"] * 70)  # 70 words
        resume = _make_resume(
            summary=long_summary,
            work_experience=[_work()],
        )
        score, _, issues, _ = await first_impression_scorer(resume, _make_jd())
        assert any("summary" in i.lower() for i in issues)

    @pytest.mark.asyncio
    async def test_strong_title_boosted(self):
        resume = _make_resume(
            summary="Experienced engineer",
            work_experience=[_work(title="Senior Staff Engineer", company="Google")],
        )
        score_strong, *_ = await first_impression_scorer(resume, _make_jd())

        resume_weak = _make_resume(
            summary="Experienced engineer",
            work_experience=[_work(title="Developer", company="Smallco")],
        )
        score_weak, *_ = await first_impression_scorer(resume_weak, _make_jd())

        assert score_strong > score_weak


# ── Helper functions ──────────────────────────────────────────────────────────


class TestHelpers:
    def test_all_bullets(self):
        resume = _make_resume(
            work_experience=[
                _work(bullets=["A", "B"]),
                _work(bullets=["C"]),
            ]
        )
        assert _all_bullets(resume) == ["A", "B", "C"]

    def test_all_bullets_empty(self):
        resume = _make_resume(work_experience=[])
        assert _all_bullets(resume) == []

    def test_recent_bullets_filters_old(self):
        resume = _make_resume(
            work_experience=[
                _work(start="2024-01-01", bullets=["Recent"]),
                _work(start="2015-01-01", end="2016-12-31", bullets=["Old"]),
            ]
        )
        recent = _recent_bullets(resume, years=3)
        assert "Recent" in recent
        assert "Old" not in recent

    def test_builder_and_maintainer_verbs_disjoint(self):
        assert _BUILDER_VERBS & _MAINTAINER_VERBS == set()

    def test_builder_verbs_not_empty(self):
        assert len(_BUILDER_VERBS) >= 20

    def test_maintainer_verbs_not_empty(self):
        assert len(_MAINTAINER_VERBS) >= 15
