"""Tests for the /demo endpoint and demo data."""

from __future__ import annotations

import pytest

from backend.fixtures.demo_data import DEMO_RESUME_TEXT, DEMO_JD_TEXT
from backend.parsers.resume_parser import parse_resume_text
from backend.parsers.jd_parser import parse_jd
from backend.agents.tailor.agent import TailorAgent
from backend.agents.scout.salary_intel import estimate_salary


# ── Demo data validity ──────────────────────────────────────────────────────

class TestDemoData:
    def test_demo_resume_not_empty(self):
        assert len(DEMO_RESUME_TEXT) > 200

    def test_demo_jd_not_empty(self):
        assert len(DEMO_JD_TEXT) > 200

    def test_demo_resume_parses(self):
        resume = parse_resume_text(DEMO_RESUME_TEXT)
        assert resume.contact.name
        assert resume.contact.email
        assert len(resume.work_experience) >= 2
        assert len(resume.education) >= 1
        assert resume.total_yoe > 0

    def test_demo_jd_parses(self):
        jd = parse_jd(DEMO_JD_TEXT)
        assert jd.title
        assert jd.company
        assert len(jd.required_skills) > 0 or len(jd.tech_stack) > 0


# ── Demo scoring ────────────────────────────────────────────────────────────

class TestDemoScoring:
    @pytest.fixture
    def resume_and_jd(self):
        return parse_resume_text(DEMO_RESUME_TEXT), parse_jd(DEMO_JD_TEXT)

    async def test_dual_score_returns_result(self, resume_and_jd):
        resume, jd = resume_and_jd
        agent = TailorAgent()
        result = await agent.score_dual(resume, jd)
        assert result.combined_score > 0
        assert result.total_dimensions == 22
        assert result.combined_grade

    async def test_demo_combined_score_reasonable(self, resume_and_jd):
        resume, jd = resume_and_jd
        agent = TailorAgent()
        result = await agent.score_dual(resume, jd)
        assert result.combined_score > 50

    async def test_callback_prediction_positive(self, resume_and_jd):
        resume, jd = resume_and_jd
        agent = TailorAgent()
        result = await agent.score_dual(resume, jd)
        assert result.callback_prediction is not None
        assert result.callback_prediction.probability > 0
        assert result.callback_prediction.probability <= 1.0

    def test_salary_estimate_valid(self, resume_and_jd):
        resume, jd = resume_and_jd
        salary = estimate_salary(resume, jd)
        assert salary.estimated_range[0] > 0
        assert salary.estimated_range[1] > salary.estimated_range[0]
        assert salary.estimated_midpoint > 0
        assert salary.confidence in ("high", "medium", "low")


# ── FastAPI route ───────────────────────────────────────────────────────────

class TestDemoRoute:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        return TestClient(app)

    def test_demo_score_returns_200(self, client):
        resp = client.get("/api/demo/score")
        assert resp.status_code == 200
        data = resp.json()
        assert "dual_score" in data
        assert "salary" in data
        assert "demo_resume_text" in data
        assert "demo_jd_text" in data

    def test_demo_score_has_22_dimensions(self, client):
        resp = client.get("/api/demo/score")
        data = resp.json()
        assert data["dual_score"]["total_dimensions"] == 22

    def test_demo_score_cached(self, client):
        resp1 = client.get("/api/demo/score")
        resp2 = client.get("/api/demo/score")
        assert resp1.json()["dual_score"]["combined_score"] == resp2.json()["dual_score"]["combined_score"]
