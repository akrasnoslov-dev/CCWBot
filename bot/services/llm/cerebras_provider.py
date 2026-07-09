"""Cerebras provider (first fallback). OpenAI-compatible chat-completions API."""

from bot.services.llm.base_provider import OpenAICompatibleProvider


class CerebrasProvider(OpenAICompatibleProvider):
    name = "cerebras"


_provider = CerebrasProvider()


def get_provider() -> CerebrasProvider:
    return _provider
