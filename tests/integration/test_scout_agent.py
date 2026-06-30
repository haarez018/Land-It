"""Integration tests for the Scout agent."""

import pytest
from datetime import date

from backend.agents.scout.agent import ScoutAgent, ScoutResult, ScoredJob
from backend.agents.scout.scorer import score_fit
from backend.agents.scout.scrapers.base import BaseScraper, ScrapedJob
from backend.parsers.schemas import (
    Resume, ResumeContact, WorkExperience, Education,
    JobDescription, JDRequirement,
)
from typing import Optional


def _resume() -> Resume:
    return Resume(
        contact=ResumeContact(name="Jane Doe", email="j@t.com", location="SF"),
        work_experience=[
            WorkExperience(
                company="TechCo",
                title="Senior Backend Engineer",
                start_date=date(2018, 1, 1),
                bullets=["Built payment system"],
                technologies=["Python", "Go", "PostgreSQL", "Kubernetes"],
            ),
        ],
        education=[Education(institution="MIT", degree="BS", field="CS")],
        skills={
            "languages": ["Python", "Go", "TypeScript"],
            "databases": ["PostgreSQL", "Redis"],
            "infra": ["Kubernetes", "Docker"],
        },
        total_yoe=7.0,
        seniority_level="senior",
        primary_domain="fintech",
        raw_text="Senior backend engineer Python Go PostgreSQL Kubernetes",
    )


_SAMPLE_JD = """
Senior Backend Engineer at Stripe
San Francisco, CA (Hybrid)

We're looking for a Senior Backend Engineer to join our payments infrastructure team.

Requirements:
- 5+ years backend development experience
- Strong Python and Go skills
- Experience with PostgreSQL and distributed systems
- Kubernetes experience preferred

Tech Stack: Python, Go, PostgreSQL, Docker, Kubernetes, gRPC

We value moving fast, thinking big, and being transparent.
"""


class MockScraper(BaseScraper):
    """Mock scraper for testing."""
    source_name = "mock"

    def __init__(self, jobs: list[ScrapedJob]):
        self._jobs = jobs

    async def search(self, query: str, location: str = "", *, max_results: int = 25) -> list[ScrapedJob]:
        return self._jobs[:max_results]

    async def get_job_details(self, url: str) -> Optional[ScrapedJob]:
        for j in self._jobs:
            if j.url == url:
                return j
        return None


class FailingScraper(BaseScraper):
    """Scraper that always fails."""
    source_name = "failing"

    async def search(self, query: str, location: str = "", *, max_results: int = 25) -> list[ScrapedJob]:
        raise NotImplementedError("Not configured")

    async def get_job_details(self, url: str) -> Optional[ScrapedJob]:
        raise NotImplementedError("Not configured")


class TestScoutAgentScoreSingleJD:

    @pytest.mark.asyncio
    async def test_score_single_jd(self):
        agent = ScoutAgent()
        result = await agent.score_single_jd(_resume(), _SAMPLE_JD)
        assert isinstance(result, ScoutResult)
        assert result.total_scored == 1
        assert len(result.jobs) == 1
        assert result.jobs[0].fit.total_score > 0

    @pytest.mark.asyncio
    async def test_scored_job_has_fit_dimensions(self):
        agent = ScoutAgent()
        result = await agent.score_single_jd(_resume(), _SAMPLE_JD)
        job = result.jobs[0]
        assert len(job.fit.dimensions) == 8
        assert job.fit.match_summary

    @pytest.mark.asyncio
    async def test_good_match_scores_high(self):
        agent = ScoutAgent()
        result = await agent.score_single_jd(_resume(), _SAMPLE_JD)
        assert result.jobs[0].fit.total_score >= 50


