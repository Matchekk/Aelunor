import ast
import unittest
from pathlib import Path

from app.services.progression import skills


CORE_ROOT = Path(__file__).resolve().parents[2]
STATE_ENGINE_PATH = CORE_ROOT / "app" / "services" / "state_engine.py"
SKILLS_PATH = CORE_ROOT / "app" / "services" / "progression" / "skills.py"


class ProgressionSkillsServiceTests(unittest.TestCase):
    def test_skill_xp_helpers_live_in_target_module(self) -> None:
        tree = ast.parse(SKILLS_PATH.read_text(encoding="utf-8"))
        function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

        for name in ("normalize_dynamic_skill_state", "merge_dynamic_skill", "grant_skill_xp", "apply_skill_events"):
            self.assertIn(name, function_names)

    def test_state_engine_keeps_thin_skill_wrapper_for_compatibility(self) -> None:
        tree = ast.parse(STATE_ENGINE_PATH.read_text(encoding="utf-8"))
        wrapper = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "normalize_dynamic_skill_state")

        self.assertEqual(len(wrapper.body), 1)
        self.assertIn("_progression_skills_service.normalize_dynamic_skill_state", ast.unparse(wrapper))

    def test_grant_skill_xp_levels_existing_skill(self) -> None:
        character = {
            "bio": {"name": "Ada"},
            "skills": {
                "skill_spark": {"name": "Spark", "level": 1, "level_max": 2, "xp": 95, "next_xp": 100, "rank": "F"},
            },
        }

        messages = skills.grant_skill_xp(character, "Spark", "normal", world_settings={})

        self.assertEqual(messages, ["Skill-Fortschritt: Spark erreicht Lv 2/2."])
        self.assertEqual(character["skills"]["skill_spark"]["level"], 2)
        self.assertEqual(character["skills"]["skill_spark"]["xp"], 11)


if __name__ == "__main__":
    unittest.main()
