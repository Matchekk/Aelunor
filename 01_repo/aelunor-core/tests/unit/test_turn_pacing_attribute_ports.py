import ast
import unittest
from pathlib import Path


TURN_ENGINE_PATH = Path(__file__).resolve().parents[2] / "app" / "services" / "turn_engine.py"


class TurnPacingAttributePortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = TURN_ENGINE_PATH.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_configure_builds_targeted_pacing_and_attribute_dependencies(self) -> None:
        self.assertIn("_build_runtime_turn_pacing_dependencies(main_globals)", self.source)
        self.assertIn('_build_source_turn_pacing_dependencies(main_globals.get("state_engine"))', self.source)
        self.assertIn("configure_turn_pacing_dependencies(pacing_deps)", self.source)
        self.assertIn("_build_runtime_turn_attribute_dependencies(main_globals)", self.source)
        self.assertIn('_build_source_turn_attribute_dependencies(main_globals.get("state_engine"))', self.source)
        self.assertIn("configure_turn_attribute_dependencies(attribute_deps)", self.source)

    def test_configure_does_not_overwrite_local_pacing_or_attribute_wrappers(self) -> None:
        self.assertIn("_TURN_PACING_PORT_NAMES", self.source)
        self.assertIn("_TURN_ATTRIBUTE_PORT_NAMES", self.source)
        self.assertIn("if key not in _TURN_PORT_NAMES", self.source)

    def test_turn_engine_exposes_patchable_pacing_and_attribute_wrappers(self) -> None:
        function_names = {
            node.name
            for node in self.tree.body
            if isinstance(node, ast.FunctionDef)
        }

        for name in (
            "active_pacing_profile",
            "milestone_state_for_turn",
            "compute_turn_budget_estimates",
            "build_pacing_instruction_block",
            "update_turn_timing_ema",
            "normalize_attribute_influence_meta",
        ):
            self.assertIn(name, function_names)

    def test_default_attribute_influence_meta_is_not_pulled_into_turn_ports(self) -> None:
        self.assertNotIn("default_attribute_influence_meta", self.source)


if __name__ == "__main__":
    unittest.main()
