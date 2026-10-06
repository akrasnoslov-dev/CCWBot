"""Cloudflare Workers AI provider via its OpenAI-compatible Chat Completions endpoint."""

from bot.services.llm.base_provider import OpenAICompatibleProvider


class CloudflareProvider(OpenAICompatibleProvider):
    name = "cloudflare"


_provider = CloudflareProvider()


def get_provider() -> CloudflareProvider:
    return _provider
