"""Base scraper interface for job board scrapers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScrapedJob:
    """Raw job listing from a scraper before parsing."""
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str
    posted_date: Optional[str] = None
    salary_text: Optional[str] = None
    remote_policy: str = ""
    employment_type: str = "full_time"
    tags: list[str] = field(default_factory=list)


class BaseScraper(ABC):
    """Interface for job board scrapers."""

    source_name: str = "unknown"

    @abstractmethod
    async def search(
        self,
        query: str,
        location: str = "",
        *,
        max_results: int = 25,
    ) -> list[ScrapedJob]:
        """
        Search for jobs matching the query.

        Args:
            query: Search query (role title, keywords)
            location: Optional location filter
            max_results: Maximum number of results to return

        Returns:
            List of ScrapedJob objects
        """
        ...

    @abstractmethod
    async def get_job_details(self, url: str) -> Optional[ScrapedJob]:
        """
        Get full details for a specific job listing.

        Args:
            url: URL of the job listing

        Returns:
            ScrapedJob with full description, or None if not found
        """
        ...
