"""Naukri job scraper stub."""

from typing import Optional
from backend.agents.scout.scrapers.base import BaseScraper, ScrapedJob


class NaukriScraper(BaseScraper):
    source_name = "naukri"

    async def search(self, query: str, location: str = "", *, max_results: int = 25) -> list[ScrapedJob]:
        raise NotImplementedError(
            "Naukri scraper requires configuration. Set NAUKRI_API_KEY in .env"
        )

    async def get_job_details(self, url: str) -> Optional[ScrapedJob]:
        raise NotImplementedError("Naukri scraper not configured")
