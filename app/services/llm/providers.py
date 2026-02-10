from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

import ollama
from google import genai


ProviderName = Literal["gemini", "ollama"]


class LLMProvider(Protocol):
    name: ProviderName

    def generate(self, prompt: str) -> str: ...

    def summarize(self, text: str) -> str: ...


@dataclass
class GeminiProvider:
    model: str
    client: genai.Client  # created with api_key from .env (GOOGLE_API_KEY)
    name: ProviderName = "gemini"

    def generate(self, prompt: str) -> str:
        # Same as: gemini_client.models.generate_content(model="...", contents=prompt)
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        return (response.text if hasattr(response, "text") else "") or ""

    def summarize(self, text: str) -> str:
        prompt = (
            "Summarize the key points of this chat so far.\n\n"
            "Requirements:\n"
            "- Keep names, goals, constraints, decisions, and open questions\n"
            "- Use concise bullet points\n"
            "- Do not invent details\n\n"
            f"CHAT:\n{text}"
        )
        return self.generate(prompt)


@dataclass
class OllamaProvider:
    model: str
    client: ollama.Client  # host from .env (OLLAMA_HOST), model from .env (OLLAMA_MODEL)
    name: ProviderName = "ollama"

    def generate(self, prompt: str) -> str:
        # Same as: ollama_client.chat(model='llama3', messages=[{'role': 'user', 'content': prompt}])
        response = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return (response.get("message") or {}).get("content", "") or ""

    def summarize(self, text: str) -> str:
        prompt = (
            "Summarize the key points of this chat so far.\n\n"
            "Requirements:\n"
            "- Keep names, goals, constraints, decisions, and open questions\n"
            "- Use concise bullet points\n"
            "- Do not invent details\n\n"
            f"CHAT:\n{text}"
        )
        return self.generate(prompt)

