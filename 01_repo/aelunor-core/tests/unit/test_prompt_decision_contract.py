"""Contract-Tests: Standard-GM-Instruktionen duerfen keine Entscheidungsfragen erzwingen."""
import json
import os
import unittest

from app.prompts.system_prompts import TURN_MODE_GUIDE
from app.services.turn.prompt_payloads import build_turn_system_prompt
from app.services.world.world_settings import build_pacing_instruction_block

PROMPTS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "app", "prompts.json")

FORBIDDEN_INSTRUCTION_PATTERNS = [
    "Antworte mit 2-4 konkreten Optionen",
    "plus klarer Entscheidungspunkt",
    "maximal eine Abschlussfrage",
    "Entscheide dich zwischen",
]


def _system_prompt_base() -> str:
    with open(PROMPTS_PATH, encoding="utf-8") as handle:
        return json.load(handle)["system_prompt"]


def _full_turn_system_prompt() -> str:
    pacing = build_pacing_instruction_block({"meta": {"turn": 3}, "world": {"settings": {"campaign_length": "short"}}})
    return build_turn_system_prompt(
        system_prompt_base=_system_prompt_base(),
        turn_mode_guide=TURN_MODE_GUIDE,
        pacing_text=pacing["text"],
        attribute_prompt_hints="",
        combat_scaling_context={},
        min_story_chars=400,
        max_story_chars=2200,
    )


class PromptDecisionContractTests(unittest.TestCase):
    def test_no_forced_option_menus_in_standard_instructions(self):
        prompt = _full_turn_system_prompt()
        for pattern in FORBIDDEN_INSTRUCTION_PATTERNS:
            self.assertNotIn(pattern, prompt, pattern)

    def test_prompt_forbids_decision_questions(self):
        prompt = _full_turn_system_prompt()
        self.assertIn("Stelle keine Entscheidungsfragen", prompt)
        self.assertIn("Standard für requests ist none", prompt)
        self.assertIn("Beende story nie mit Entscheidungsfragen", prompt)

    def test_short_campaign_pacing_does_not_force_options(self):
        pacing = build_pacing_instruction_block({"meta": {"turn": 3}, "world": {"settings": {"campaign_length": "short"}}})
        self.assertNotIn("Optionen und zusätzlich", pacing["text"])
        self.assertIn("der Spieler entscheidet selbst", pacing["text"])

    def test_output_budget_block_present(self):
        prompt = _full_turn_system_prompt()
        self.assertIn("AUSGABE-BUDGET", prompt)
        self.assertIn("2–4 Absätzen", prompt)
        # explizite Ziel- und Obergrenze (kein nacktes Minimum mehr)
        self.assertIn("Ziel-Länge der story", prompt)
        self.assertIn("2200 Zeichen nicht", prompt)  # 400..2200 -> Cap-Direktive
        self.assertIn("DICHT statt lang", prompt)

    def test_output_budget_demands_complete_json_and_lean_patch(self):
        prompt = _full_turn_system_prompt()
        self.assertIn("vollständige, abgeschlossene Prosa ab, BEVOR das JSON", prompt)
        self.assertIn("niemals abgeschnittenen Text", prompt)
        self.assertIn("Halte den patch knapp", prompt)
        self.assertIn("keinen Endlos-Output", prompt)

    def test_pacing_block_uses_range_not_bare_minimum(self):
        pacing = build_pacing_instruction_block({"meta": {"turn": 3}, "world": {"settings": {}}})
        self.assertIn("überschreite max_story_chars nicht", pacing["text"])
        self.assertNotIn("muss mindestens min_story_chars Zeichen haben", pacing["text"])


if __name__ == "__main__":
    unittest.main()
