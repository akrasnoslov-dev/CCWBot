"""Central callback-query router for Telegram inline keyboards."""

from telegram import Update
from telegram.ext import ContextTypes

from bot.alerts import schedule_automatic_market_check
from bot.keyboards import build_interval_keyboard
from bot.prices import send_manual_rate_limit_message, send_price_message
from bot.reports import send_daily_report_message, send_weekly_report_message
from bot.services.price_service import CoinGeckoRateLimitError
from bot.settings import (
    get_db_alert_settings,
    get_state_alert_settings,
    normalize_automatic_check_interval_seconds,
    save_interval_setting,
)
from bot.storage import load_state

from .admin import send_admin_callback_response
from .common import _callback_command_update, _mark_denied, handlers_module, log_request, logger


@log_request("callback")
async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""

    try:
        root = handlers_module()
        is_admin_callback = data.startswith("settings:") or data.startswith("admin:")
        if is_admin_callback and not await root.is_admin_user(
            query.from_user.id if query.from_user else None,
        ):
            _mark_denied(context)
            await query.answer("Sorry, only the bot admin can change settings.")
            await query.message.reply_text("Sorry, only the bot admin can change settings.")
            return

        if data.startswith("admin:"):
            await query.answer()
            if await send_admin_callback_response(data, query.message, context.application):
                return

        if data.startswith("watchlist:"):
            handled = await root.handle_watchlist_callback(update, data)
            if handled:
                return
        await query.answer()

        if data.startswith("price:"):
            await send_price_message(query.message, data.split(":", maxsplit=1)[1])
            return
        if data == "reports:daily":
            await send_daily_report_message(query.message)
            return
        if data == "reports:weekly":
            await send_weekly_report_message(query.message)
            return
        if data == "plan:my_plan":
            await root.myplan_command(_callback_command_update(update))
            return
        if data == "plan:subscribe":
            await root.send_subscribe_invoice(_callback_command_update(update), context)
            return
        if data == "settings:current":
            if root.DB_ENABLED and root.DB_SESSION_LOCAL:
                alert_settings = await get_db_alert_settings()
            else:
                state = load_state()
                alert_settings = get_state_alert_settings(state)
            await query.message.reply_text(
                "Current alert settings ⚙️\n\n"
                "Event decision: Groq LLM JSON analysis\n"
                "Movement thresholds: disabled for automatic Event Alerts\n"
                "Event Alert analysis interval: "
                f"{alert_settings['automatic_check_interval_seconds']} seconds"
            )
            return
        if data == "settings:interval_menu":
            await query.message.reply_text(
                "Choose a new Event Alert analysis interval:",
                reply_markup=build_interval_keyboard(),
            )
            return
        if data.startswith("settings:set_interval:"):
            interval = int(data.rsplit(":", maxsplit=1)[1])
            applied_interval = normalize_automatic_check_interval_seconds(interval)
            await save_interval_setting(applied_interval)
            schedule_automatic_market_check(context.application, applied_interval)
            interval = applied_interval
            await query.message.reply_text(
                f"Event Alert analysis interval updated to {interval} seconds ✅ "
                "Applied immediately."
            )
            return
    except CoinGeckoRateLimitError:
        await send_manual_rate_limit_message(
            query.message, query.message.chat_id if query.message else None
        )
    except ValueError as error:
        logger.warning("Callback price lookup failed: %s", error)
        await query.message.reply_text("Price data is temporarily unavailable.")
    except Exception as error:
        logger.exception("Callback handling failed: %s", error)
        await query.message.reply_text("Sorry, something went wrong.")
