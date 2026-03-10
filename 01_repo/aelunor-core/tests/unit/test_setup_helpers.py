import unittest
from typing import Any, Dict, Optional

from app.helpers import setup_helpers


def extract_text_answer(value: Any) -> str:
    if isinstance(value, dict):
        if "value" in value and value["value"] is not None:
            return str(value["value"])
        selected = value.get("selected")
        if isinstance(selected, list):
            return ", ".join(str(entry) for entry in selected)
        if selected is not None:
            return str(selected)
        return str(value.get("other_text") or "")
    if value is None:
        return ""
    return str(value)


class SetupHelpersTests(unittest.TestCase):
    def build_deps(self) -> setup_helpers.SetupHelperDependencies:
        def current_question_id(setup_node: Dict[str, Any]) -> Optional[str]:
            for qid in setup_node.get("question_order") or []:
                if qid not in (setup_node.get("answers") or {}):
                    return qid
            return None

        return setup_helpers.SetupHelperDependencies(
            setup_random_system_prompt="prompt",
            setup_random_schema={"type": "object"},
            target_turns_defaults={"short": 120},
            pacing_profile_defaults={"short": {"beats_per_turn": 3}},
            max_players=4,
            call_ollama_schema=lambda *args, **kwargs: {"value": "Zufall"},
            extract_text_answer=extract_text_answer,
            normalized_eval_text=lambda value: str(value or "").strip().lower(),
            utc_now=lambda: "2026-01-01T00:00:00Z",
            deep_copy=lambda value: __import__("copy").deepcopy(value),
            current_question_id=current_question_id,
            normalize_answer_summary_defaults=lambda: {},
            normalize_resource_name=lambda value, default="Aether": str(value or default),
            normalize_campaign_length_choice=lambda value: str(value or "medium").strip().lower(),
            normalize_ruleset_choice=lambda value: str(value or "Konsequent"),
            parse_attribute_range=lambda _value: {"label": "1-10", "min": 1, "max": 10},
            parse_factions=lambda _value: [],
            parse_lines=lambda value: [line.strip() for line in str(value or "").splitlines() if line.strip()],
            parse_earth_items=lambda value: [part.strip() for part in str(value or "").split(",") if part.strip()],
            normalize_world_settings=lambda settings: dict(settings or {}),
            ensure_world_codex_from_setup=lambda _state, _summary: None,
            initialize_dynamic_slots=lambda campaign, _count: campaign.setdefault("claims", {}),
            apply_world_summary_to_boards=lambda campaign, _updated_by: campaign.setdefault("boards", {}).setdefault("plot_essentials", {}),
            apply_character_summary_to_state=lambda campaign, slot_name: campaign["state"]["characters"][slot_name].update({"synced": True}),
            maybe_start_adventure=lambda _campaign: {"turn_id": "turn_start_1"},
        )

    def test_validate_answer_payload_select_other(self) -> None:
        question = {
            "id": "q_select",
            "label": "Frage",
            "type": "select",
            "required": True,
            "allow_other": True,
            "options": ["A", "B"],
        }
        answer = {"selected": "", "other_text": "Eigen"}
        result = setup_helpers.validate_answer_payload(question, answer)
        self.assertEqual(result, {"selected": "Sonstiges", "other_text": "Eigen"})

    def test_build_world_summary_clamps_player_count(self) -> None:
        deps = self.build_deps()
        campaign = {
            "setup": {
                "world": {
                    "answers": {
                        "theme": "Dunkel",
                        "difficulty": "brutal",
                        "player_count": "99",
                        "campaign_length": "Kurz",
                        "resource_name": "Mana",
                    }
                }
            }
        }
        summary = setup_helpers.build_world_summary(campaign, deps=deps)
        self.assertEqual(summary["player_count"], 4)
        self.assertEqual(summary["consequence_severity"], "hoch")
        self.assertEqual(summary["resource_name"], "Mana")

    def test_build_and_apply_random_setup_preview(self) -> None:
        deps = self.build_deps()
        campaign = {
            "setup": {
                "world": {
                    "question_order": ["q1"],
                    "answers": {},
                    "raw_transcript": [],
                }
            }
        }
        setup_node = campaign["setup"]["world"]
        question_map = {"q1": {"id": "q1", "label": "Q1", "type": "text", "required": True}}

        preview = setup_helpers.build_random_setup_preview(
            campaign,
            setup_node,
            question_map,
            setup_type="world",
            player_id="host_1",
            mode="single",
            deps=deps,
        )
        self.assertEqual(len(preview), 1)
        self.assertEqual(preview[0]["question_id"], "q1")
        self.assertEqual(campaign["setup"]["world"]["answers"], {})

        applied = setup_helpers.apply_random_setup_preview(
            campaign,
            setup_node,
            question_map,
            [{"question_id": "q1", "value": "Antwort"}],
            player_id="host_1",
            deps=deps,
        )
        self.assertEqual(applied, 1)
        self.assertIn("q1", setup_node["answers"])

    def test_finalize_character_setup_marks_completed(self) -> None:
        deps = self.build_deps()
        campaign = {
            "state": {"meta": {"phase": "character_setup_open"}, "characters": {"slot_aria": {}}},
            "setup": {"characters": {"slot_aria": {"answers": {}, "completed": False}}},
        }
        turn = setup_helpers.finalize_character_setup(campaign, "slot_aria", deps=deps)
        self.assertEqual(campaign["setup"]["characters"]["slot_aria"]["completed"], True)
        self.assertEqual(campaign["state"]["meta"]["phase"], "character_setup_open")
        self.assertEqual(turn, {"turn_id": "turn_start_1"})


if __name__ == "__main__":
    unittest.main()

