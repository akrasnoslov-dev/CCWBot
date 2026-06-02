from bot.runtime import log
from bot.runtime.bootstrap import main
from bot.runtime.event_loop import create_event_loop, get_stop_signals
from bot.runtime.telegram_app import register_handlers

__all__ = ["create_event_loop", "get_stop_signals", "main", "register_handlers"]


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("ops_event=bot_stopped_by_user")
