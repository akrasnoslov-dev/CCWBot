"""Gemini provider (second fallback).

Reached through Google's OpenAI-compatible endpoint so the provider code stays uniform with
Groq/Mistral and no extra client dependency is required.
"""

from bot.services.llm.base_provider import OpenAICompatibleProvider


class GeminiProvider(OpenAICompatibleProvider):
    name = "gemini"

    def _sampling_parameters(self, *, model: str) -> dict[str, float]:
        """Gemini 3.x deprecates explicit sampling parameters in generation config."""
        if model.strip().lower().startswith("gemini-3."):
            return {}
        return super()._sampling_parameters(model=model)


_provider = GeminiProvider()


def get_provider() -> GeminiProvider:
    return _provider
