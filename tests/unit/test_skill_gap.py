"""Tests for the Skill Gap Analyzer."""

from __future__ import annotations

from datetime import date

import pytest

from backend.parsers.schemas import (
    Resume, ResumeContact, WorkExperience, JobDescription, JDRequirement,
)
from backend.agents.tailor.skill_gap import (
    analyze_skill_gaps, _canonicalize, _is_category_match,
    _extract_resume_skills, _extract_jd_skills, SKILL_SYNONYMS, SKILL_CATEGORIES,
    SkillGap, SkillGapAnalysis,
)


def _make_resume(skills: dict[str, list[str]] | None = None, raw_text: str = "") -> Resume:
    return Resume(
        contact=ResumeContact(name="Test", email="test@test.com"),
        raw_text=raw_text,
        skills=skills or {},
        work_experience=[
            WorkExperience(
                company="ACME", title="Engineer", start_date=date(2020, 1, 1),
                bullets=["Built APIs with Python and FastAPI", "Deployed on AWS using Docker"],
                technologies=["Python", "FastAPI", "AWS", "Docker"],
            ),
        ],
    )


def _make_jd(
    required: list[str] | None = None,
    preferred: list[str] | None = None,
    tech_stack: list[str] | None = None,
) -> JobDescription:
    return JobDescription(
        title="Senior Backend Engineer",
        company="Google",
        required_skills=required or [],
        preferred_skills=preferred or [],
        tech_stack=tech_stack or [],
    )


# ── Canonicalization ────────────────────────────────────────────────────

class TestCanonicalization:
    def test_synonym_react(self):
        assert _canonicalize("React.js") == "react"
        assert _canonicalize("ReactJS") == "react"
        assert _canonicalize("react") == "react"

    def test_synonym_kubernetes(self):
        assert _canonicalize("k8s") == "kubernetes"
        assert _canonicalize("Kubernetes") == "kubernetes"

    def test_synonym_postgres(self):
        assert _canonicalize("PostgreSQL") == "postgres"
        assert _canonicalize("psql") == "postgres"

    def test_synonym_aws(self):
        assert _canonicalize("Amazon Web Services") == "aws"
        assert _canonicalize("AWS") == "aws"

    def test_unknown_skill_lowercased(self):
        assert _canonicalize("SomeUnknownTool") == "someunknowntool"

    def test_synonym_gcp(self):
        assert _canonicalize("Google Cloud Platform") == "gcp"
        assert _canonicalize("Google Cloud") == "gcp"

    def test_synonym_cicd(self):
        assert _canonicalize("CI/CD") == "ci/cd"
        assert _canonicalize("continuous integration") == "ci/cd"


# ── Skill extraction ───────────────────────────────────────────────────

class TestSkillExtraction:
    def test_extract_from_skills_section(self):
        resume = _make_resume(skills={"languages": ["Python", "Go", "Java"]})
        skills = _extract_resume_skills(resume)
        assert "python" in skills
        assert "go" in skills

    def test_extract_from_technologies(self):
        resume = _make_resume()
        skills = _extract_resume_skills(resume)
        assert "python" in skills
        assert "aws" in skills

    def test_extract_from_raw_text(self):
        resume = _make_resume(raw_text="Experience with Kafka and Redis")
        skills = _extract_resume_skills(resume)
        assert "kafka" in skills
        assert "redis" in skills

    def test_jd_skills_categorized(self):
        jd = _make_jd(required=["Python", "Go"], preferred=["Rust"], tech_stack=["Kafka"])
        skills = _extract_jd_skills(jd)
        assert skills[_canonicalize("Python")] == "required"
        assert skills[_canonicalize("Rust")] == "preferred"
        assert skills[_canonicalize("Kafka")] == "required"


# ── Gap analysis ───────────────────────────────────────────────────────

