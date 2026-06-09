import unittest
from typing import Any, Dict, Optional

from app.services.llm.client import (
    LlmClientSettings,
    call_ollama_chat,
    call_ollama_json,
    call_ollama_schema,
    call_ollama_text,
)


class FakeAdapter:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.calls: list[Dict[str, Any]] = []

    def chat(
        self,
        system: str,
        user: str,
        *,
        format_schema: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        temperature: Optional[float] = None,
        repeat_penalty: Optional[float] = None,
        num_ctx: Optional[int] = None,
    ) -> str:
        self.calls.append(
            {
                "system": system,
                "user": user,
                "format_schema": format_schema,
                "timeout": timeout,
                "temperature": temperature,
                "repeat_penalty": repeat_penalty,
                "num_ctx": num_ctx,
            }
        )
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return str(response)


def settings() -> LlmClientSettings:
    return LlmClientSettings(
        timeout_sec=240,
        temperature=0.6,
        response_schema={"type": "object", "required": ["story", "patch", "requests"]},
        error_code_json_repair="json_repair",
    )


class LlmClientServiceTests(unittest.TestCase):
    def test_call_ollama_text_uses_text_defaults(self) -> None:
        adapter = FakeAdapter(["Antwort"])

        result = call_ollama_text(adapter, settings(), "System", "User")

        self.assertEqual(result, "Antwort")
        self.assertEqual(adapter.calls[0]["timeout"], 240)
        self.assertEqual(adapter.calls[0]["temperature"], 0.35)
        self.assertEqual(adapter.calls[0]["num_ctx"], 4096)

    def test_call_ollama_chat_retries_without_schema_when_ollama_format_fails(self) -> None:
        adapter = FakeAdapter([RuntimeError("failed to parse grammar"), "{\"ok\": true}"])

        result = call_ollama_chat(
            adapter,
            settings(),
            "System",
            "User",
            format_schema={"type": "object"},
            timeout=42,
            temperature=0.2,
            repeat_penalty=1.1,
        )

        self.assertEqual(result, "{\"ok\": true}")
        self.assertEqual(len(adapter.calls), 2)
        self.assertIsNotNone(adapter.calls[0]["format_schema"])
        self.assertIsNone(adapter.calls[1]["format_schema"])
        self.assertIn("WICHTIGER FALLBACK-HINWEIS", adapter.calls[1]["user"])
        self.assertEqual(adapter.calls[1]["timeout"], 42)
        self.assertEqual(adapter.calls[1]["temperature"], 0.2)
        self.assertEqual(adapter.calls[1]["repeat_penalty"], 1.1)

    def test_call_ollama_json_emits_parse_ok_event(self) -> None:
        adapter = FakeAdapter(['{"story": "Weiter", "patch": {}, "requests": []}'])
        events: list[Dict[str, Any]] = []

        result = call_ollama_json(
            adapter,
            settings(),
            "System",
            "User",
            trace_ctx={"trace_id": "trace_1"},
            emit_turn_phase_event=lambda _ctx, **payload: events.append(payload),
        )

        self.assertEqual(result["story"], "Weiter")
        self.assertEqual(events[0]["extra"], {"mode": "parse_ok"})
        self.assertEqual(adapter.calls[0]["timeout"], 240)
        self.assertEqual(adapter.calls[0]["temperature"], 0.6)

    def test_call_ollama_json_repairs_non_json_response(self) -> None:
        adapter = FakeAdapter([
            "kein json",
            '{"story": "Repariert", "patch": {}, "requests": []}',
        ])
        events: list[Dict[str, Any]] = []

        result = call_ollama_json(
            adapter,
            settings(),
            "System",
            "User",
            trace_ctx={"trace_id": "trace_1"},
            emit_turn_phase_event=lambda _ctx, **payload: events.append(payload),
        )

        self.assertEqual(result["story"], "Repariert")
        self.assertEqual([event["extra"]["mode"] for event in events], ["parse_failed_repair_attempt", "formatless_retry_ok"])
        self.assertIn("WICHTIG: Der vorherige schema-formatierte Aufruf", adapter.calls[1]["user"])
        self.assertIsNone(adapter.calls[1]["format_schema"])
        self.assertEqual(adapter.calls[1]["temperature"], 0.5)

    def test_call_ollama_json_retries_empty_schema_response_without_format(self) -> None:
        adapter = FakeAdapter([
            "",
            '{"story": "Formatlos repariert", "patch": {}, "requests": []}',
        ])
        events: list[Dict[str, Any]] = []

        result = call_ollama_json(
            adapter,
            settings(),
            "System",
            "User",
            trace_ctx={"trace_id": "trace_1"},
            emit_turn_phase_event=lambda _ctx, **payload: events.append(payload),
        )

        self.assertEqual(result["story"], "Formatlos repariert")
        self.assertEqual([event["extra"]["mode"] for event in events], ["parse_failed_repair_attempt", "formatless_retry_ok"])
        self.assertIsNotNone(adapter.calls[0]["format_schema"])
        self.assertIsNone(adapter.calls[1]["format_schema"])

    def test_call_ollama_json_wraps_repair_failure_when_trace_context_exists(self) -> None:
        adapter = FakeAdapter(["kein json", "immer noch kein json"])
        events: list[Dict[str, Any]] = []

        def make_error(**payload: Any) -> Exception:
            return RuntimeError(f"{payload['error_code']}:{payload['phase']}")

        with self.assertRaisesRegex(RuntimeError, "json_repair:narrator_json_parse_repair"):
            call_ollama_json(
                adapter,
                settings(),
                "System",
                "User",
                trace_ctx={"trace_id": "trace_1"},
                emit_turn_phase_event=lambda _ctx, **payload: events.append(payload),
                turn_flow_error=make_error,
            )

        self.assertEqual(events[-1]["extra"], {"mode": "repair_failed"})
        self.assertEqual(events[-1]["error_code"], "json_repair")

    def test_call_ollama_schema_repairs_non_json_response_with_capped_timeout(self) -> None:
        adapter = FakeAdapter(["kein json", '{"ok": true}'])

        result = call_ollama_schema(
            adapter,
            settings(),
            "System",
            "User",
            {"type": "object"},
            timeout=240,
            temperature=0.7,
        )

        self.assertEqual(result, {"ok": True})
        self.assertEqual(adapter.calls[0]["timeout"], 240)
        self.assertEqual(adapter.calls[0]["temperature"], 0.7)
        self.assertEqual(adapter.calls[1]["timeout"], 120)


if __name__ == "__main__":
    unittest.main()
