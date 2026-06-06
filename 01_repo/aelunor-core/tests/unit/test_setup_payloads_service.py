import unittest
from typing import Any, Dict, Optional

from app.services import state_engine
from app.services.setup import payloads


class SetupPayloadsServiceTests(unittest.TestCase):
    def deps(self) -> payloads.SetupPayloadDependencies:
        return payloads.SetupPayloadDependencies(
            deep_copy=lambda value: __import__("copy").deepcopy(value),
            display_name_for_slot=lambda _campaign, slot_name: f"Slot {slot_name}",
            extract_text_answer=lambda value: str((value or {}).get("value") or value or ""),
            is_host=lambda _campaign, player_id: player_id == "host_1",
            current_question_id=lambda setup_node: setup_node.get("question_order", ["theme"])[0],
            progress_payload=lambda setup_node: {"answered": len(setup_node.get("answers") or {})},
            normalize_campaign_length_choice=lambda value: str(value or "medium").lower(),
            normalize_ruleset_choice=lambda value: str(value or "Konsequent"),
        )

    def test_build_question_payload_preserves_core_shape(self) -> None:
        campaign: Dict[str, Any] = {"setup": {"world": {"answers": {"tone": {"value": "Brutal"}}}, "characters": {}}}
        question = {"id": "theme", "label": "Theme", "type": "select", "options": ["Sandbox (freie Erkundung)"], "allow_other": True}

        result = payloads.build_question_payload(
            question,
            campaign=campaign,
            setup_type="world",
            ai_copy="  Eigener Text  ",
            deps=self.deps(),
        )

        self.assertEqual(result["question_id"], "theme")
        self.assertEqual(result["ai_copy"], "Eigener Text")
        self.assertEqual(result["option_entries"][0]["value"], "Sandbox (freie Erkundung)")
        self.assertIn("entdeckung", result["option_entries"][0]["description"].lower())

    def test_world_question_state_returns_none_for_non_host(self) -> None:
        campaign: Dict[str, Any] = {"setup": {"world": {"question_order": ["theme"], "answers": {}}, "characters": {}}}

        self.assertIsNone(payloads.build_world_question_state(campaign, "player_1", deps=self.deps()))
        self.assertEqual(state_engine.EXPORTED_SYMBOLS, ["public_turn", "build_campaign_view"])


if __name__ == "__main__":
    unittest.main()
