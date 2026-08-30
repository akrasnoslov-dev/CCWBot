"""Provider interface and the shared OpenAI-compatible provider implementation.

``BaseProvider`` is the common contract. ``OpenAICompatibleProvider`` holds the chat-completion
logic generalized out of the old ``_run_groq_chat_completion`` (JSON mode, raw-response header
capture, rate-limit backoff parsing, and usage logging). Groq, Gemini, and Mistral
all speak the OpenAI chat-completions protocol, so each concrete provider is a thin subclass
that only sets its name and reads its base URL / API key from :mod:`bot.services.llm.config`.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx
from openai import AsyncOpenAI

from bot.services.llm import config
from bot.services.llm.errors import AIProviderRateLimitError, LLMRateLimitBackoffActive
from bot.services.llm.operation import current_llm_operation_id
from bot.services.llm.telemetry import (
    RATE_LIMIT_BACKOFF_CALL_TYPES,
    active_rate_limit_backoff,
    classify_ai_error_reason,
    headers_from_error,
    is_provider_quota_exhausted_error,
    is_rate_limit_error,
    message_input_chars,
    response_content,
    safe_error_message,
    start_llm_rate_limit_backoff,
    usage_int,
    usage_status_for_error,
    write_llm_usage_log,
)

logger = logging.getLogger(__name__)


@dataclass
class ProviderResult:
    """Normalized successful chat-completion result returned by every provider."""

    provider: str
    model: str
    raw_content: str
    input_chars: int
    headers: object = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    max_tokens: int | None = None
    # Raw provider response object, retained so callers can reuse existing usage-logging
    # helpers that read token counts from the response.
    response: object = None


class BaseProvider(ABC):
    """Common interface for all LLM providers."""

    name: str = "base"

    def is_configured(self) -> bool:
        """True when this provider has an API key and can be attempted."""
        return config.api_key(self.name) is not None

    @abstractmethod
    async def chat_completion(
        self,
        *,
        call_type: str,
        symbol: str | None,
        model: str,
        messages: list[dict],
        max_tokens: int,
        response_format: dict | None,
        timeout: int = 15,
        reasoning_effort: str | None = None,
    ) -> ProviderResult:
        """Run one chat completion and return a :class:`ProviderResult` on success.

        ``reasoning_effort`` is omitted from the request payload when ``None``, so providers
        and models without reasoning support see exactly the payload they saw before.
        """
        raise NotImplementedError


class OpenAICompatibleProvider(BaseProvider):
    """Shared implementation for OpenAI-compatible chat-completions providers."""

    name = "openai_compatible"

    def __init__(self):
        self._client: AsyncOpenAI | None = None

    def _build_client(self) -> AsyncOpenAI:
        api_key = config.api_key(self.name)
        if not api_key:
            env_name = config.api_key_env(self.name) or f"{self.name.upper()}_API_KEY"
            raise RuntimeError(f"{env_name} is not configured.")
        return AsyncOpenAI(
            api_key=api_key,
            base_url=config.base_url(self.name),
            timeout=httpx.Timeout(20.0, connect=10.0),
            max_retries=0,
        )

    def get_client(self) -> AsyncOpenAI:
        """Create the provider client lazily, only when a call is actually needed."""
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def reset_client(self) -> None:
        self._client = None

    async def chat_completion(
        self,
        *,
        call_type: str,
        symbol: str | None,
        model: str,
        messages: list[dict],
        max_tokens: int,
        response_format: dict | None,
        timeout: int = 15,
        reasoning_effort: str | None = None,
    ) -> ProviderResult:
        input_chars = message_input_chars(messages)
        provider = self.name

        limited_until = None
        if call_type in RATE_LIMIT_BACKOFF_CALL_TYPES:
            limited_until = active_rate_limit_backoff(provider=provider, model=model)
        if limited_until is not None:
            await write_llm_usage_log(
                provider=provider,
                call_type=call_type,
                symbol=symbol,
                model=model,
                status="skipped_due_to_rate_limit",
                input_chars=input_chars,
                output_chars=None,
                max_tokens=max_tokens,
                error_reason="rate_limit_backoff_active",
                error_message=(
                    f"{provider} model {model} is limited until {limited_until.isoformat()}"
                ),
            )
            logger.info(
                "ops_event=llm_call_completed provider=%s model=%s call_type=%s "
                "status=skipped_due_to_rate_limit operation_id=%s",
                provider,
                model,
                call_type,
                current_llm_operation_id(),
            )
            raise LLMRateLimitBackoffActive(
                provider=provider,
                model=model,
                limited_until=limited_until,
            )

        client = self.get_client()
        request_kwargs = {
            "model": model,
            "messages": messages,
            "temperature": 0.0,
            # ``max_tokens`` rather than ``max_completion_tokens``: all providers in the
            # chain accept it, and Groq treats it as an alias of the newer name, so reasoning
            # models still receive the correct budget. See the PR discussion in docs/llm_usage.md.
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            request_kwargs["response_format"] = response_format
        if reasoning_effort is not None:
            request_kwargs["reasoning_effort"] = reasoning_effort

        try:
            completions = client.chat.completions
            raw_resource = getattr(completions, "with_raw_response", None)
            raw_create = getattr(raw_resource, "create", None)
            if raw_create is not None:
                raw_response = await asyncio.wait_for(
                    raw_create(**request_kwargs), timeout=timeout
                )
                headers = getattr(raw_response, "headers", None)
                response = raw_response.parse()
            else:
                response = await asyncio.wait_for(
                    completions.create(**request_kwargs), timeout=timeout
                )
                headers = getattr(response, "headers", None)
        except Exception as error:
            headers = headers_from_error(error)
            status = usage_status_for_error(error)
            await write_llm_usage_log(
                provider=provider,
                call_type=call_type,
                symbol=symbol,
                model=model,
                status=status,
                input_chars=input_chars,
                output_chars=None,
                max_tokens=max_tokens,
                headers=headers,
                error_reason=classify_ai_error_reason(error),
                error_message=safe_error_message(error),
            )
            if is_rate_limit_error(error) and not is_provider_quota_exhausted_error(error):
                retry_after_seconds, limited_until = start_llm_rate_limit_backoff(
                    provider=provider,
                    model=model,
                    call_type=call_type,
                    error=error,
                    headers=headers,
                )
                raise AIProviderRateLimitError(
                    str(error),
                    provider=provider,
                    model=model,
                    retry_after_seconds=retry_after_seconds,
                    limited_until=limited_until,
                ) from error
            raise
        logger.debug(
            "ops_event=llm_call_completed provider=%s model=%s call_type=%s "
            "status=success operation_id=%s",
            provider,
            model,
            call_type,
            current_llm_operation_id(),
        )
        return ProviderResult(
            provider=provider,
            model=model,
            raw_content=response_content(response),
            input_chars=input_chars,
            headers=headers,
            prompt_tokens=usage_int(response, "prompt_tokens"),
            completion_tokens=usage_int(response, "completion_tokens"),
            total_tokens=usage_int(response, "total_tokens"),
            max_tokens=max_tokens,
            response=response,
        )
