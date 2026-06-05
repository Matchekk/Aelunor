import ast
import unittest
from pathlib import Path


CORE_ROOT = Path(__file__).resolve().parents[2]
STATE_ENGINE_PATH = CORE_ROOT / "app" / "services" / "state_engine.py"
TURN_ENGINE_PATH = CORE_ROOT / "app" / "services" / "turn_engine.py"

TURN_PORT_NAMES = {
    "call_ollama_json",
    "call_ollama_schema",
    "build_extractor_context_packet",
    "call_canon_extractor",
    "call_npc_extractor",
    "apply_npc_upserts",
    "run_canon_gate",
    "normalize_npc_codex_state",
    "apply_progression_events",
    "apply_skill_events",
    "collect_codex_triggers",
    "apply_codex_triggers",
    "active_pacing_profile",
    "milestone_state_for_turn",
    "compute_turn_budget_estimates",
    "build_pacing_instruction_block",
    "update_turn_timing_ema",
    "normalize_attribute_influence_meta",
}


def module_assignment_literal(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"{name} assignment not found in {path}")


class RuntimeSymbolsBridgeTests(unittest.TestCase):
    def test_public_state_engine_exports_stay_small(self) -> None:
        exports = module_assignment_literal(STATE_ENGINE_PATH, "EXPORTED_SYMBOLS")

        self.assertEqual(exports, ["public_turn", "build_campaign_view"])

    def test_turn_port_names_are_removed_from_runtime_symbols(self) -> None:
        runtime_names = set(module_assignment_literal(STATE_ENGINE_PATH, "_STATE_ENGINE_RUNTIME_SYMBOLS"))

        self.assertTrue(TURN_PORT_NAMES.isdisjoint(runtime_names))

    def test_campaign_character_change_hook_stays_in_runtime_symbols(self) -> None:
        runtime_names = set(module_assignment_literal(STATE_ENGINE_PATH, "_STATE_ENGINE_RUNTIME_SYMBOLS"))

        self.assertIn("append_character_change_events", runtime_names)

    def test_turn_configure_has_targeted_state_engine_port_fallback(self) -> None:
        source = TURN_ENGINE_PATH.read_text(encoding="utf-8")

        self.assertIn('_build_target_turn_extraction_dependencies(main_globals.get("state_engine"))', source)
        self.assertIn('_build_source_turn_extraction_dependencies(main_globals.get("state_engine"))', source)
        self.assertIn('_build_source_turn_progression_dependencies(main_globals.get("state_engine"))', source)
        self.assertIn('_build_source_turn_codex_dependencies(main_globals.get("state_engine"))', source)
        self.assertIn('_build_source_turn_pacing_dependencies(main_globals.get("state_engine"))', source)
        self.assertIn('_build_source_turn_attribute_dependencies(main_globals.get("state_engine"))', source)


if __name__ == "__main__":
    unittest.main()
