import ast
import unittest
from pathlib import Path

from app.services.canon import progression_gate


CORE_ROOT = Path(__file__).resolve().parents[2]
STATE_ENGINE_PATH = CORE_ROOT / "app" / "services" / "state_engine.py"
PROGRESSION_GATE_PATH = CORE_ROOT / "app" / "services" / "canon" / "progression_gate.py"


class CanonProgressionGateServiceTests(unittest.TestCase):
    def test_progression_gate_helpers_live_in_target_module(self) -> None:
        tree = ast.parse(PROGRESSION_GATE_PATH.read_text(encoding="utf-8"))
        function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

        for name in (
            "detect_progression_claim_types",
            "progression_claim_coverage_for_actor_patch",
            "merge_progression_patch_additive",
            "call_progression_canon_extractor",
        ):
            self.assertIn(name, function_names)

    def test_state_engine_keeps_thin_progression_gate_wrappers(self) -> None:
        tree = ast.parse(STATE_ENGINE_PATH.read_text(encoding="utf-8"))
        wrappers = {
            node.name: ast.unparse(node)
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name in {
                "detect_progression_claim_types",
                "progression_claim_coverage_for_actor_patch",
                "merge_progression_patch_additive",
                "call_progression_canon_extractor",
            }
        }

        self.assertEqual(set(wrappers), {
            "detect_progression_claim_types",
            "progression_claim_coverage_for_actor_patch",
            "merge_progression_patch_additive",
            "call_progression_canon_extractor",
        })
        for source in wrappers.values():
            self.assertIn("_progression_gate_service.", source)

    def test_progression_claim_coverage_detects_existing_structured_patch(self) -> None:
        patch = {
            "characters": {
                "slot_1": {
                    "skills_set": {
                        "spark": {"name": "Spark", "level": 2, "xp": 0},
                    },
                    "class_update": {"level": 2},
                },
            },
        }

        coverage = progression_gate.progression_claim_coverage_for_actor_patch(patch, "slot_1")

        self.assertIn("skill_claim", coverage)
        self.assertIn("skill_level_claim", coverage)
        self.assertIn("class_claim", coverage)
        self.assertIn("class_level_claim", coverage)


if __name__ == "__main__":
    unittest.main()
