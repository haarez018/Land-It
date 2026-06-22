"""
JSearch scraper — aggregates LinkedIn, Indeed, Glassdoor & ZipRecruiter via RapidAPI.

Setup: add JSEARCH_API_KEY to .env (get it at rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)
"""

from __future__ import annotations

import os
from typing import Optional

import httpx

from backend.agents.scout.scrapers.base import BaseScraper, ScrapedJob

_HOST = "jsearch.p.rapidapi.com"
_BASE_URL = f"https://{_HOST}"


class JSearchScraper(BaseScraper):
    """Searches live job listings across LinkedIn, Indeed, Glassdoor, ZipRecruiter."""

    source_name = "jsearch"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("JSEARCH_API_KEY", "")

    @property
    def _headers(self) -> dict:
        return {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": _HOST,
        }

    def _ready(self) -> bool:
        return bool(self.api_key and self.api_key not in ("", "your_key_here"))

    async def search(
        self,
        query: str,
        location: str = "",
        *,
        max_results: int = 20,
        remote_only: bool = False,
        date_posted: str = "week",  # all | today | 3days | week | month
    ) -> list[ScrapedJob]:
        if not self._ready():
            raise NotImplementedError(
                "JSEARCH_API_KEY not set. Get your key at rapidapi.com → JSearch."
            )

        full_query = f"{query} in {location}" if location else query

        params: dict = {
            "query": full_query,
            "num_pages": "1",
            "date_posted": date_posted,
        }
        if remote_only:
            params["remote_jobs_only"] = "true"

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"{_BASE_URL}/search",
                params=params,
                headers=self._headers,
            )
            resp.raise_for_status()
            data = resp.json()

        jobs: list[ScrapedJob] = []
        for item in data.get("data", [])[:max_results]:
            salary_text = _build_salary(item)
            location_str = _build_location(item)
            remote_policy = "remote" if item.get("job_is_remote") else "onsite"
            emp_type = _normalize_employment(item.get("job_employment_type", ""))

            # Pull highlights as tags (qualifications keywords)
            highlights = item.get("job_highlights") or {}
            qualifications = highlights.get("Qualifications", [])
            tags = [q[:60] for q in qualifications[:5]]

            jobs.append(ScrapedJob(
                title=item.get("job_title", ""),
                company=item.get("employer_name", ""),
                location=location_str,
                description=item.get("job_description", ""),
                url=item.get("job_apply_link") or item.get("job_google_link", ""),
                source="jsearch",
                posted_date=item.get("job_posted_at_datetime_utc"),
                salary_text=salary_text,
                remote_policy=remote_policy,
                employment_type=emp_type,
                tags=tags,
            ))

        return jobs

    async def get_job_details(self, url: str) -> Optional[ScrapedJob]:
        return None  # JSearch has no individual detail endpoint


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_salary(item: dict) -> Optional[str]:
    lo = item.get("job_min_salary")
    hi = item.get("job_max_salary")
    if lo and hi:
        period = (item.get("job_salary_period") or "year").lower()
        return f"${lo:,.0f}–${hi:,.0f}/{period}"
    return None


def _build_location(item: dict) -> str:
    parts = [
        item.get("job_city", ""),
        item.get("job_state", ""),
        item.get("job_country", ""),
    ]
    return ", ".join(p for p in parts if p)


def _normalize_employment(raw: str) -> str:
    raw = raw.lower()
    if "part" in raw:
        return "part_time"
    if "contract" in raw or "temp" in raw:
        return "contract"
    if "intern" in raw:
        return "internship"
    return "full_time"
