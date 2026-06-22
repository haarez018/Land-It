"""Application configuration via pydantic-settings. All env vars from .env are loaded here."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Anthropic
    ANTHROPIC_API_KEY: Optional[str] = None

    # JSearch (RapidAPI) — free scrapers are used by default, this is optional
    JSEARCH_API_KEY: Optional[str] = None

    # OpenAI (embeddings + Whisper)
    OPENAI_API_KEY: Optional[str] = None

    # Supabase
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_KEY: Optional[str] = None

    # Redis (for Celery)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Gmail OAuth
    GMAIL_CLIENT_ID: Optional[str] = None
    GMAIL_CLIENT_SECRET: Optional[str] = None
    GMAIL_REDIRECT_URI: str = "http://localhost:8000/api/auth/callback/gmail"

    # ChromaDB
    CHROMA_PERSIST_PATH: str = "./data/chroma"

    # Database
    DATABASE_URL: str = "sqlite:///./data/career_copilot.db"

    # ElevenLabs (TTS in Coach)
    ELEVENLABS_API_KEY: Optional[str] = None

    # App settings
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    CORS_ORIGINS: str = "http://localhost:5173"
    WEEKLY_PLANNER_CRON: str = "0 18 * * 0"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


settings = Settings()
