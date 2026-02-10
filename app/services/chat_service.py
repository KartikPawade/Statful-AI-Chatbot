from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import ollama
from google import genai

from app.core.config import Settings
from app.core.tokens import estimate_tokens
from app.db.redis_store import ChatRepository
from app.services.llm.providers import (
    GeminiProvider,
    LLMProvider,
    OllamaProvider,
    ProviderName,
)
from app.services.memory.memory import (
    ChatSession,
    MemoryStrategy,
    Message,
    apply_rolling_summary,
    apply_sliding_window,
)


@dataclass
class ChatResult:
    provider: ProviderName
    reply: str
    session_id: Optional[str] = None


class ChatService:
    """
    Professional workflow: Request (message + session_id) → Fetch from Redis →
    Truncation (token limit → summarization) → Call LLM → Save new pair to Redis.
    """

    def __init__(self, settings: Settings, repository: ChatRepository):
        self._settings = settings
        self._repo = repository
        self._gemini: GeminiProvider | None = None  # lazy: created with API key from .env
        self._ollama = OllamaProvider(
            model=settings.ollama_model,
            client=ollama.Client(host=settings.ollama_host),
        )

    def _get_gemini(self) -> GeminiProvider:
        """Create Gemini client using GOOGLE_API_KEY from .env (loaded via settings)."""
        if self._gemini is None:
            key = self._settings.google_api_key
            if not key:
                raise ValueError(
                    "Gemini requires GOOGLE_API_KEY. Set GOOGLE_API_KEY=your_key in .env "
                    "(project root) and restart the server."
                )
            self._gemini = GeminiProvider(
                model=self._settings.gemini_model,
                client=genai.Client(api_key=key),
            )
        return self._gemini

    def _get_provider(self, provider: str) -> tuple[ProviderName, LLMProvider]:
        p = (provider or "").lower().strip()
        if p in ("gemini", ""):
            return "gemini", self._get_gemini()
        if p in ("ollama", "local"):
            return "ollama", self._ollama
        raise ValueError("Provider must be 'gemini' or 'ollama'")

    def _session_tokens(self, session: ChatSession) -> int:
        return estimate_tokens(session.transcript())

    def ask(
        self,
        prompt: str,
        provider: str,
        *,
        session_id: Optional[str] = None,
        memory: Optional[str] = None,
        max_messages: Optional[int] = None,
        keep_last: Optional[int] = None,
        window_size: Optional[int] = None,
    ) -> ChatResult:
        provider_name, llm = self._get_provider(provider)

        mem: MemoryStrategy = (memory or self._settings.memory_strategy or "rolling")  # type: ignore[assignment]
        if mem not in ("rolling", "window", "none"):
            mem = "rolling"

        # Stateless: no persistence
        if not session_id or mem == "none":
            reply = llm.generate(prompt)
            return ChatResult(provider=provider_name, reply=reply, session_id=session_id)

        # --- Fetch: last N messages + summary from Redis ---
        fetch_n = self._settings.fetch_last_n
        summary = self._repo.get_summary(session_id)
        messages = self._repo.get_last_messages(session_id, limit=fetch_n)
        session = ChatSession(summary=summary, messages=messages)

        # --- Add current user message ---
        user_msg = Message(role="user", content=prompt)
        session.messages.append(user_msg)

        max_tokens = self._settings.max_tokens_before_summarize
        keep_last_n = keep_last or self._settings.keep_last
        max_msg = max_messages or self._settings.max_messages
        win_size = window_size or self._settings.window_size

        # --- Truncation: if over token limit, run summarization first ---
        if mem == "rolling":
            if self._session_tokens(session) > max_tokens:
                apply_rolling_summary(
                    session=session,
                    provider=llm,
                    max_messages=max_msg,
                    keep_last=keep_last_n,
                )
                self._repo.set_summary(session_id, session.summary)
                self._repo.trim_messages(session_id, keep_last_n)
        elif mem == "window":
            apply_sliding_window(session=session, window_size=win_size)

        # --- Call: send managed history to LLM ---
        compiled_prompt = session.transcript().strip() + "\n\nASSISTANT:"
        reply = llm.generate(compiled_prompt).strip()

        # --- Save: update Redis with new user/assistant pair ---
        assistant_msg = Message(role="assistant", content=reply)
        self._repo.append_messages(session_id, [user_msg, assistant_msg])
        if mem == "window":
            self._repo.trim_messages(session_id, win_size)

        return ChatResult(provider=provider_name, reply=reply, session_id=session_id)

    def list_gemini_models(self) -> list[dict]:
        models = self._get_gemini().client.models.list()
        return [
            {"name": getattr(m, "name", None), "display_name": getattr(m, "display_name", None)}
            for m in models
        ]
