"""Supabase service-role client for server-side DB operations (bypasses RLS)."""

from __future__ import annotations
from functools import lru_cache
from supabase import create_client, Client
from backend.config import settings


@lru_cache(maxsize=1)
def get_db() -> Client:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env"
        )
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
