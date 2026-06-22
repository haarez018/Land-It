"""LinkedIn job scraper stub — requires LinkedIn API credentials."""

from typing import Optional
from backend.agents.scout.scrapers.base import BaseScraper, ScrapedJob


class LinkedInScraper(BaseScraper):
    source_name = "linkedin"

    async def search(self, query: str, location: str = "", *, max_results: int = 25) -> list[ScrapedJob]:
        raise NotImplementedError(
            "LinkedIn scraper requires API credentials. "
            "Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET in .env"
        )

    async def get_job_details(self, url: str) -> Optional[ScrapedJob]:
        raise NotImplementedError("LinkedIn scraper not configured")
