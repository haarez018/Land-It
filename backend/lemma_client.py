from functools import lru_cache
from lemma_sdk import Pod
from backend.config import settings

@lru_cache(maxsize=1)
def get_pod() -> Pod:
    """Initialize and cache the Lemma Pod client."""
    # Ensure variables are available in os.environ for Pod.from_env()
    import os
    if settings.LEMMA_TOKEN:
        os.environ["LEMMA_TOKEN"] = settings.LEMMA_TOKEN
    if settings.LEMMA_POD_ID:
        os.environ["LEMMA_POD_ID"] = settings.LEMMA_POD_ID

    return Pod.from_env()
