"""Tests for the job-profile fit scorer."""

import pytest
from datetime import date

from backend.agents.scout.scorer import (
    FitResult,
    FitDimension,
    score_fit,
    _score_skill_match,
    _score_tech_stack,
    _score_seniority_fit,
    _score_experience_years,
    _score_domain_overlap,
    _score_location_fit,
    _score_role_type,
)
from backend.parsers.schemas import (
    Resume, ResumeContact, WorkExperience, Education,
    JobDescription, JDRequirement,
)


def _resume(**overrides) -> Resume:
    defaults = dict(
        contact=ResumeContact(name="Jane Doe", email="jane@test.com", location="San Francisco, CA"),
        summary="Senior backend engineer with 7 years of experience",
        work_experience=[
            WorkExperience(
                company="TechCo",
                title="Senior Backend Engineer",
                start_date=date(2019, 1, 1),
                end_date=date(2024, 1, 1),
                bullets=["Built distributed payment system processing $10M daily"],
                technologies=["Python", "Go", "PostgreSQL", "Kubernetes", "gRPC"],
                impact_metrics=["$10M daily"],
                seniority_signals=["led team of 5"],
            ),
        ],
        education=[
            Education(institution="MIT", degree="B.S.", field="Computer Science"),
        ],
        skills={
            "languages": ["Python", "Go", "TypeScript"],
            "databases": ["PostgreSQL", "Redis", "MongoDB"],
            "infrastructure": ["Kubernetes", "Docker", "Terraform", "AWS"],
            "frameworks": ["FastAPI", "gRPC", "React"],
        },
        total_yoe=7.0,
        seniority_level="senior",
        primary_domain="fintech",
        raw_text="Senior backend engineer Python Go PostgreSQL distributed systems",
    )
    defaults.update(overrides)
    return Resume(**defaults)


def _jd(**overrides) -> JobDescription:
    defaults = dict(
        title="Senior Backend Engineer",
        company="Stripe",
        location="San Francisco, CA",
        remote_policy="hybrid",
        seniority_level="senior",
        required_skills=["Python", "Go", "PostgreSQL"],
        preferred_skills=["Kubernetes", "Redis", "gRPC"],
        tech_stack=["Python", "Go", "PostgreSQL", "Docker", "Kubernetes"],
        requirements=[
            JDRequirement(text="5+ years backend dev", category="must_have",
                          skill_type="technical", extracted_keyword="backend"),
        ],
        required_experience_years=5,
        company_values=["Move fast", "Think big"],
        domain_knowledge=["fintech"],
    )
    defaults.update(overrides)
    return JobDescription(**defaults)


class TestScoreSkillMatch:

    def test_perfect_match_scores_high(self):
        score, _, _, _ = _score_skill_match(
            _resume(),
            _jd(required_skills=["Python", "Go", "PostgreSQL"],
                preferred_skills=["Kubernetes", "Redis"]),
        )
        assert score >= 90

    def test_no_match_scores_low(self):
        score, _, _, gaps = _score_skill_match(
            _resume(skills={"languages": ["Java"]}),
            _jd(required_skills=["Ruby", "Scala", "Haskell"]),
        )
        assert score < 30
        assert len(gaps) > 0

    def test_partial_match(self):
        score, _, _, _ = _score_skill_match(
            _resume(),
            _jd(required_skills=["Python", "Rust", "Elixir"]),
        )
        assert 20 < score < 60

    def test_returns_gaps(self):
        _, _, _, gaps = _score_skill_match(
            _resume(),
            _jd(required_skills=["Python", "Rust"]),
        )
        missing = [g for g in gaps if "rust" in g.lower()]
        assert len(missing) == 1


class TestScoreTechStack:

    def test_full_stack_match(self):
        score, _ = _score_tech_stack(
            _resume(),
            _jd(tech_stack=["Python", "Go", "PostgreSQL", "Docker", "Kubernetes"]),
        )
        assert score >= 80

    def test_no_stack_specified(self):
        score, _ = _score_tech_stack(_resume(), _jd(tech_stack=[]))
        assert score == 70.0  # Default neutral

    def test_zero_overlap(self):
        score, _ = _score_tech_stack(
            _resume(skills={"languages": ["Java"]}),
            _jd(tech_stack=["Ruby", "Elixir", "Phoenix"]),
        )
        assert score < 10


class TestScoreSeniorityFit:

    def test_exact_match(self):
        score, _, db = _score_seniority_fit(
            _resume(seniority_level="senior"),
            _jd(seniority_level="senior"),
        )
        assert score == 100.0
        assert len(db) == 0

    def test_one_level_off(self):
        score, _, _ = _score_seniority_fit(
            _resume(seniority_level="mid"),
            _jd(seniority_level="senior"),
        )
        assert score == 75.0

    def test_large_gap_is_dealbreaker(self):
        score, _, db = _score_seniority_fit(
            _resume(seniority_level="junior"),
            _jd(seniority_level="principal"),
        )
        assert score <= 10
        assert len(db) > 0


