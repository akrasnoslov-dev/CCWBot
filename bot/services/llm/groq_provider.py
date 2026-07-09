"""Groq provider (primary). OpenAI-compatible chat-completions API."""

from bot.services.llm.base_provider import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    name = "groq"


_provider = GroqProvider()


def get_provider() -> GroqProvider:
    return _provider
