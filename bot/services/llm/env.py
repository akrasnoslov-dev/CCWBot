"""Environment parsing helpers for the LLM subsystem that fail loudly.

The historical ``_get_int_env`` copies silently returned the default when the configured
value could not be parsed, so a typo in ``.env`` (``GROQ_EVENT_ANALYSIS_MAX_TOKENS=3OO``)
looked identical to "not configured at all". These helpers keep the same fallback-to-default
behaviour — a bad value must never crash the bot — but log a WARNING naming the variable and
the rejected value first.

Only the variable *name* and the rejected *value* are logged, and only for the non-credential
variables these helpers are used for. Credential variables (API keys, tokens, ``DATABASE_URL``)
are never read through this module, so their values can never reach a log line.
"""

import logging
import os
import re

logger = logging.getLogger(__name__)

# Suffixes that mark a variable as credential-like. Values of such variables are never logged,
# even if a caller wires one of these helpers up to one by mistake. The ``TOKEN``/``TOKENS``
# distinction keeps budget variables readable: ``..._TOKEN`` is a credential, while
# ``..._MAX_TOKENS`` is a completion budget whose value is safe and useful to show.
_SECRET_NAME_SUFFIXES = (
    "_KEY",
    "_TOKEN",
    "_SECRET",
    "_PASSWORD",
    "_CREDENTIALS",
    "_DSN",
    "_URL",
)

# Value shapes that look like a credential regardless of the variable name. The realistic
# operator error is pasting a key into the wrong line of .env — the name gate cannot catch
# that, and a WARNING goes to stdout where the redacting file formatter does not run.
_SECRET_VALUE_RE = re.compile(
    r"(?:^(?:sk-|gsk_|AIza|xox[baprs]-|ghp_|github_pat_)"
    r"|^[A-Za-z0-9_\-]{40,}$)"
)

# Upper bound on distinct warnings retained. Nothing request-derived reaches this cache today;
# the cap keeps that true if a future caller wires one of these helpers to dynamic input.
_MAX_WARNED_ENTRIES = 200

# (variable, rejected value) pairs already warned about, so a misconfiguration produces one
# warning rather than one per LLM call. ``reset_env_warning_cache`` re-arms it; the startup
# configuration log calls that first so the warnings are guaranteed to land after logging is
# configured, even when the same value was already rejected during module import.
_warned: set[tuple[str, str]] = set()


def reset_env_warning_cache() -> None:
    """Clear the warn-once cache (startup logging and tests)."""
    _warned.clear()


def _is_secret_name(name: str) -> bool:
    upper = name.upper()
    for marker in ("API_KEY", "APIKEY", "PASSWORD", "SECRET", "TOKEN", "CREDENTIAL"):
        if marker in upper:
            # ..._MAX_TOKENS is a completion budget, not a credential.
            if marker == "TOKEN" and "TOKENS" in upper:
                continue
            return True
    return upper.endswith(_SECRET_NAME_SUFFIXES)


def _looks_like_secret_value(value: str) -> bool:
    return bool(_SECRET_VALUE_RE.match(value))


def _warn_rejected(name: str, raw: str, reason: str, default) -> None:
    collapsed = " ".join(str(raw).split())
    if _is_secret_name(name) or _looks_like_secret_value(collapsed):
        # Never echo a credential value; naming the variable is enough to act on. The value
        # check catches a key pasted into a variable whose name looks harmless.
        shown = "[redacted]"
    else:
        shown = collapsed[:80]
    key = (name, shown)
    if key in _warned:
        return
    if len(_warned) < _MAX_WARNED_ENTRIES:
        _warned.add(key)
    logger.warning(
        "ops_event=llm_config_invalid variable=%s value=%r reason=%s using_default=%s",
        name,
        shown,
        reason,
        default,
    )


def warn_rejected_value(name: str, raw: str, reason: str, default) -> None:
    """Warn once that a configured value was rejected (for callers with custom parsing)."""
    _warn_rejected(name, raw, reason, default)


def get_int_env(name: str, default: int, *, minimum: int = 0, maximum: int | None = None) -> int:
    """Read an int env var, warning once when the configured value is unusable."""
    raw = os.getenv(name)
    if raw is None:
        return default
    stripped = raw.strip()
    if not stripped:
        return default
    try:
        value = int(stripped)
    except ValueError:
        _warn_rejected(name, raw, "not_an_integer", default)
        return default
    if value < minimum:
        _warn_rejected(name, raw, f"below_minimum_{minimum}", default)
        return default
    if maximum is not None and value > maximum:
        _warn_rejected(name, raw, f"above_maximum_{maximum}", default)
        return default
    return value


def get_choice_env(name: str, choices: tuple[str, ...], default: str | None = None) -> str | None:
    """Read a lowercase enum env var, warning once when the value is not an allowed choice.

    An unset or empty variable returns ``default`` without warning: "not configured" is a
    valid state, unlike "configured with a value this code cannot use".
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    stripped = raw.strip().lower()
    if not stripped:
        return default
    if stripped not in choices:
        _warn_rejected(name, raw, f"not_one_of_{'|'.join(choices)}", default)
        return default
    return stripped
