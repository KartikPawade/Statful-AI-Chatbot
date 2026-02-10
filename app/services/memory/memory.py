from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.services.llm.providers import LLMProvider


MemoryStrategy = Literal["rolling", "window", "none"]


@dataclass
class Message:
    role: Literal["user", "assistant"]
    content: str


@dataclass
class ChatSession:
    summary: str = ""
    messages: list[Message] = field(default_factory=list)

    def transcript(self) -> str:
        parts: list[str] = []
        if self.summary.strip():
            parts.append("SUMMARY SO FAR:\n" + self.summary.strip())
        if self.messages:
            parts.append("RECENT MESSAGES:")
            for m in self.messages:
                parts.append(f"{m.role.upper()}: {m.content}")
        return "\n".join(parts).strip()


def apply_sliding_window(session: ChatSession, window_size: int) -> None:
    if window_size <= 0:
        session.messages = []
        return
    if len(session.messages) > window_size:
        session.messages = session.messages[-window_size:]


def apply_rolling_summary(
    session: ChatSession,
    provider: LLMProvider,
    max_messages: int,
    keep_last: int,
) -> None:
    """
    When history grows beyond max_messages, summarize older messages into session.summary
    and keep only the last keep_last messages.
    """
    if max_messages <= 0:
        return
    if len(session.messages) <= max_messages:
        return

    keep_last = max(0, keep_last)
    older = session.messages[:-keep_last] if keep_last < len(session.messages) else []
    recent = session.messages[-keep_last:] if keep_last > 0 else []

    if not older:
        return

    older_transcript = "\n".join(f"{m.role.upper()}: {m.content}" for m in older)
    if session.summary.strip():
        older_transcript = (
            "Existing summary:\n"
            + session.summary.strip()
            + "\n\nNew messages to incorporate:\n"
            + older_transcript
        )

    session.summary = provider.summarize(older_transcript).strip()
    session.messages = recent

