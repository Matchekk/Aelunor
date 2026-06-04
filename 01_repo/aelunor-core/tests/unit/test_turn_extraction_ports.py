import ast
import unittest
from pathlib import Path


TURN_ENGINE_PATH = Path(__file__).resolve().parents[2] / "app" / "services" / "turn_engine.py"


class TurnExtractionPortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = TURN_ENGINE_PATH.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_configure_builds_targeted_extraction_dependencies_from_runtime_mapping(self) -> None:
        self.assertIn("_build_runtime_turn_extraction_dependencies(main_globals)", self.source)
        self.assertIn("configure_turn_extraction_dependencies(runtime_extraction_deps)", self.source)

    def test_configure_does_not_overwrite_local_extraction_wrappers(self) -> None:
        self.assertIn("_TURN_EXTRACTION_PORT_NAMES", self.source)
        self.assertIn("if key not in _TURN_PORT_NAMES", self.source)

    def test_turn_engine_exposes_patchable_extraction_wrappers(self) -> None:
        function_names = {
            node.name
            for node in self.tree.body
            if isinstance(node, ast.FunctionDef)
        }

        for name in (
            "build_extractor_context_packet",
            "call_canon_extractor",
            "call_npc_extractor",
            "apply_npc_upserts",
            "run_canon_gate",
            "normalize_npc_codex_state",
        ):
            self.assertIn(name, function_names)

    def test_progression_skill_codex_calls_remain_outside_extraction_port(self) -> None:
        extraction_group_start = self.source.index("_TURN_EXTRACTION_PORT_NAMES")
        extraction_group_end = self.source.index("_TURN_PROGRESSION_PORT_NAMES")
        extraction_group = self.source[extraction_group_start:extraction_group_end]

        self.assertNotIn("apply_progression_events", extraction_group)
        self.assertNotIn("apply_skill_events", extraction_group)
        self.assertNotIn("apply_codex_triggers", extraction_group)


if __name__ == "__main__":
    unittest.main()
