import ast
import unittest
from pathlib import Path


CORE_ROOT = Path(__file__).resolve().parents[2]
NPC_PATH = CORE_ROOT / "app" / "services" / "canon" / "npc_extractor.py"
STATE_ENGINE_PATH = CORE_ROOT / "app" / "services" / "state_engine.py"


NPC_FUNCTIONS = {
    "build_npc_extractor_context_packet",
    "call_npc_extractor",
    "apply_npc_upserts",
    "resolve_npc_scene_hint",
    "best_matching_npc_id",
    "is_generic_npc_name",
}


def function_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}


class NpcExtractorServiceTests(unittest.TestCase):
    def test_npc_extractor_functions_live_in_target_module(self) -> None:
        names = function_names(NPC_PATH)

        self.assertTrue(NPC_FUNCTIONS <= names)

    def test_npc_extractor_does_not_import_state_engine(self) -> None:
        source = NPC_PATH.read_text(encoding="utf-8")

        self.assertNotIn("state_engine", source)
        self.assertIn("NPC_EXTRACTOR_SYSTEM_PROMPT", source)
        self.assertIn("NPC_EXTRACTOR_SCHEMA", source)

    def test_state_engine_keeps_thin_npc_wrappers(self) -> None:
        source = STATE_ENGINE_PATH.read_text(encoding="utf-8")

        for name in NPC_FUNCTIONS:
            self.assertIn(f"def {name}(*args: Any, **kwargs: Any):", source)
            self.assertIn(f"return _npc_extractor_service.{name}(*args, **kwargs)", source)


if __name__ == "__main__":
    unittest.main()
