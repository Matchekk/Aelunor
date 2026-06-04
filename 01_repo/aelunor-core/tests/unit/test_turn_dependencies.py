import unittest
from typing import Any, Dict, Optional

from app.services.llm.client import LlmClientSettings
from app.services.turn.dependencies import (
    TurnAttributeDependencies,
    TurnCodexDependencies,
    TurnExtractionDependencies,
    TurnPacingDependencies,
    TurnProgressionDependencies,
    build_turn_llm_dependencies,
)


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

    def test_turn_extraction_dependencies_group_only_extractor_ports(self) -> None:
        calls: list[str] = []
        deps = TurnExtractionDependencies(
            build_extractor_context_packet=lambda *_args, **_kwargs: {"packet": True},
            call_canon_extractor=lambda *_args, **_kwargs: {"events_add": ["canon"]},
            call_npc_extractor=lambda *_args, **_kwargs: [{"id": "npc_1"}],
            apply_npc_upserts=lambda *_args, **_kwargs: [{"id": "npc_1", "applied": True}],
            run_canon_gate=lambda *_args, **_kwargs: {"patch": {}, "state": {}, "meta": {}},
            normalize_npc_codex_state=lambda *_args, **_kwargs: calls.append("normalized"),
        )

        self.assertEqual(deps.build_extractor_context_packet()["packet"], True)
        self.assertEqual(deps.call_canon_extractor()["events_add"], ["canon"])
        self.assertEqual(deps.call_npc_extractor()[0]["id"], "npc_1")
        self.assertTrue(deps.apply_npc_upserts()[0]["applied"])
        self.assertIn("meta", deps.run_canon_gate())
        deps.normalize_npc_codex_state({})
        self.assertEqual(calls, ["normalized"])

    def test_turn_progression_dependencies_group_only_progression_and_skill_ports(self) -> None:
        calls: list[str] = []
        deps = TurnProgressionDependencies(
            append_character_change_events=lambda *_args, **_kwargs: calls.append("changes"),
            apply_progression_events=lambda *_args, **_kwargs: {"events": [{"id": "progression_1"}]},
            apply_skill_events=lambda *_args, **_kwargs: [{"id": "skill_1"}],
        )

        deps.append_character_change_events({}, {}, turn_number=3)
        self.assertEqual(deps.apply_progression_events()["events"][0]["id"], "progression_1")
        self.assertEqual(deps.apply_skill_events()[0]["id"], "skill_1")
        self.assertEqual(calls, ["changes"])

    def test_turn_codex_dependencies_group_only_codex_ports(self) -> None:
        deps = TurnCodexDependencies(
            collect_codex_triggers=lambda *_args, **_kwargs: {"triggers": [{"id": "codex_1"}]},
            apply_codex_triggers=lambda *_args, **_kwargs: [{"id": "codex_1", "applied": True}],
        )

        self.assertEqual(deps.collect_codex_triggers()["triggers"][0]["id"], "codex_1")
        self.assertTrue(deps.apply_codex_triggers()[0]["applied"])

    def test_turn_pacing_dependencies_group_only_pacing_and_timing_ports(self) -> None:
        calls: list[str] = []
        deps = TurnPacingDependencies(
            active_pacing_profile=lambda *_args, **_kwargs: {"pace": "normal"},
            milestone_state_for_turn=lambda *_args, **_kwargs: {"last": 2, "next": 5},
            compute_turn_budget_estimates=lambda *_args, **_kwargs: calls.append("budget"),
            build_pacing_instruction_block=lambda *_args, **_kwargs: "Pacing",
            update_turn_timing_ema=lambda *_args, **_kwargs: calls.append("timing"),
        )

        self.assertEqual(deps.active_pacing_profile()["pace"], "normal")
        self.assertEqual(deps.milestone_state_for_turn()["next"], 5)
        deps.compute_turn_budget_estimates({})
        self.assertEqual(deps.build_pacing_instruction_block({}), "Pacing")
        deps.update_turn_timing_ema({}, 1.0, 2.0)
        self.assertEqual(calls, ["budget", "timing"])

    def test_turn_attribute_dependencies_group_only_attribute_meta_ports(self) -> None:
        deps = TurnAttributeDependencies(
            normalize_attribute_influence_meta=lambda meta: {**meta, "normalized": True},
        )

        self.assertTrue(deps.normalize_attribute_influence_meta({"last_turn": 1})["normalized"])


if __name__ == "__main__":
    unittest.main()
