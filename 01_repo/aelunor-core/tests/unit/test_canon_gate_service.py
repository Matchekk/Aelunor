import ast
import unittest
from pathlib import Path

from app.services.canon import gate as canon_gate


CORE_ROOT = Path(__file__).resolve().parents[2]
STATE_ENGINE_PATH = CORE_ROOT / "app" / "services" / "state_engine.py"
CANON_GATE_PATH = CORE_ROOT / "app" / "services" / "canon" / "gate.py"


class CanonGateServiceTests(unittest.TestCase):
    def test_run_canon_gate_lives_in_canon_gate_module(self) -> None:
        tree = ast.parse(CANON_GATE_PATH.read_text(encoding="utf-8"))
        function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

        self.assertIn("run_canon_gate", function_names)

    def test_state_engine_keeps_only_thin_run_canon_gate_wrapper(self) -> None:
        tree = ast.parse(STATE_ENGINE_PATH.read_text(encoding="utf-8"))
        run_gate = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "run_canon_gate"
        )

        self.assertEqual(len(run_gate.body), 1)
        self.assertIn(
            "_canon_gate_service.run_canon_gate",
            ast.unparse(run_gate),
        )

    def test_run_canon_gate_skips_when_no_progression_claims(self) -> None:
        campaign = {
            "state": {
                "characters": {
                    "slot_1": {"bio": {"name": "Ada"}},
                },
            },
        }
        state_after = campaign["state"]

        result = canon_gate.run_canon_gate(
            campaign,
            state_before=state_after,
            state_after=state_after,
            patch={"characters": {}},
            actor="slot_1",
            action_type="do",
            player_text="look around",
            story_text="Ada looks around the hall.",
        )

        self.assertEqual(result["meta"]["reason_code"], "NO_CLAIMS")
        self.assertEqual(result["meta"]["decision"], "skipped")


if __name__ == "__main__":
    unittest.main()
