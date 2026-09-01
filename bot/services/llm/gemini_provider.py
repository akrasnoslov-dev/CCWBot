"""Gemini provider (second fallback).

Reached through Google's OpenAI-compatible endpoint so the provider code stays uniform with
Groq/Mistral and no extra client dependency is required.
"""

from bot.services.llm.base_provider import OpenAICompatibleProvider


class GeminiProvider(OpenAICompatibleProvider):
    name = "gemini"


_provider = GeminiProvider()


def get_provider() -> GeminiProvider:
    return _provider
