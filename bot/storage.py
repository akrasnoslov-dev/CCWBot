import json
from decimal import Decimal

# Local JSON file used for lightweight single-instance runtime state.
STATE_FILE = "state.json"


def load_state() -> dict:
    """Read bot state from state.json.

    If the file does not exist yet, return default state keys used by the bot.
    """
    try:
        with open(STATE_FILE, encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {
            "last_price": None,
            "last_24h_change": None,
            "last_checked_at": None,
            "last_alert_at": None,
        }


def save_state(state: dict) -> None:
    """Persist bot state to state.json."""
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(state, file, indent=2, default=_json_state_value)


def _json_state_value(value: object) -> str:
    """Preserve Decimal precision in the JSON-only fallback state."""
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
