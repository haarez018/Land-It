"""Lever ATS job scraper stub."""

from typing import Optional
from backend.agents.scout.scrapers.base import BaseScraper, ScrapedJob


class LeverScraper(BaseScraper):
    source_name = "lever"

    async def search(self, query: str, location: str = "", *, max_results: int = 25) -> list[ScrapedJob]:
        raise NotImplementedError(
            "Lever scraper requires configuration. Set LEVER_API_KEY in .env"
        )

    async def get_job_details(self, url: str) -> Optional[ScrapedJob]:
        raise NotImplementedError("Lever scraper not configured")
