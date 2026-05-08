from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ai_agent_groq import _parse_json


def test_clean_json_parses_correctly():
    assert _parse_json('{"ok": true, "count": 2}') == {"ok": True, "count": 2}


def test_json_wrapped_in_markdown_fence_parses_correctly():
    assert _parse_json('```json\n{"ok": true}\n```') == {"ok": True}


def test_json_with_surrounding_whitespace_parses_correctly():
    assert _parse_json('\n  {"ok": true}  \n') == {"ok": True}


def test_invalid_json_returns_none():
    assert _parse_json("not json") is None
