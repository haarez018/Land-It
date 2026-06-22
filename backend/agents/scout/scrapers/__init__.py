"""
Job board scraper modules.

Each scraper implements the BaseScraper interface.
All scrapers are stubs that raise NotImplementedError
when API keys / credentials are not configured.
"""

from backend.agents.scout.scrapers.base import BaseScraper, ScrapedJob

__all__ = ["BaseScraper", "ScrapedJob"]
