"""Mistral provider (third fallback). OpenAI-compatible chat-completions API."""

from bot.services.llm.base_provider import OpenAICompatibleProvider


class MistralProvider(OpenAICompatibleProvider):
    name = "mistral"


_provider = MistralProvider()


def get_provider() -> MistralProvider:
    return _provider
