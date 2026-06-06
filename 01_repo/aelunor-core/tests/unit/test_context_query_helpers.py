import unittest

from app.services import state_engine
from app.services.context import (
    build_context_knowledge_index,
    build_context_result_payload,
    build_context_result_via_llm,
    context_result_to_answer_text,
    context_state_signature,
    parse_context_intent,
    resolve_context_target,
)


class ContextQueryHelperTests(unittest.TestCase):
    def test_state_engine_reexports_context_helpers_from_target_modules(self) -> None:
        self.assertIs(state_engine.parse_context_intent, parse_context_intent)
        self.assertIs(state_engine.build_context_knowledge_index, build_context_knowledge_index)
        self.assertIs(state_engine.build_context_result_payload, build_context_result_payload)
        self.assertIs(state_engine.context_result_to_answer_text, context_result_to_answer_text)

    def test_intent_index_and_answer_text_remain_stable_for_small_campaign(self) -> None:
        campaign = {
            "claims": {"slot_1": "player_1"},
            "setup": {"characters": {"slot_1": {"completed": True}}},
            "boards": {"world_info": []},
            "state": {
                "characters": {
                    "slot_1": {
                        "bio": {"name": "Aria"},
                        "class_current": {"id": "class_guardian", "name": "Guardian", "rank": "F"},
                        "skills": {},
                    }
                },
                "world": {"settings": {}},
            },
        }
        state = campaign["state"]

        intent = parse_context_intent("Wer ist Guardian?")
        self.assertEqual(intent, {"intent": "who", "target": "guardian"})
        index = build_context_knowledge_index(campaign, state)
        resolved = resolve_context_target(index, "Guardian")
        self.assertEqual(resolved["status"], "found")

        result = state_engine.deterministic_context_result_from_entry(
            intent=intent["intent"],
            target=intent["target"],
            entry=resolved["entry"],
            confidence=resolved["confidence"],
        )
        self.assertEqual(result["status"], "found")
        self.assertIn("Guardian", context_result_to_answer_text(result))

    def test_llm_context_answer_uses_injected_schema_port_without_state_engine_import(self) -> None:
        calls = []

        def fake_call_schema(*args, **kwargs):
            calls.append((args, kwargs))
            return {
                "status": "found",
                "intent": "summary",
                "target": "Aria",
                "confidence": "medium",
                "entity_type": "npc",
                "entity_id": "npc_aria",
                "title": "Aria",
                "explanation": "**Aria** ist bekannt.",
                "facts": ["Traegt ein Siegel"],
                "sources": [{"type": "npc", "id": "npc_aria", "label": "NPC-Codex: Aria"}],
                "suggestions": [],
            }

        result = build_context_result_via_llm(
            "Wer ist Aria?",
            "summary",
            "Aria",
            [{"type": "npc", "id": "npc_aria", "title": "Aria", "facts": ["Traegt ein Siegel"]}],
            call_schema=fake_call_schema,
        )
        self.assertEqual(result["status"], "found")
        self.assertEqual(result["explanation"], "Aria ist bekannt.")
        self.assertEqual(len(calls), 1)

    def test_runtime_symbols_and_public_exports_stay_small(self) -> None:
        self.assertEqual(state_engine.EXPORTED_SYMBOLS, ["public_turn", "build_campaign_view"])
        runtime = state_engine.runtime_symbols()
        self.assertLess(len(runtime), 25)
        # Context-query helpers now live in app.services.context and are wired
        # directly into the context-service factory, no longer via the bridge.
        self.assertNotIn("parse_context_intent", runtime)
        self.assertNotIn("build_context_knowledge_index", runtime)

    def test_context_signature_is_stable_for_equal_state(self) -> None:
        left = context_state_signature({"b": 2, "a": 1})
        right = context_state_signature({"a": 1, "b": 2})
        self.assertEqual(left, right)


if __name__ == "__main__":
    unittest.main()
