"""
Arbeitnow scraper — 100% free, no API key, international tech jobs (remote-friendly).
API: https://www.arbeitnow.com/api/job-board-api
"""

from __future__ import annotations

import asyncio
import re
from typing import Optional

import httpx

from backend.agents.scout.scrapers.base import BaseScraper, ScrapedJob
from backend.agents.scout.scrapers.ranker import rank_jobs

_BASE_URL = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowScraper(BaseScraper):
    """Fetches tech jobs from Arbeitnow — no API key, always free."""

    source_name = "arbeitnow"

    async def search(
        self,
        query: str,
        location: str = "",
        *,
        max_results: int = 15,
    ) -> list[ScrapedJob]:
        # Fetch 3 pages in parallel for a richer candidate pool (~300 jobs)
        async with httpx.AsyncClient(timeout=20.0) as client:
            responses = await asyncio.gather(
                *[client.get(_BASE_URL, params={"page": p}) for p in range(1, 4)],
                return_exceptions=True,
            )

        seen_urls: set[str] = set()
        pool: list[ScrapedJob] = []

        for resp in responses:
            if isinstance(resp, Exception):
                continue
            try:
                resp.raise_for_status()
                items = resp.json().get("data", [])
            except Exception:
                continue

            for item in items:
                url = item.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                remote_policy = "remote" if item.get("remote") else "onsite"
                pool.append(ScrapedJob(
                    title=item.get("title", ""),
                    company=item.get("company_name", ""),
                    location=item.get("location") or "Remote",
                    description=item.get("description", ""),
                    url=url,
                    source="arbeitnow",
                    posted_date=item.get("created_at"),
                    salary_text=None,
                    remote_policy=remote_policy,
                    employment_type="full_time",
                    tags=item.get("tags", [])[:6],
                ))

        return rank_jobs(query, pool, top_n=max_results, min_score=0.05)

    async def get_job_details(self, url: str) -> Optional[ScrapedJob]:
        return None
