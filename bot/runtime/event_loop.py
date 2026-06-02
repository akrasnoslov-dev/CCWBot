import asyncio
import signal
import sys


def create_event_loop() -> asyncio.AbstractEventLoop:
    if sys.platform == "win32":
        return asyncio.SelectorEventLoop()
    return asyncio.new_event_loop()


def get_stop_signals() -> tuple[signal.Signals, ...] | None:
    if sys.platform == "win32":
        return None
    return (signal.SIGINT, signal.SIGTERM)
