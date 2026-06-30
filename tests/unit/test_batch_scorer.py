"""Tests for the Batch Scorer."""

from __future__ import annotations

from datetime import date

import pytest

from backend.parsers.schemas import Resume, ResumeContact, WorkExperience, JobDescription
from backend.parsers.jd_parser import parse_jd
from backend.agents.tailor.batch_scorer import batch_score, BatchScoreResult


def _resume() -> Resume:
    return Resume(
        contact=ResumeContact(name="Alex", email="alex@test.com", location="San Francisco, CA"),
        raw_text=(
            "Alex | alex@test.com\nSUMMARY\nSenior backend engineer with 8 years.\n"
            "EXPERIENCE\nSenior Engineer at Google\nJan 2020 - Present\n"
            "- Architected pipeline handling 5M events/day using Kafka and Go\n"
            "- Led team of 8 engineers to redesign service, reliability 94% to 99.7%\n"
            "- Mentored 4 junior engineers\n"
            "SKILLS\nPython, Go, Kafka, PostgreSQL, Redis, Docker, Kubernetes, AWS"
        ),
        skills={"lang": ["Python", "Go"], "infra": ["Kafka", "PostgreSQL", "Redis", "Docker", "Kubernetes", "AWS"]},
        work_experience=[
            WorkExperience(
                company="Google", title="Senior Engineer", start_date=date(2020, 1, 1),
                bullets=["Architected pipeline handling 5M events/day", "Led team of 8 engineers"],
                technologies=["Python", "Go", "Kafka", "PostgreSQL", "AWS"],
                seniority_signals=["led", "architected", "mentored"],
            ),
        ],
        total_yoe=8.0,
        seniority_level="senior",
        primary_domain="backend",
    )


JD_TEXTS = [
    "Senior Backend Engineer at Google. Required: Go, distributed systems, Kafka. Preferred: Python, Kubernetes.",
    "Software Engineer at Stripe. Required: Python, PostgreSQL, API design. Preferred: Go, Redis.",
    "Backend Engineer at Netflix. Required: Java, microservices, AWS. Preferred: Go, Kafka.",
    "Senior SWE at Meta. Required: Python, distributed systems, React. Preferred: Go, ML.",
    "Platform Engineer at Startup. Required: Python, Docker, Kubernetes, Terraform. Preferred: Go, AWS.",
]