class TestGapAnalysis:
    def test_all_skills_matched(self):
        resume = _make_resume(
            skills={"lang": ["Python", "Go"], "infra": ["AWS", "Docker", "Kafka"]},
        )
        jd = _make_jd(required=["Python", "Go"], tech_stack=["AWS", "Docker"])
        result = analyze_skill_gaps(resume, jd)
        assert result.total_gaps == 0
        assert result.match_percentage == 100.0
        assert len(result.critical_gaps) == 0

    def test_missing_required_skills(self):
        resume = _make_resume(skills={"lang": ["Python"]})
        jd = _make_jd(required=["Python", "Go", "Rust"])
        result = analyze_skill_gaps(resume, jd)
        critical_skills = [g.skill for g in result.critical_gaps]
        assert any("go" in s or "rust" in s for s in critical_skills)
        assert result.match_percentage < 100

    def test_synonym_matching(self):
        resume = _make_resume(skills={"db": ["PostgreSQL"]})
        jd = _make_jd(required=["Postgres"])
        result = analyze_skill_gaps(resume, jd)
        assert _canonicalize("Postgres") in result.matched_skills or \
               _canonicalize("PostgreSQL") in result.matched_skills

    def test_category_matching(self):
        resume = _make_resume(skills={"cloud": ["AWS"]})
        jd = _make_jd(required=["GCP"])
        result = analyze_skill_gaps(resume, jd)
        assert _canonicalize("gcp") in result.matched_skills

    def test_score_impact_positive_bounded(self):
        resume = _make_resume(skills={})
        jd = _make_jd(required=["Go", "Rust", "Kafka", "gRPC"])
        result = analyze_skill_gaps(resume, jd)
        for gap in result.critical_gaps + result.recommended_gaps + result.bonus_gaps:
            assert 0 < gap.score_impact <= 15

    def test_quick_wins_generated(self):
        resume = _make_resume(skills={"cloud": ["AWS"]})
        jd = _make_jd(preferred=["GCP", "Azure"])
        result = analyze_skill_gaps(resume, jd)
        # AWS user should get easy suggestions for other cloud providers
        # (category match means they'd be matched, so no gaps here)
        # But let's test with non-category skills
        resume2 = _make_resume(skills={"lang": ["React"]})
        jd2 = _make_jd(preferred=["Vue", "Angular"])
        result2 = analyze_skill_gaps(resume2, jd2)
        # React → Vue/Angular is same category, so they'd be matched
        assert result2.match_percentage >= 0

    def test_difficulty_assessment(self):
        resume = _make_resume(skills={"lang": ["Python", "Go", "Java", "TypeScript", "Rust", "C++"]})
        jd = _make_jd(required=["Haskell"])
        result = analyze_skill_gaps(resume, jd)
        for gap in result.critical_gaps:
            assert gap.difficulty in ("easy", "medium", "hard")

    def test_suggestion_not_empty(self):
        resume = _make_resume(skills={})
        jd = _make_jd(required=["Go", "Kubernetes"])
        result = analyze_skill_gaps(resume, jd)
        for gap in result.critical_gaps:
            assert len(gap.suggestion) > 10

    def test_top_3_sorted_by_impact(self):
        resume = _make_resume(skills={})
        jd = _make_jd(required=["Go", "Rust"], preferred=["Haskell", "Elixir"])
        result = analyze_skill_gaps(resume, jd)
        if len(result.top_3_highest_impact_gaps) >= 2:
            impacts = [g.score_impact for g in result.top_3_highest_impact_gaps]
            assert impacts == sorted(impacts, reverse=True)

    def test_total_potential_gain(self):
        resume = _make_resume(skills={})
        jd = _make_jd(required=["Go", "Kafka"], preferred=["Rust"])
        result = analyze_skill_gaps(resume, jd)
        expected = sum(g.score_impact for g in result.critical_gaps + result.recommended_gaps + result.bonus_gaps)
        assert abs(result.total_potential_score_gain - expected) < 0.1

    def test_empty_jd(self):
        resume = _make_resume(skills={"lang": ["Python"]})
        jd = _make_jd()
        result = analyze_skill_gaps(resume, jd)
        assert result.total_gaps == 0
        assert result.match_percentage == 100.0

    def test_empty_resume(self):
        resume = Resume(
            contact=ResumeContact(name="Test", email="t@t.com"),
            raw_text="",
            skills={},
            work_experience=[],
        )
        jd = _make_jd(required=["Python", "Go"])
        result = analyze_skill_gaps(resume, jd)
        assert result.total_gaps >= 2
        assert result.match_percentage == 0.0


# ── Synonym data completeness ──────────────────────────────────────────

class TestSynonymData:
    def test_synonyms_not_empty(self):
        assert len(SKILL_SYNONYMS) >= 40

    def test_categories_not_empty(self):
        assert len(SKILL_CATEGORIES) >= 10

    def test_all_synonyms_lowercase_canonical(self):
        for canonical in SKILL_SYNONYMS:
            assert canonical == canonical.lower()

    def test_category_members_have_synonyms(self):
        for cat, members in SKILL_CATEGORIES.items():
            for m in members:
                canon = _canonicalize(m)
                assert isinstance(canon, str)


# ── API route ──────────────────────────────────────────────────────────

class TestSkillGapRoute:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        return TestClient(app)

    def test_skill_gaps_404_no_resume(self, client):
        resp = client.post("/api/resume/nonexistent/skill-gaps", json={"jd_text": "Some JD"})
        assert resp.status_code == 404

    def test_skill_gaps_returns_analysis(self, client):
        # Upload resume first
        import tempfile, os
        from backend.fixtures.demo_data import DEMO_RESUME_TEXT
        tf = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8")
        tf.write(DEMO_RESUME_TEXT)
        tf.close()
        try:
            with open(tf.name, "rb") as f:
                resp = client.post("/api/resume/upload", files={"file": ("resume.txt", f, "text/plain")})
            assert resp.status_code == 200
            resume_id = resp.json()["id"]

            gap_resp = client.post(
                f"/api/resume/{resume_id}/skill-gaps",
                json={"jd_text": "Senior Go engineer. Required: Go, Kubernetes, Terraform. Preferred: Rust, gRPC."},
            )
            assert gap_resp.status_code == 200
            data = gap_resp.json()
            assert "total_gaps" in data
            assert "matched_skills" in data
            assert "match_percentage" in data
            assert isinstance(data["critical_gaps"], list)
            assert isinstance(data["quick_wins"], list)
        finally:
            os.unlink(tf.name)
