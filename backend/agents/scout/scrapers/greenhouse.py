"""Greenhouse ATS job scraper stub."""

from typing import Optional
from backend.agents.scout.scrapers.base import BaseScraper, ScrapedJob


class GreenhouseScraper(BaseScraper):
    source_name = "greenhouse"

    async def search(self, query: str, location: str = "", *, max_results: int = 25) -> list[ScrapedJob]:
        raise NotImplementedError(
            "Greenhouse scraper requires configuration. Set GREENHOUSE_API_KEY in .env"
        )

    async def get_job_details(self, url: str) -> Optional[ScrapedJob]:
        raise NotImplementedError("Greenhouse scraper not configured")
