import unittest

from app import main
from app.services import state_engine
from app.services import turn_engine


class MainStateEngineConfigTests(unittest.TestCase):
    def test_skill_rank_order_available_after_main_import(self) -> None:
        # Regression guard: importing app.main must leave extracted state-engine
        # helpers fully configured with skill rank symbols.
        self.assertIsNotNone(main.app)
        self.assertGreaterEqual(state_engine.skill_rank_sort_value("A"), 0)

    def test_turn_engine_has_deep_copy_after_main_import(self) -> None:
        # Regression guard: setup/boot flows can touch turn helpers before
        # turn endpoints are called, so turn engine must be configured on import.
        deep_copy_fn = getattr(turn_engine, "deep_copy", None)
        self.assertTrue(callable(deep_copy_fn))
        self.assertEqual(deep_copy_fn({"ok": 1}), {"ok": 1})


if __name__ == "__main__":
    unittest.main()
