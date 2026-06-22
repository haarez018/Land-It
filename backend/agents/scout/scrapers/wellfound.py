"""Wellfound (AngelList) job scraper stub."""

from typing import Optional
from backend.agents.scout.scrapers.base import BaseScraper, ScrapedJob


class WellfoundScraper(BaseScraper):
    source_name = "wellfound"

    async def search(self, query: str, location: str = "", *, max_results: int = 25) -> list[ScrapedJob]:
        raise NotImplementedError(
            "Wellfound scraper requires configuration. Set WELLFOUND_API_KEY in .env"
        )

    async def get_job_details(self, url: str) -> Optional[ScrapedJob]:
        raise NotImplementedError("Wellfound scraper not configured")
