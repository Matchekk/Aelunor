import unittest

from app import main
from app.prompts import system_prompts
from app.services import state_engine
from app.services import turn_engine


class SystemPromptWiringTests(unittest.TestCase):
    def test_main_reexports_system_prompt_names_from_prompt_module(self) -> None:
        prompt_names = (
            "TURN_MODE_GUIDE",
            "CANON_EXTRACTOR_JSON_CONTRACT",
            "CANON_EXTRACTOR_SYSTEM_PROMPT",
            "PROGRESSION_EXTRACTOR_JSON_CONTRACT",
            "PROGRESSION_EXTRACTOR_SYSTEM_PROMPT",
            "NPC_EXTRACTOR_JSON_CONTRACT",
            "NPC_EXTRACTOR_SYSTEM_PROMPT",
            "MEMORY_SYSTEM_PROMPT",
            "SETUP_QUESTION_SYSTEM_PROMPT",
            "SETUP_RANDOM_SYSTEM_PROMPT",
            "CHARACTER_ATTRIBUTE_SYSTEM_PROMPT",
            "CONTEXT_ASSISTANT_SYSTEM_PROMPT",
            "TURN_RESPONSE_JSON_CONTRACT",
            "MANIFESTATION_SKILL_NAME_SYSTEM_PROMPT",
        )

        for name in prompt_names:
            self.assertIs(getattr(main, name), getattr(system_prompts, name), name)

    def test_configured_engines_keep_prompt_globals_available(self) -> None:
        for module, names in (
            (
                state_engine,
                (
                    "CANON_EXTRACTOR_JSON_CONTRACT",
                    "CANON_EXTRACTOR_SYSTEM_PROMPT",
                    "PROGRESSION_EXTRACTOR_JSON_CONTRACT",
                    "PROGRESSION_EXTRACTOR_SYSTEM_PROMPT",
                    "NPC_EXTRACTOR_JSON_CONTRACT",
                    "NPC_EXTRACTOR_SYSTEM_PROMPT",
                    "MEMORY_SYSTEM_PROMPT",
                    "SETUP_QUESTION_SYSTEM_PROMPT",
                    "SETUP_RANDOM_SYSTEM_PROMPT",
                    "CHARACTER_ATTRIBUTE_SYSTEM_PROMPT",
                    "CONTEXT_ASSISTANT_SYSTEM_PROMPT",
                    "TURN_RESPONSE_JSON_CONTRACT",
                    "MANIFESTATION_SKILL_NAME_SYSTEM_PROMPT",
                ),
            ),
            (
                turn_engine,
                (
                    "TURN_MODE_GUIDE",
                    "TURN_RESPONSE_JSON_CONTRACT",
                    "CANON_EXTRACTOR_SYSTEM_PROMPT",
                ),
            ),
        ):
            for name in names:
                self.assertIs(getattr(module, name), getattr(main, name), f"{module.__name__}.{name}")

    def test_prompt_content_smoke_matches_expected_contract_phrases(self) -> None:
        self.assertEqual(system_prompts.TURN_MODE_GUIDE["canon"], "CANON: Harte Wahrheit. Dieser Text wird verbindlich in den Zustand übernommen.")
        self.assertIn("Antworte mit genau einem JSON-Objekt ohne Markdown", system_prompts.TURN_RESPONSE_JSON_CONTRACT)
        self.assertIn("Du bist der Canon Extractor.", system_prompts.CANON_EXTRACTOR_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
