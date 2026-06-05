import ast
import unittest
from pathlib import Path

from app.services.extraction import quarantine


CORE_ROOT = Path(__file__).resolve().parents[2]
CANON_PATH = CORE_ROOT / "app" / "services" / "canon" / "extractor.py"
STATE_ENGINE_PATH = CORE_ROOT / "app" / "services" / "state_engine.py"


class ExtractionHeuristicsServiceTests(unittest.TestCase):
    def test_quarantine_metadata_normalization_matches_current_shape(self) -> None:
        meta = {
            "extraction_quarantine": {
                "max_entries": 2,
                "entries": [
                    {"status": "safe", "label": "ignored"},
                    {"status": "review", "turn": 3, "actor": "slot_1", "label": "Klingenfokus"},
                ],
            }
        }

        result = quarantine.normalize_extraction_quarantine_meta(meta)

        self.assertEqual(result["max_entries"], 2)
        self.assertEqual(len(result["entries"]), 1)
        self.assertEqual(result["entries"][0]["status"], "review")
        self.assertEqual(result["entries"][0]["label"], "Klingenfokus")

    def test_canon_extractor_imports_heuristics_without_state_engine(self) -> None:
        source = CANON_PATH.read_text(encoding="utf-8")

        self.assertIn("app.services.extraction.heuristics", source)
        self.assertIn("app.services.extraction.quarantine", source)
        self.assertNotIn("state_engine", source)

    def test_state_engine_reexports_auto_extraction_without_implementing_it(self) -> None:
        tree = ast.parse(STATE_ENGINE_PATH.read_text(encoding="utf-8"))
        function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

        self.assertNotIn("clean_auto_item_name", function_names)
        self.assertNotIn("extract_auto_learned_abilities", function_names)
        self.assertNotIn("extract_auto_story_injuries", function_names)


if __name__ == "__main__":
    unittest.main()
