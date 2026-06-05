import ast
import unittest
from pathlib import Path


CORE_ROOT = Path(__file__).resolve().parents[2]
CANON_PATH = CORE_ROOT / "app" / "services" / "canon" / "extractor.py"
STATE_ENGINE_PATH = CORE_ROOT / "app" / "services" / "state_engine.py"


CANON_FUNCTIONS = {
    "build_extractor_context_packet",
    "call_canon_extractor",
    "normalize_extractor_output_patch",
}

EXTRACTION_IMPORTS = {
    "resolve_extractor_conflicts",
    "normalize_extraction_quarantine_meta",
    "append_extraction_quarantine",
    "safe_candidates_to_patch",
    "merge_safe_patch_additive",
}


def function_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}


class CanonExtractorServiceTests(unittest.TestCase):
    def test_canon_extractor_functions_live_in_target_module(self) -> None:
        names = function_names(CANON_PATH)

        self.assertTrue(CANON_FUNCTIONS <= names)

    def test_canon_extractor_does_not_import_state_engine(self) -> None:
        source = CANON_PATH.read_text(encoding="utf-8")

        self.assertNotIn("state_engine", source)
        self.assertIn("app.services.extraction.heuristics", source)
        self.assertIn("app.services.extraction.quarantine", source)
        self.assertIn("CANON_EXTRACTOR_SYSTEM_PROMPT", source)
        self.assertIn("CANON_EXTRACTOR_SCHEMA", source)

    def test_state_engine_keeps_thin_canon_wrappers(self) -> None:
        source = STATE_ENGINE_PATH.read_text(encoding="utf-8")

        for name in CANON_FUNCTIONS:
            self.assertIn(f"def {name}(*args: Any, **kwargs: Any):", source)
            self.assertIn(f"return _canon_extractor_service.{name}(*args, **kwargs)", source)

    def test_canon_uses_extraction_modules_for_heuristics(self) -> None:
        source = CANON_PATH.read_text(encoding="utf-8")

        for name in EXTRACTION_IMPORTS:
            self.assertIn(name, source)

        names = function_names(CANON_PATH)
        self.assertTrue(EXTRACTION_IMPORTS.isdisjoint(names))


if __name__ == "__main__":
    unittest.main()
