import unittest
from typing import Any, Dict, Optional

from app.services.llm.client import LlmClientSettings
from app.services.turn.dependencies import build_turn_llm_dependencies


class FakeAdapter:
    def __init__(self, responses: list[str]) -> None:
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
        return self.responses.pop(0)


class TurnDependenciesTests(unittest.TestCase):
    def test_turn_llm_dependencies_route_json_calls_through_client(self) -> None:
        adapter = FakeAdapter(['{"story": "ok", "patch": {}, "requests": []}'])
        events: list[Dict[str, Any]] = []
        deps = build_turn_llm_dependencies(
            adapter=adapter,
            settings=LlmClientSettings(
                timeout_sec=240,
                temperature=0.6,
                response_schema={"type": "object", "required": ["story", "patch", "requests"]},
                error_code_json_repair="json_repair",
            ),
            emit_turn_phase_event=lambda _ctx, **payload: events.append(payload),
            turn_flow_error=lambda **payload: RuntimeError(payload["error_code"]),
        )

        result = deps.call_ollama_json("System", "User", trace_ctx={"trace_id": "trace_1"})

        self.assertEqual(result["story"], "ok")
        self.assertEqual(adapter.calls[0]["timeout"], 240)
        self.assertEqual(events[0]["extra"], {"mode": "parse_ok"})

    def test_turn_llm_dependencies_route_schema_calls_through_client(self) -> None:
        adapter = FakeAdapter(['{"story": "lang"}'])
        deps = build_turn_llm_dependencies(
            adapter=adapter,
            settings=LlmClientSettings(
                timeout_sec=240,
                temperature=0.6,
                response_schema={"type": "object"},
                error_code_json_repair="json_repair",
            ),
            emit_turn_phase_event=lambda *_args, **_kwargs: None,
            turn_flow_error=lambda **payload: RuntimeError(payload["error_code"]),
        )

        result = deps.call_ollama_schema("System", "User", {"type": "object"}, timeout=120, temperature=0.5)

        self.assertEqual(result, {"story": "lang"})
        self.assertEqual(adapter.calls[0]["timeout"], 120)
        self.assertEqual(adapter.calls[0]["temperature"], 0.5)


if __name__ == "__main__":
    unittest.main()
