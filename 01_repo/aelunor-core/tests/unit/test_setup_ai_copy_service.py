import unittest
from typing import Any, Dict

from app.services import state_engine
from app.services.setup import ai_copy


class SetupAiCopyServiceTests(unittest.TestCase):
    def test_clean_and_bad_copy_detection_match_state_engine_wrapper(self) -> None:
        self.assertEqual(ai_copy.clean_setup_ai_copy('"Hallo"'), "Hallo")
        self.assertTrue(ai_copy.is_bad_setup_ai_copy("Frage-ID: theme"))
        self.assertIs(state_engine.clean_setup_ai_copy, state_engine.clean_setup_ai_copy)
        self.assertEqual(state_engine.clean_setup_ai_copy("'Hallo'"), "Hallo")

    def test_ensure_question_ai_copy_uses_existing_runtime_copy_without_llm(self) -> None:
        calls = []

        def call_ollama_text(_system: str, _user: str) -> str:
            calls.append("llm")
            return "Nicht genutzt"

        deps = ai_copy.SetupAiCopyDependencies(
            call_ollama_text=call_ollama_text,
            display_name_for_slot=lambda _campaign, slot_name: str(slot_name),
            looks_non_german_text=lambda *_args, **_kwargs: False,
            utc_now=lambda: "2026-01-01T00:00:00Z",
        )
        campaign: Dict[str, Any] = {
            "setup": {
                "world": {
                    "question_runtime": {
                        "theme": {"ai_copy": "Bestehender Text"},
                    }
                }
            }
        }

        result = ai_copy.ensure_question_ai_copy(campaign, setup_type="world", question_id="theme", deps=deps)

        self.assertEqual(result, "Bestehender Text")
        self.assertEqual(calls, [])
        self.assertEqual(len(state_engine.runtime_symbols()), 42)


if __name__ == "__main__":
    unittest.main()
