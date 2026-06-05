import ast
import unittest
from pathlib import Path


TURN_ENGINE_PATH = Path(__file__).resolve().parents[2] / "app" / "services" / "turn_engine.py"


class TurnProgressionCodexPortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = TURN_ENGINE_PATH.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_configure_builds_targeted_progression_and_codex_dependencies(self) -> None:
        self.assertIn("_build_runtime_turn_progression_dependencies(main_globals)", self.source)
        self.assertIn('_build_source_turn_progression_dependencies(main_globals.get("state_engine"))', self.source)
        self.assertIn("configure_turn_progression_dependencies(progression_deps)", self.source)
        self.assertIn("_build_runtime_turn_codex_dependencies(main_globals)", self.source)
        self.assertIn('_build_source_turn_codex_dependencies(main_globals.get("state_engine"))', self.source)
        self.assertIn("configure_turn_codex_dependencies(codex_deps)", self.source)

    def test_configure_does_not_overwrite_local_progression_or_codex_wrappers(self) -> None:
        self.assertIn("_TURN_PROGRESSION_PORT_NAMES", self.source)
        self.assertIn("_TURN_CODEX_PORT_NAMES", self.source)
        self.assertIn("if key not in _TURN_PORT_NAMES", self.source)

    def test_turn_engine_exposes_patchable_progression_and_codex_wrappers(self) -> None:
        function_names = {
            node.name
            for node in self.tree.body
            if isinstance(node, ast.FunctionDef)
        }

        for name in (
            "append_character_change_events",
            "apply_progression_events",
            "apply_skill_events",
            "collect_codex_triggers",
            "apply_codex_triggers",
        ):
            self.assertIn(name, function_names)

    def test_pacing_timing_remains_outside_progression_codex_ports(self) -> None:
        progression_group_start = self.source.index("_TURN_PROGRESSION_PORT_NAMES")
        progression_group_end = self.source.index("_TURN_CODEX_PORT_NAMES")
        progression_group = self.source[progression_group_start:progression_group_end]
        codex_group_start = self.source.index("_TURN_CODEX_PORT_NAMES")
        codex_group_end = self.source.index("_TURN_PACING_PORT_NAMES")
        codex_group = self.source[codex_group_start:codex_group_end]

        for group in (progression_group, codex_group):
            self.assertNotIn("compute_turn_budget_estimates", group)
            self.assertNotIn("milestone_state_for_turn", group)
            self.assertNotIn("update_turn_timing_ema", group)


if __name__ == "__main__":
    unittest.main()
