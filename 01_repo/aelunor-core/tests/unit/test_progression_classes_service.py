import ast
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
