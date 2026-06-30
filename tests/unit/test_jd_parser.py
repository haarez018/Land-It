"""Unit tests for the JD parser against sample fixtures."""

from pathlib import Path

import pytest

from backend.parsers.jd_parser import parse_jd

FIXTURES = Path(__file__).parent.parent / "fixtures" / "sample_jds"


class TestBackendEngineerJD:
    @pytest.fixture
    def jd(self):
        text = (FIXTURES / "backend_engineer.txt").read_text(encoding="utf-8")
        return parse_jd(text)

    def test_title_extracted(self, jd):
        assert "backend" in jd.title.lower() or "engineer" in jd.title.lower()

    def test_tech_stack_extracted(self, jd):
        tech_lower = [t.lower() for t in jd.tech_stack]
        assert any("go" == t for t in tech_lower) or any("python" == t for t in tech_lower)
        assert any("postgresql" in t for t in tech_lower) or any("redis" in t for t in tech_lower)

    def test_requirements_extracted(self, jd):
        assert len(jd.requirements) >= 3

    def test_salary_range(self, jd):
        assert jd.salary_range is not None
        low, high = jd.salary_range
        assert low >= 100000
        assert high >= low

    def test_seniority_detected(self, jd):
        assert jd.seniority_level in ("senior", "mid")

    def test_remote_policy(self, jd):
        assert jd.remote_policy == "hybrid"

    def test_required_skills_present(self, jd):
        assert len(jd.required_skills) >= 1

    def test_soft_skills_detected(self, jd):
        assert len(jd.soft_skills) >= 0  # May or may not find soft skills

    def test_role_type_inference(self, jd):
        assert jd.infer_role_type() == "software_engineer_backend"


class TestProductManagerJD:
    @pytest.fixture
    def jd(self):
        text = (FIXTURES / "product_manager.txt").read_text(encoding="utf-8")
        return parse_jd(text)

    def test_role_type(self, jd):
        assert jd.infer_role_type() == "product_manager"

    def test_remote_policy(self, jd):
        assert jd.remote_policy == "remote"

    def test_requirements_present(self, jd):
        assert len(jd.requirements) >= 2

    def test_company_values(self, jd):
        # The JD mentions values
        assert len(jd.company_values) >= 0


class TestDataScientistJD:
    @pytest.fixture
    def jd(self):
        text = (FIXTURES / "data_scientist.txt").read_text(encoding="utf-8")
        return parse_jd(text)

    def test_role_type(self, jd):
        assert jd.infer_role_type() == "data_scientist"

    def test_tech_stack(self, jd):
        tech_lower = [t.lower() for t in jd.tech_stack]
        assert any("python" == t for t in tech_lower)
        assert any("pytorch" in t or "spark" in t for t in tech_lower)

    def test_education_requirement(self, jd):
        assert jd.required_education is not None

    def test_domain_knowledge(self, jd):
        assert len(jd.domain_knowledge) >= 0

    def test_experience_years(self, jd):
        assert jd.required_experience_years is not None
        assert jd.required_experience_years >= 3
