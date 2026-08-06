"""The ops-agent's copy of the shipped model defaults must not drift from the bot's.

The ops-agent image does not contain `bot/`, so the drift detector cannot import the real
defaults and keeps its own copy. This test is what stops that copy from going stale: change a
model default in the bot without updating the ops-agent table and the build fails, rather than
the drift detector silently comparing against a value nobody ships any more.
"""

from __future__ import annotations

from ops_agent.expected_models import SHIPPED_DEFAULT_MODELS

from bot.services.llm import config as llm_config


def test_ops_agent_expected_models_match_the_bot_defaults():
    bot_defaults = {
        call_type: default
        for call_type, (_env, default) in llm_config._GROQ_MODEL_ENV_BY_CALL_TYPE.items()
    }

    assert SHIPPED_DEFAULT_MODELS == bot_defaults


def test_no_shipped_default_is_a_known_decommissioned_model():
    from ops_agent.expected_models import KNOWN_DECOMMISSIONED_MODELS

    assert not (set(SHIPPED_DEFAULT_MODELS.values()) & KNOWN_DECOMMISSIONED_MODELS)
