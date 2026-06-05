import ast
import unittest
from pathlib import Path

from app.services.canon import patch_gate


CORE_ROOT = Path(__file__).resolve().parents[2]
PATCH_GATE_PATH = CORE_ROOT / "app" / "services" / "canon" / "patch_gate.py"


class CanonPatchGateServiceTests(unittest.TestCase):
    def test_patch_gate_helper_lives_in_target_module(self) -> None:
        tree = ast.parse(PATCH_GATE_PATH.read_text(encoding="utf-8"))
        function_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}

        self.assertIn("apply_canon_gate_patch", function_names)

    def test_apply_canon_gate_patch_uses_sanitize_validate_apply_ports(self) -> None:
        calls = []

        def sanitize(_state, patch):
            calls.append("sanitize")
            return patch

        def validate(_state, _patch):
            calls.append("validate")

        def apply(state, patch, *, attribute_cap):
            calls.append(("apply", attribute_cap))
            next_state = {"characters": {"slot_1": {"bio": {"name": "Ada"}}}}
            next_state["applied_patch"] = patch
            return next_state

        patch_gate.configure(
            sanitize_patch=sanitize,
            validate_patch=validate,
            apply_patch=apply,
            attribute_cap_for_campaign=lambda _campaign: 42,
            emit_turn_phase_event=lambda *_args, **_kwargs: calls.append("emit"),
        )

        next_state, merged_patch = patch_gate.apply_canon_gate_patch(
            {"state": {}},
            state_after={"characters": {"slot_1": {}}},
            merged_patch={"characters": {}},
            merged_with_gate={"characters": {"slot_1": {"progression_events": [{"type": "training_success"}]}}},
            actor="slot_1",
        )

        self.assertIn("sanitize", calls)
        self.assertIn("validate", calls)
        self.assertIn(("apply", 42), calls)
        self.assertIn("applied_patch", next_state)
        self.assertIn("slot_1", merged_patch["characters"])


if __name__ == "__main__":
    unittest.main()
