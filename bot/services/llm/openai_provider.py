"""OpenAI paid fallback, guarded by an explicit kill switch and durable budget."""

from bot.services.llm.base_provider import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    name = "openai"

    def _sampling_parameters(self, *, model: str) -> dict[str, float]:
        return {}

    def _max_tokens_parameters(self, *, max_tokens: int) -> dict[str, int]:
        return {"max_completion_tokens": max_tokens}


_provider = OpenAIProvider()


def get_provider() -> OpenAIProvider:
    return _provider