class TestScoutAgentScoreBatch:

    @pytest.mark.asyncio
    async def test_score_batch(self):
        agent = ScoutAgent()
        jds = [_SAMPLE_JD, "Junior Cobol Developer at Rural Corp. Must know Cobol and FORTRAN."]
        result = await agent.score_batch(_resume(), jds)
        assert result.total_found == 2
        assert result.total_scored == 2

    @pytest.mark.asyncio
    async def test_batch_sorted_by_fit(self):
        agent = ScoutAgent()
        jds = [
            "Junior Cobol Developer. Requires FORTRAN and Cobol experience.",
            _SAMPLE_JD,  # Should score higher for our Python/Go senior resume
        ]
        result = await agent.score_batch(_resume(), jds)
        if len(result.jobs) >= 2:
            assert result.jobs[0].fit.total_score >= result.jobs[1].fit.total_score


class TestScoutAgentSearchAndScore:

    @pytest.mark.asyncio
    async def test_with_mock_scraper(self):
        mock_jobs = [
            ScrapedJob(
                title="Senior Backend Engineer",
                company="Stripe",
                location="SF",
                description=_SAMPLE_JD,
                url="https://stripe.com/jobs/123",
                source="mock",
            ),
        ]
        agent = ScoutAgent(scrapers=[MockScraper(mock_jobs)])
        result = await agent.search_and_score(_resume(), "backend engineer")

        assert result.total_found == 1
        assert result.total_scored >= 1
        assert "mock" in result.sources_searched

    @pytest.mark.asyncio
    async def test_failing_scraper_reports_errors(self):
        agent = ScoutAgent(scrapers=[FailingScraper()])
        result = await agent.search_and_score(_resume(), "backend")

        assert result.total_found == 0
        assert len(result.errors) >= 1
        assert "failing" in result.errors[0].lower()

    @pytest.mark.asyncio
    async def test_mixed_scrapers(self):
        mock_jobs = [
            ScrapedJob(
                title="Engineer",
                company="Co",
                location="Remote",
                description="Python Go Engineer role",
                url="https://example.com/1",
                source="mock",
            ),
        ]
        agent = ScoutAgent(scrapers=[MockScraper(mock_jobs), FailingScraper()])
        result = await agent.search_and_score(_resume(), "engineer")

        # Mock scraper succeeds, failing one reports error
        assert "mock" in result.sources_searched
        assert len(result.errors) >= 1

    @pytest.mark.asyncio
    async def test_no_scrapers_returns_empty(self):
        agent = ScoutAgent(scrapers=[])
        result = await agent.search_and_score(_resume(), "engineer")
        assert result.total_found == 0
        assert result.total_scored == 0

    @pytest.mark.asyncio
    async def test_min_fit_score_filters(self):
        mock_jobs = [
            ScrapedJob(
                title="Junior Cobol Dev",
                company="X",
                location="Antarctica",
                description="Must know Cobol and FORTRAN only",
                url="https://x.com/1",
                source="mock",
            ),
        ]
        agent = ScoutAgent(scrapers=[MockScraper(mock_jobs)])
        result = await agent.search_and_score(
            _resume(), "cobol", min_fit_score=90.0
        )
        # The Cobol job should not score 90+ for a Python/Go dev
        assert result.total_scored == 0


class TestScoutAgentLangGraph:

    @pytest.mark.asyncio
    async def test_run_score_jd(self):
        agent = ScoutAgent()
        state = {
            "resume": _resume(),
            "action": "score_jd",
            "jd_text": _SAMPLE_JD,
        }
        result = await agent.run(state)
        assert "scout_result" in result
        assert result["scout_result"].total_scored == 1

    @pytest.mark.asyncio
    async def test_run_score_batch(self):
        agent = ScoutAgent()
        state = {
            "resume": _resume(),
            "action": "score_batch",
            "jd_texts": [_SAMPLE_JD],
        }
        result = await agent.run(state)
        assert result["scout_result"].total_scored == 1

    @pytest.mark.asyncio
    async def test_run_unknown_action(self):
        agent = ScoutAgent()
        state = {"resume": _resume(), "action": "invalid"}
        result = await agent.run(state)
        assert len(result["scout_result"].errors) >= 1
