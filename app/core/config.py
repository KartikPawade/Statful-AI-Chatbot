import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Project root (directory containing the "app" package)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_env() -> None:
    """Load .env from project root so it works regardless of current working directory."""
    load_dotenv(_PROJECT_ROOT / ".env")
    load_dotenv(_PROJECT_ROOT / ".nev")  # common typo
    load_dotenv()  # cwd override


@dataclass(frozen=True)
class Settings:
    # Providers
    google_api_key: str  # for Gemini; required when using provider=gemini
    default_provider: str
    gemini_model: str
    ollama_host: str
    ollama_model: str

    # Redis (persistence; e.g. run in WSL via Docker)
    redis_url: str

    # Memory / truncation
    memory_strategy: str
    fetch_last_n: int  # how many messages to load from Redis per request
    max_tokens_before_summarize: int  # trigger summarization when history exceeds this
    max_messages: int
    keep_last: int
    window_size: int


@lru_cache
def get_settings() -> Settings:
    """
    Loads env vars from project root .env (and .nev) then cwd. Returns typed settings.
    """
    _load_env()

    def _int(name: str, default: int) -> int:
        raw = os.getenv(name)
        if raw is None or raw == "":
            return default
        try:
            return int(raw)
        except ValueError:
            return default

    return Settings(
        google_api_key=os.getenv("GOOGLE_API_KEY", "").strip(),
        default_provider=os.getenv("DEFAULT_PROVIDER", "gemini"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        memory_strategy=os.getenv("MEMORY_STRATEGY", "rolling"),
        fetch_last_n=_int("FETCH_LAST_N", 10),
        max_tokens_before_summarize=_int("MAX_TOKENS_BEFORE_SUMMARIZE", 4000),
        max_messages=_int("MAX_MESSAGES", 10),
        keep_last=_int("KEEP_LAST", 4),
        window_size=_int("WINDOW_SIZE", 10),
    )

