"""FastAPI dependency injection. Stub clients raise NotImplementedError when keys are missing."""

from functools import lru_cache
from typing import Optional

from backend.config import settings


@lru_cache
def get_settings():
    return settings


class AnthropicClient:
    def __init__(self):
        if not settings.ANTHROPIC_API_KEY:
            self._client = None
        else:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    @property
    def client(self):
        if self._client is None:
            raise NotImplementedError(
                "ANTHROPIC_API_KEY not set. Add it to .env to use Anthropic features."
            )
        return self._client


class OpenAIClient:
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            self._client = None
        else:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    @property
    def client(self):
        if self._client is None:
            raise NotImplementedError(
                "OPENAI_API_KEY not set. Add it to .env to use OpenAI features."
            )
        return self._client


class SupabaseClient:
    def __init__(self):
        if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
            self._client = None
        else:
            from supabase import create_client
            self._client = create_client(
                settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY
            )

    @property
    def client(self):
        if self._client is None:
            raise NotImplementedError(
                "SUPABASE_URL and SUPABASE_ANON_KEY not set. Add them to .env."
            )
        return self._client


class ChromaClient:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                import chromadb
                self._client = chromadb.PersistentClient(
                    path=settings.CHROMA_PERSIST_PATH
                )
            except Exception:
                raise NotImplementedError(
                    "ChromaDB not available. Install chromadb and check CHROMA_PERSIST_PATH."
                )
        return self._client


class ElevenLabsClient:
    def __init__(self):
        if not settings.ELEVENLABS_API_KEY:
            self._client = None
        else:
            self._client = True  # Placeholder for real client

    @property
    def client(self):
        if self._client is None:
            raise NotImplementedError(
                "ELEVENLABS_API_KEY not set. Add it to .env to use TTS features."
            )
        return self._client


anthropic_client = AnthropicClient()
openai_client = OpenAIClient()
supabase_client = SupabaseClient()
chroma_client = ChromaClient()
elevenlabs_client = ElevenLabsClient()
