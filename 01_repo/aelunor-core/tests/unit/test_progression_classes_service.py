import ast
import unittest
from pathlib import Path

from app.services import state_engine
from app.services.progression import classes


CORE_ROOT = Path(__file__).resolve().parents[2]
CLASSES_PATH = CORE_ROOT / "app" / "services" / "progression" / "classes.py"


class ProgressionClassesServiceTests(unittest.TestCase):
    def test_class_progression_helpers_live_in_target_module(self) -> None:
        tree = ast.parse(CLASSES_PATH.read_text(encoding="utf-8"))
        function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

        for name in ("apply_class_xp", "ensure_class_rank_core_skills", "migrate_legacy_role_to_class"):
            self.assertIn(name, function_names)

    def test_apply_class_xp_levels_and_unlocks_ascension(self) -> None:
        character = {
            "class_current": {
                "id": "class_spark",
                "name": "Spark",
                "rank": "F",
                "level": 1,
                "level_max": 2,
                "xp": 90,
                "xp_next": 100,
                "ascension": {"status": "none"},
            },
        }

        messages = classes.apply_class_xp(character, 20)

        self.assertEqual(messages, ["Klassenaufstieg bereit: Spark.", "Klassenfortschritt: Spark erreicht Lv 2/2."])
        self.assertEqual(character["class_current"]["level"], 2)
        self.assertEqual(character["class_current"]["ascension"]["status"], "available")

    def test_ensure_class_rank_core_skills_wires_element_path_ports(self) -> None:
        character = {
            "slot_id": "slot_1",
            "bio": {"name": "Matchek"},
            "class_current": {
                "id": "class_flame_guard",
                "name": "Flame Guard",
                "rank": "f",
                "element_id": "elem_fire",
            },
            "skills": {},
        }
        world = {
            "elements": {"elem_fire": {"name": "Fire"}},
            "element_class_paths": {
                "elem_fire": [
                    {
                        "id": "path_flame",
                        "name": "Flame Path",
                        "ranks": {
                            "F": {
                                "core_skills_required": ["Spark Guard"],
                                "core_skills_unlockable": ["Ember Step"],
                                "signature_skills": [],
                            }
                        },
                    }
                ]
            },
        }

        messages = classes.ensure_class_rank_core_skills(character, world, {}, unlock_extra=False)

        self.assertEqual(messages, ["Matchek schaltet den Klassenkern-Skill Spark Guard frei."])
        self.assertIn("skill_spark_guard", character["skills"])
        self.assertEqual(character["class_current"]["path_id"], "path_flame")
        self.assertEqual(character["class_current"]["path_rank"], "F")
        self.assertEqual(character["class_current"]["element_id"], "elem_fire")
        self.assertEqual(len(state_engine.runtime_symbols()), 42)


if __name__ == "__main__":
    unittest.main()
