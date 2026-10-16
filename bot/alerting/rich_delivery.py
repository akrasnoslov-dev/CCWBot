"""Single-request Telegram Bot API 10.2+ rich-message transport.

PTB 22.8 does not expose sendRichMessage. Do not use its private methods.
An unacknowledged HTTP request is NEVER retried or followed by a plain send:
Telegram has no per-send idempotency key.
"""
from __future__ import annotations

import json

import httpx
from telegram.error import BadRequest, Forbidden, RetryAfter


class RichDeliveryUncertain(Exception):
    """The Telegram request might have been accepted: never send a duplicate."""


def _returned_photo_file_id(result: object) -> str | None:
    def walk(value: object) -> str | None:
        if isinstance(value, dict):
            photo = value.get("photo")
            if isinstance(photo, list):
                for item in reversed(photo):
                    if isinstance(item, dict) and isinstance(item.get("file_id"), str):
                        return item["file_id"]
            for nested in value.values():
                found = walk(nested)
                if found:
                    return found
        elif isinstance(value, list):
            for nested in value:
                found = walk(nested)
                if found:
                    return found
        return None
    if isinstance(result, dict):
        return walk(result.get("rich_message", {}))
    return None


async def send_rich_event_alert(
    *,
    bot_token: str,
    chat_id: int,
    rich_html: str,
    chart_png: bytes | None,
    chart_file_id: str | None = None,
) -> str | None:
    """Send one rich message; reuse Telegram photo file_id when the API returns one.

    BadRequest indicates confirmed rejection and permits a *single* HTML fallback.
    RichDeliveryUncertain means no fallback or retry is safe.
    """
    media: list[dict] = []
    files = None
    if chart_png is not None:
        reference = chart_file_id or "attach://chart"
        media = [{"id": "chart", "media": {"type": "photo", "media": reference}}]
        if not chart_file_id:
            files = {"chart": ("event-chart.png", chart_png, "image/png")}
    content = {"html": rich_html, "skip_entity_detection": True}
    if media:
        content["media"] = media
    request_data = {
        "chat_id": str(chat_id),
        "rich_message": json.dumps(content, ensure_ascii=False),
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendRichMessage",
                data=request_data,
                files=files,
            )
    except httpx.RequestError as exc:
        # Never stringify exc: the URL includes the private bot token.
        raise RichDeliveryUncertain("Rich delivery acknowledgement unknown") from None

    try:
        payload = response.json()
    except (ValueError, TypeError):
        raise RichDeliveryUncertain("Rich delivery response unreadable") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("ok"), bool):
        raise RichDeliveryUncertain("Rich delivery response invalid")
    if payload["ok"]:
        # A valid Telegram success response is proof of completion.
        if not isinstance(payload.get("result"), dict):
            raise RichDeliveryUncertain("Rich delivery response lacks receipt")
        return _returned_photo_file_id(payload["result"]) or chart_file_id

    code = payload.get("error_code")
    if code == 429:
        parameters = payload.get("parameters") or {}
        try:
            delay = max(int(parameters.get("retry_after", 1)), 1)
        except (TypeError, ValueError, AttributeError):
            delay = 1
        raise RetryAfter(delay)
    if code == 403:
        raise Forbidden("Telegram destination rejected rich message")
    if isinstance(code, int) and 400 <= code < 500:
        raise BadRequest("Telegram explicitly rejected rich message")
    # Server errors might follow a successful send. Never risk a duplicate.
    raise RichDeliveryUncertain("Rich delivery outcome uncertain")
