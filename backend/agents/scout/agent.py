"""
ScoutAgent: discovers and scores jobs from multiple sources.

Pipeline: scrape/receive jobs → parse JD → score fit → rank → filter
Falls back to manual JD input when scrapers are not configured.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from backend.parsers.schemas import Resume, JobDescription
from backend.parsers.jd_parser import parse_jd
from backend.agents.scout.scorer import FitResult, score_fit, score_fit_ai
from backend.agents.scout.scrapers.base import BaseScraper, ScrapedJob


@dataclass
class ScoredJob:
    """A job listing with fit scoring."""
    jd: JobDescription
    fit: FitResult
    source: str
    source_url: str = ""


@dataclass
class ScoutResult:
    """Complete result from the scout pipeline."""
    jobs: list[ScoredJob]
    sources_searched: list[str]
    total_found: int
    total_scored: int
    errors: list[str] = field(default_factory=list)


class ScoutAgent:
    """Discovers, parses, and fit-scores job listings."""

    def __init__(self, scrapers: Optional[list[BaseScraper]] = None):
        self.scrapers = scrapers or []

    async def run(self, state: dict) -> dict:
        """
        LangGraph-compatible run method.

        Expected state keys:
            - resume: Resume object
            - action: str — "search" | "score_jd" | "score_batch"
            - query: str (for search)
            - location: str (for search, optional)
            - jd_text: str (for score_jd)
            - jd_texts: list[str] (for score_batch)

        Returns updated state with:
            - scout_result: ScoutResult
        """
        resume: Resume = state["resume"]
        action = state.get("action", "search")

        if action == "search":
            result = await self.search_and_score(
                resume,
                query=state.get("query", resume.primary_domain),
                location=state.get("location", ""),
            )
        elif action == "score_jd":
            result = await self.score_single_jd(
                resume, state["jd_text"]
            )
        elif action == "score_batch":
            result = await self.score_batch(
                resume, state.get("jd_texts", [])
            )
        else:
            result = ScoutResult(
                jobs=[], sources_searched=[], total_found=0, total_scored=0,
                errors=[f"Unknown action: {action}"],
            )

        return {**state, "scout_result": result}

    async def search_and_score(
        self,
        resume: Resume,
        query: str,
        location: str = "",
        *,
        max_results: int = 25,
        min_fit_score: float = 40.0,
    ) -> ScoutResult:
        """
        Search all configured scrapers and score results.

        Args:
            resume: Candidate resume for fit scoring
            query: Search query
            location: Location filter
            max_results: Max results per scraper
            min_fit_score: Minimum fit score to include

        Returns:
            ScoutResult with scored and ranked jobs
        """
        all_scraped: list[tuple[ScrapedJob, str]] = []
        sources_searched: list[str] = []
        errors: list[str] = []

        for scraper in self.scrapers:
            try:
                jobs = await scraper.search(query, location, max_results=max_results)
                all_scraped.extend((job, scraper.source_name) for job in jobs)
                sources_searched.append(scraper.source_name)
            except NotImplementedError as e:
                errors.append(f"{scraper.source_name}: {e}")
            except Exception as e:
                errors.append(f"{scraper.source_name}: {e}")

        # Parse and score each job
        scored_jobs: list[ScoredJob] = []
        for scraped, source in all_scraped:
            try:
                jd = parse_jd(scraped.description, source=source, source_url=scraped.url)
                # Enrich JD with scraped metadata
                if scraped.title and not jd.title:
                    jd.title = scraped.title
                if scraped.company and not jd.company:
                    jd.company = scraped.company
                if scraped.location and not jd.location:
                    jd.location = scraped.location
                if scraped.remote_policy:
                    jd.remote_policy = scraped.remote_policy

                fit = await score_fit_ai(resume, jd)
                jd.fit_score = fit.total_score

                if fit.total_score >= min_fit_score:
                    scored_jobs.append(ScoredJob(
                        jd=jd,
                        fit=fit,
                        source=source,
                        source_url=scraped.url,
                    ))
            except Exception as e:
                errors.append(f"Failed to score job from {source}: {e}")

        # Sort by fit score descending
        scored_jobs.sort(key=lambda j: j.fit.total_score, reverse=True)

        return ScoutResult(
            jobs=scored_jobs,
            sources_searched=sources_searched,
            total_found=len(all_scraped),
            total_scored=len(scored_jobs),
            errors=errors,
        )

    async def score_single_jd(
        self, resume: Resume, jd_text: str
    ) -> ScoutResult:
        """Score a single JD text against the resume."""
        jd = parse_jd(jd_text, source="manual")
        fit = score_fit(resume, jd)
        jd.fit_score = fit.total_score

        return ScoutResult(
            jobs=[ScoredJob(jd=jd, fit=fit, source="manual")],
            sources_searched=["manual"],
            total_found=1,
            total_scored=1,
        )

    async def score_batch(
        self,
        resume: Resume,
        jd_texts: list[str],
        *,
        min_fit_score: float = 0.0,
    ) -> ScoutResult:
        """Score a batch of JD texts."""
        scored: list[ScoredJob] = []
        errors: list[str] = []

        for i, text in enumerate(jd_texts):
            try:
                jd = parse_jd(text, source="manual")
                fit = await score_fit_ai(resume, jd)
                jd.fit_score = fit.total_score

                if fit.total_score >= min_fit_score:
                    scored.append(ScoredJob(jd=jd, fit=fit, source="manual"))
            except Exception as e:
                errors.append(f"JD #{i + 1}: {e}")

        scored.sort(key=lambda j: j.fit.total_score, reverse=True)

        return ScoutResult(
            jobs=scored,
            sources_searched=["manual"],
            total_found=len(jd_texts),
            total_scored=len(scored),
            errors=errors,
        )
