"""Simple token estimation for truncation/summarization decisions (no external tokenizer)."""


def estimate_tokens(text: str) -> int:
    """Rough token count: ~4 chars per token for English. Use before calling LLM."""
    if not text or not text.strip():
        return 0
    return max(1, len(text) // 4)
