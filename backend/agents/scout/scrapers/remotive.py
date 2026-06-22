"""
Remotive scraper — 100% free, no API key, real remote tech jobs.
API: https://remotive.com/api/remote-jobs
"""

from __future__ import annotations

from typing import Optional

import asyncio
import httpx

from backend.agents.scout.scrapers.base import BaseScraper, ScrapedJob
from backend.agents.scout.scrapers.ranker import rank_jobs

_BASE_URL = "https://remotive.com/api/remote-jobs"

# Remotive category slugs
_CATEGORY_MAP = {
    "software": "software-dev",
    "engineer": "software-dev",
    "developer": "software-dev",
    "frontend": "software-dev",
    "backend": "software-dev",
    "fullstack": "software-dev",
    "devops": "devops-sysadmin",
    "data": "data",
    "machine learning": "data",
    "ml": "data",
    "ai": "data",
    "product": "product",
    "design": "design",
    "marketing": "marketing",
    "qa": "qa",
    "testing": "qa",
}


def _infer_category(query: str) -> str:
    q = query.lower()
    for keyword, category in _CATEGORY_MAP.items():
        if keyword in q:
            return category
    return "software-dev"  # default


class RemotiveScraper(BaseScraper):
    """Fetches real remote jobs from Remotive — no API key, always free."""

    source_name = "remotive"

    async def search(
        self,
        query: str,
        location: str = "",
        *,
        max_results: int = 20,
    ) -> list[ScrapedJob]:
        category = _infer_category(query)

        # Fire two parallel requests:
        # 1. category + search — focused but small pool
        # 2. search only — broader pool across all categories
        async with httpx.AsyncClient(timeout=20.0) as client:
            focused_req   = client.get(_BASE_URL, params={"category": category, "search": query, "limit": 100})
            broad_req     = client.get(_BASE_URL, params={"search": query, "limit": 100})
            focused_resp, broad_resp = await asyncio.gather(focused_req, broad_req, return_exceptions=True)

        seen_urls: set[str] = set()
        pool: list[ScrapedJob] = []

        for resp in (focused_resp, broad_resp):
            if isinstance(resp, Exception):
                continue
            try:
                resp.raise_for_status()
                items = resp.json().get("jobs", [])
            except Exception:
                continue

            for item in items:
                url = item.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                pool.append(ScrapedJob(
                    title=item.get("title", ""),
                    company=item.get("company_name", ""),
                    location=item.get("candidate_required_location") or "Remote",
                    description=item.get("description", ""),
                    url=url,
                    source="remotive",
                    posted_date=item.get("publication_date"),
                    salary_text=item.get("salary") or None,
                    remote_policy="remote",
                    employment_type=_normalize_job_type(item.get("job_type", "")),
                    tags=item.get("tags", [])[:8],
                ))

        # Re-rank the merged pool by query relevance, drop irrelevant
        return rank_jobs(query, pool, top_n=max_results, min_score=0.05)

    async def get_job_details(self, url: str) -> Optional[ScrapedJob]:
        return None


def _normalize_job_type(raw: str) -> str:
    raw = raw.lower()
    if "part" in raw:
        return "part_time"
    if "contract" in raw or "freelance" in raw:
        return "contract"
    if "intern" in raw:
        return "internship"
    return "full_time"
