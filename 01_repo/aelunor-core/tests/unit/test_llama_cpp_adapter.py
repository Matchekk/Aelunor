"""Tests für den experimentellen llama.cpp OpenAI-Adapter + Provider-Wahl."""
from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import patch

from app.adapters.llama_cpp_adapter import LlamaCppOpenAIAdapter, LlamaCppSettings


def _adapter() -> LlamaCppOpenAIAdapter:
    return LlamaCppOpenAIAdapter(
        LlamaCppSettings(
            base_url="http://127.0.0.1:8088/v1",
            model="gemma-3n-e4b",
            timeout_sec=240,
            temperature=0.6,
            num_ctx=32768,
            max_tokens=6144,
            seed=7,
        )
    )


class _FakeResp:
    def __init__(self, status: int, payload: Dict[str, Any]) -> None:
        self.status_code = status
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self) -> Dict[str, Any]:
        return self._payload


def test_default_provider_stays_ollama_and_llama_cpp_selectable():
    from app.adapters import llm_config as c
    assert c.select_llm_adapter("ollama").__class__.__name__ == "OllamaAdapter"
    assert c.select_llm_adapter("llama_cpp_openai").__class__.__name__ == "LlamaCppOpenAIAdapter"
    assert c.select_llm_adapter("llamacpp").__class__.__name__ == "LlamaCppOpenAIAdapter"


def test_chat_plain_sends_openai_payload():
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["payload"] = json
        return _FakeResp(200, {"choices": [{"message": {"content": " hallo "}}], "usage": {"prompt_tokens": 5, "completion_tokens": 2}})

    with patch("app.adapters.llama_cpp_adapter.requests.post", fake_post):
        out = _adapter().chat("SYS", "USER")
    assert out == "hallo"
    assert captured["url"].endswith("/v1/chat/completions")
    msgs = captured["payload"]["messages"]
    assert msgs[0] == {"role": "system", "content": "SYS"}
    assert msgs[1] == {"role": "user", "content": "USER"}
    assert captured["payload"]["max_tokens"] == 6144
    assert "response_format" not in captured["payload"]


def test_chat_sends_repeat_penalty_to_prevent_retry_runaway():
    # Regression: der llama.cpp-Server-Default repeat_penalty=1.0 lieferte auf
    # Retry-/Repair-Calls Wiederholungs-Runaways (finish_reason=length) -> stage D.
    # Der Adapter muss die Anti-Repetition-Sampler immer mitsenden.
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured["payload"] = json
        return _FakeResp(200, {"choices": [{"message": {"content": "hi"}}], "usage": {}})

    with patch("app.adapters.llama_cpp_adapter.requests.post", fake_post):
        # Default aus den Settings (kein expliziter Wert vom Aufrufer).
        _adapter().chat("SYS", "USER")
    assert captured["payload"]["repeat_penalty"] == 1.18
    assert captured["payload"]["repeat_last_n"] == 192

    # Expliziter Aufrufer-Wert (z.B. Repair-Pass mit 1.05) hat Vorrang.
    with patch("app.adapters.llama_cpp_adapter.requests.post", fake_post):
        _adapter().chat("SYS", "USER", repeat_penalty=1.05)
    assert captured["payload"]["repeat_penalty"] == 1.05


def test_chat_schema_uses_json_schema_response_format():
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured["payload"] = json
        return _FakeResp(200, {"choices": [{"message": {"content": "{\"x\":1}"}}], "usage": {}})

    schema = {"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"], "additionalProperties": False}
    with patch("app.adapters.llama_cpp_adapter.requests.post", fake_post):
        out = _adapter().chat("SYS", "USER", format_schema=schema)
    assert out == '{"x":1}'
    rf = captured["payload"]["response_format"]
    assert rf["type"] == "json_schema"
    assert rf["json_schema"]["strict"] is True
    assert rf["json_schema"]["schema"] == schema


def test_chat_schema_falls_back_to_json_object_on_400():
    calls = []

    def fake_post(url, json=None, timeout=None):
        calls.append(json)
        if len(calls) == 1:
            return _FakeResp(400, {"error": "grammar rejected"})
        return _FakeResp(200, {"choices": [{"message": {"content": "{\"x\":2}"}}], "usage": {}})

    schema = {"type": "object", "properties": {"x": {"type": "integer"}}}
    with patch("app.adapters.llama_cpp_adapter.requests.post", fake_post):
        out = _adapter().chat("SYS", "USER", format_schema=schema)
    assert out == '{"x":2}'
    assert len(calls) == 2
    # erster Versuch json_schema, Fallback json_object + Schema im Prompt
    assert calls[0]["response_format"]["type"] == "json_schema"
    assert calls[1]["response_format"] == {"type": "json_object"}
    assert "SCHEMA:" in calls[1]["messages"][1]["content"]