class TestScoreExperienceYears:

    def test_meets_requirement(self):
        score, _, _ = _score_experience_years(
            _resume(total_yoe=7.0),
            _jd(required_experience_years=5),
        )
        assert score == 100.0

    def test_slightly_under(self):
        score, _, _ = _score_experience_years(
            _resume(total_yoe=4.5),
            _jd(required_experience_years=5),
        )
        assert score >= 60

    def test_significantly_under(self):
        score, _, db = _score_experience_years(
            _resume(total_yoe=2.0),
            _jd(required_experience_years=8),
        )
        assert score <= 20
        assert len(db) > 0

    def test_no_requirement(self):
        score, _, _ = _score_experience_years(
            _resume(),
            _jd(required_experience_years=None),
        )
        assert score == 70.0


class TestScoreDomainOverlap:

    def test_matching_domain(self):
        score, _ = _score_domain_overlap(
            _resume(primary_domain="fintech"),
            _jd(domain_knowledge=["fintech"]),
        )
        assert score >= 80

    def test_no_domain_required(self):
        score, _ = _score_domain_overlap(
            _resume(),
            _jd(domain_knowledge=[], title="Software Engineer"),
        )
        assert score >= 50

    def test_domain_mismatch(self):
        score, _ = _score_domain_overlap(
            _resume(primary_domain="healthcare"),
            _jd(domain_knowledge=["gaming"]),
        )
        assert score < 50


class TestScoreLocationFit:

    def test_remote_is_perfect(self):
        score, _ = _score_location_fit(
            _resume(),
            _jd(remote_policy="remote"),
        )
        assert score == 100.0

    def test_matching_city(self):
        score, _ = _score_location_fit(
            _resume(contact=ResumeContact(name="X", email="x@x.com", location="San Francisco")),
            _jd(location="San Francisco, CA", remote_policy="onsite"),
        )
        assert score >= 80

    def test_different_city(self):
        score, _ = _score_location_fit(
            _resume(contact=ResumeContact(name="X", email="x@x.com", location="New York")),
            _jd(location="San Francisco, CA", remote_policy="onsite"),
        )
        assert score <= 40


class TestScoreRoleType:

    def test_matching_role(self):
        score, _ = _score_role_type(
            _resume(skills={"languages": ["Python", "Go"], "infra": ["Docker"]}),
            _jd(title="Senior Backend Engineer"),
        )
        assert score >= 70


class TestScoreFitIntegration:

    def test_perfect_candidate(self):
        result = score_fit(_resume(), _jd())
        assert isinstance(result, FitResult)
        assert result.total_score >= 70
        assert len(result.dimensions) == 8

    def test_has_strengths_and_gaps(self):
        result = score_fit(_resume(), _jd())
        # Perfect candidate should have mostly strengths
        assert len(result.strengths) >= 1

    def test_poor_candidate(self):
        poor = _resume(
            skills={"languages": ["Cobol"]},
            work_experience=[
                WorkExperience(
                    company="Old Corp",
                    title="Cobol Developer",
                    start_date=date(2023, 1, 1),
                    bullets=["Maintained legacy Cobol systems"],
                    technologies=["Cobol", "FORTRAN"],
                ),
            ],
            total_yoe=1.0,
            seniority_level="intern",
            primary_domain="agriculture",
            contact=ResumeContact(name="X", email="x@x.com", location="Antarctica"),
            raw_text="Cobol FORTRAN agriculture",
        )
        result = score_fit(poor, _jd())
        assert result.total_score < 40
        assert len(result.gaps) >= 1

    def test_good_candidate_beats_poor(self):
        good = score_fit(_resume(), _jd())
        poor = score_fit(
            _resume(
                skills={"languages": ["Cobol"]},
                work_experience=[
                    WorkExperience(
                        company="X", title="Intern", start_date=date(2024, 1, 1),
                        bullets=["Wrote Cobol"], technologies=["Cobol"],
                    ),
                ],
                total_yoe=0.5,
                seniority_level="intern",
                raw_text="Cobol intern",
            ),
            _jd(),
        )
        assert good.total_score > poor.total_score

    def test_dimensions_sum_to_total(self):
        result = score_fit(_resume(), _jd())
        dim_total = sum(d.weighted_score for d in result.dimensions)
        assert abs(dim_total - result.total_score) < 1.0  # floating point tolerance

    def test_weights_sum_to_one(self):
        result = score_fit(_resume(), _jd())
        weight_total = sum(d.weight for d in result.dimensions)
        assert abs(weight_total - 1.0) < 0.01

    def test_dealbreakers_flagged(self):
        underqualified = _resume(total_yoe=1.0, seniority_level="intern")
        result = score_fit(underqualified, _jd(required_experience_years=10, seniority_level="principal"))
        assert len(result.dealbreakers) >= 1
        assert "Dealbreaker" in result.match_summary or "dealbreaker" in result.match_summary.lower()
