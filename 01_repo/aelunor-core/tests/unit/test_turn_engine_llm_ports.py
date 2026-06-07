import ast
import unittest
from pathlib import Path


TURN_ENGINE_PATH = Path(__file__).resolve().parents[2] / "app" / "services" / "turn_engine.py"


class TurnEngineLlmPortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = TURN_ENGINE_PATH.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_configure_does_not_overwrite_local_llm_ports_from_runtime_mapping(self) -> None:
        self.assertIn("_TURN_LLM_PORT_NAMES", self.source)
        self.assertIn("if key not in _TURN_PORT_NAMES", self.source)

    def test_turn_engine_exposes_explicit_llm_dependency_configuration(self) -> None:
        function_names = {
            node.name
            for node in self.tree.body
            if isinstance(node, ast.FunctionDef)
        }

        self.assertIn("configure_turn_llm_dependencies", function_names)
        self.assertIn("turn_llm_dependencies", function_names)
        self.assertIn("call_ollama_json", function_names)
        self.assertIn("call_ollama_schema", function_names)

    def test_default_turn_llm_dependencies_use_llm_client_factory(self) -> None:
        self.assertIn("build_turn_llm_dependencies", self.source)
        self.assertIn("build_default_llm_client_settings", self.source)

    def test_default_turn_llm_dependencies_use_selected_llm_adapter(self) -> None:
        default_function = next(
            node
            for node in self.tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "_default_turn_llm_dependencies"
        )
        default_source = ast.get_source_segment(self.source, default_function) or ""

        self.assertIn("LLM_ADAPTER", default_source)
        self.assertNotIn("adapter=OLLAMA_ADAPTER", default_source)


if __name__ == "__main__":
    unittest.main()
