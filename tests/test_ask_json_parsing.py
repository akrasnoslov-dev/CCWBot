import bot.services.ai_agent_groq as ai_agent_groq


def test_parse_json_handles_whitespace_and_invalid_text():
    assert ai_agent_groq._parse_json('\n  {"ok": true}  \n') == {"ok": True}
    assert ai_agent_groq._parse_json("not json") is None
