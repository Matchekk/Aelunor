import ast
import unittest
from pathlib import Path

from app.services.progression import application


CORE_ROOT = Path(__file__).resolve().parents[2]
STATE_ENGINE_PATH = CORE_ROOT / "app" / "services" / "state_engine.py"
APPLICATION_PATH = CORE_ROOT / "app" / "services" / "progression" / "application.py"


class ProgressionApplicationServiceTests(unittest.TestCase):
    def test_progression_application_lives_in_target_module(self) -> None:
        tree = ast.parse(APPLICATION_PATH.read_text(encoding="utf-8"))
        function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

        for name in ("apply_progression_events", "infer_progression_events_from_patch", "append_character_change_events"):
            self.assertIn(name, function_names)

    def test_state_engine_no_longer_defines_apply_progression_wrapper(self) -> None:
        tree = ast.parse(STATE_ENGINE_PATH.read_text(encoding="utf-8"))
        function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

        self.assertNotIn("apply_progression_events", function_names)

    def test_apply_progression_events_applies_explicit_training_event(self) -> None:
        state = {
            "meta": {"turn": 1},
            "world": {"settings": {}},
            "characters": {
                "slot_1": {
                    "bio": {"name": "Ada"},
                    "level": 1,
                    "xp_current": 0,
                    "xp_total": 0,
                    "xp_to_next": 120,
                    "progression": {},
                    "skills": {
                        "skill_spark": {"name": "Spark", "level": 1, "level_max": 2, "xp": 95, "next_xp": 100, "rank": "F"},
                    },
                },
            },
        }
        patch = {
            "characters": {
                "slot_1": {
                    "progression_events": [
                        {"type": "training_success", "target_skill_id": "skill_spark", "severity": "medium", "reason": "training"},
                    ],
                },
            },
        }

        result = application.apply_progression_events({}, state, state, patch, actor="slot_1", action_type="do")

        self.assertEqual(result["events"][0]["type"], "training_success")
        self.assertEqual(state["characters"]["slot_1"]["xp_total"], 19)
        self.assertEqual(state["characters"]["slot_1"]["skills"]["skill_spark"]["level"], 2)

    def test_append_character_change_events_uses_configured_appearance_ports(self) -> None:
        application.configure(
            blank_character_state=lambda slot: {"slot_id": slot},
            normalize_world_time=lambda _meta: {"absolute_day": 3},
            sync_appearance_changes=lambda *_args, **_kwargs: [{"message": "Narbe sichtbar."}],
        )
        state_after = {"meta": {}, "characters": {"slot_1": {}}}

        messages = application.append_character_change_events({}, state_after, turn_number=2)

        self.assertEqual(messages, ["Narbe sichtbar."])
        self.assertEqual(state_after["events"], ["Narbe sichtbar."])


if __name__ == "__main__":
    unittest.main()
