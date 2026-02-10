"""
Redis-backed persistence for chat history.
Keys: chat:session:{session_id}:messages (list), chat:session:{session_id}:summary (string).
Designed for use with Redis in Docker (e.g. WSL).
"""
from __future__ import annotations

import json
from redis import Redis

from app.services.memory.memory import Message


def _key_messages(session_id: str) -> str:
    return f"chat:session:{session_id}:messages"


def _key_summary(session_id: str) -> str:
    return f"chat:session:{session_id}:summary"


def _serialize_message(m: Message) -> str:
    return json.dumps({"role": m.role, "content": m.content})


def _deserialize_message(s: str) -> Message:
    data = json.loads(s)
    return Message(role=data["role"], content=data["content"])


class ChatRepository:
    """Fetch and save chat history from Redis (fast, survives restarts)."""

    def __init__(self, redis_client: Redis) -> None:
        self._redis = redis_client

    def get_last_messages(self, session_id: str, limit: int = 10) -> list[Message]:
        """Retrieve the last `limit` messages for the session (newest at end)."""
        key = _key_messages(session_id)
        # Redis list: index -1 is newest. We want last `limit` so LRANGE -limit -1
        raw = self._redis.lrange(key, -limit, -1)
        return [_deserialize_message(r.decode("utf-8")) for r in (raw or [])]

    def get_summary(self, session_id: str) -> str:
        """Get the rolling summary for the session, if any."""
        key = _key_summary(session_id)
        val = self._redis.get(key)
        return (val.decode("utf-8") or "").strip() if val else ""

    def append_messages(self, session_id: str, messages: list[Message]) -> None:
        """Append new messages to the session (e.g. one user + one assistant)."""
        if not messages:
            return
        key = _key_messages(session_id)
        for m in messages:
            self._redis.rpush(key, _serialize_message(m))

    def set_summary(self, session_id: str, summary: str) -> None:
        """Store the rolling summary for the session."""
        self._redis.set(_key_summary(session_id), summary)

    def trim_messages(self, session_id: str, keep_last: int) -> None:
        """Keep only the last `keep_last` messages; drop older ones."""
        if keep_last <= 0:
            self._redis.delete(_key_messages(session_id))
            return
        # LTRIM 0 -(keep_last+1) in 0-based terms: keep last keep_last
        # Redis: LTRIM key -(keep_last) -1
        self._redis.ltrim(_key_messages(session_id), -keep_last, -1)