class TestBatchScore:
    async def test_single_jd(self):
        resume = _resume()
        jds = [parse_jd(JD_TEXTS[0])]
        result = await batch_score(resume, jds)
        assert isinstance(result, BatchScoreResult)
        assert len(result.entries) == 1
        assert result.best_fit is not None
        assert result.worst_fit is not None
        assert result.best_fit.jd_id == result.worst_fit.jd_id

    async def test_five_jds(self):
        resume = _resume()
        jds = [parse_jd(text) for text in JD_TEXTS]
        result = await batch_score(resume, jds)
        assert len(result.entries) == 5

    async def test_all_entries_scored(self):
        resume = _resume()
        jds = [parse_jd(text) for text in JD_TEXTS[:3]]
        result = await batch_score(resume, jds)
        for entry in result.entries:
            assert entry.ats_score > 0
            assert entry.standout_score > 0
            assert entry.combined_score > 0
            assert entry.callback_probability >= 0
            assert entry.tier in ("Standout", "Strong", "Solid", "Needs Work", "Weak")

    async def test_best_fit_has_highest_combined(self):
        resume = _resume()
        jds = [parse_jd(text) for text in JD_TEXTS]
        result = await batch_score(resume, jds)
        max_combined = max(e.combined_score for e in result.entries)
        assert result.best_fit is not None
        assert result.best_fit.combined_score == max_combined

    async def test_worst_fit_has_lowest_combined(self):
        resume = _resume()
        jds = [parse_jd(text) for text in JD_TEXTS]
        result = await batch_score(resume, jds)
        min_combined = min(e.combined_score for e in result.entries)
        assert result.worst_fit is not None
        assert result.worst_fit.combined_score == min_combined

    async def test_highest_callback(self):
        resume = _resume()
        jds = [parse_jd(text) for text in JD_TEXTS[:3]]
        result = await batch_score(resume, jds)
        max_cb = max(e.callback_probability for e in result.entries)
        assert result.highest_callback is not None
        assert result.highest_callback.callback_probability == max_cb

    async def test_avg_combined_score(self):
        resume = _resume()
        jds = [parse_jd(text) for text in JD_TEXTS[:3]]
        result = await batch_score(resume, jds)
        expected = sum(e.combined_score for e in result.entries) / len(result.entries)
        assert abs(result.avg_combined_score - expected) < 0.2

    async def test_avg_callback_probability(self):
        resume = _resume()
        jds = [parse_jd(text) for text in JD_TEXTS[:2]]
        result = await batch_score(resume, jds)
        expected = sum(e.callback_probability for e in result.entries) / len(result.entries)
        assert abs(result.avg_callback_probability - expected) < 0.001

    async def test_strongest_weakest_dimension(self):
        resume = _resume()
        jds = [parse_jd(text) for text in JD_TEXTS[:2]]
        result = await batch_score(resume, jds)
        assert isinstance(result.strongest_dimension_overall, str)
        assert isinstance(result.weakest_dimension_overall, str)
        assert result.strongest_dimension_overall != ""
        assert result.weakest_dimension_overall != ""

    async def test_recommendation_not_empty(self):
        resume = _resume()
        jds = [parse_jd(text) for text in JD_TEXTS[:3]]
        result = await batch_score(resume, jds)
        assert len(result.recommendation) > 10

    async def test_company_profile_detection(self):
        resume = _resume()
        jd = parse_jd("Senior Engineer. Required: Go, Python.")
        jd.company = "Google"
        result = await batch_score(resume, [jd])
        assert result.entries[0].company_profile_used == "google"

    async def test_top_gap_format(self):
        resume = _resume()
        jds = [parse_jd(text) for text in JD_TEXTS[:2]]
        result = await batch_score(resume, jds)
        for entry in result.entries:
            assert isinstance(entry.top_gap, str)
            assert len(entry.top_gap) > 0

    async def test_common_gaps(self):
        resume = _resume()
        jds = [parse_jd(text) for text in JD_TEXTS]
        result = await batch_score(resume, jds)
        assert isinstance(result.common_gaps, list)


# ── API route ──────────────────────────────────────────────────────────

class TestBatchScoreRoute:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        return TestClient(app)

    def test_batch_score_404(self, client):
        resp = client.post("/api/resume/nonexistent/batch-score", json={"jd_texts": ["test"]})
        assert resp.status_code == 404

    def test_batch_score_too_many_jds(self, client):
        import tempfile, os
        from backend.fixtures.demo_data import DEMO_RESUME_TEXT
        tf = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8")
        tf.write(DEMO_RESUME_TEXT)
        tf.close()
        try:
            with open(tf.name, "rb") as f:
                resp = client.post("/api/resume/upload", files={"file": ("r.txt", f, "text/plain")})
            rid = resp.json()["id"]
            resp = client.post(f"/api/resume/{rid}/batch-score", json={"jd_texts": ["jd"] * 11})
            assert resp.status_code == 400
        finally:
            os.unlink(tf.name)

    def test_batch_score_success(self, client):
        import tempfile, os
        from backend.fixtures.demo_data import DEMO_RESUME_TEXT
        tf = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8")
        tf.write(DEMO_RESUME_TEXT)
        tf.close()
        try:
            with open(tf.name, "rb") as f:
                resp = client.post("/api/resume/upload", files={"file": ("r.txt", f, "text/plain")})
            rid = resp.json()["id"]
            resp = client.post(f"/api/resume/{rid}/batch-score", json={
                "jd_texts": [JD_TEXTS[0], JD_TEXTS[1]],
            })
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["entries"]) == 2
            assert data["best_fit"] is not None
            assert data["avg_combined_score"] > 0
        finally:
            os.unlink(tf.name)
