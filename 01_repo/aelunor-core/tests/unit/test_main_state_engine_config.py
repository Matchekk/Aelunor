import unittest
from datetime import datetime

from app import main
from app.services import state_engine
from app.services import turn_engine
from app.services.world import codex


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

    def test_extracted_engines_are_configured_after_main_import(self) -> None:
        self.assertIsNotNone(main.app)
        self.assertTrue(getattr(state_engine, "_CONFIGURED", False))
        self.assertTrue(getattr(turn_engine, "_CONFIGURED", False))
        self.assertTrue(getattr(codex, "_CONFIGURED", False))

    def test_core_injected_helpers_are_callable_without_network(self) -> None:
        for module in (state_engine, turn_engine, codex):
            deep_copy_fn = getattr(module, "deep_copy", None)
            self.assertTrue(callable(deep_copy_fn), module.__name__)
            original = {"nested": {"value": 1}}
            copied = deep_copy_fn(original)
            copied["nested"]["value"] = 2
            self.assertEqual(original, {"nested": {"value": 1}})

        make_id_fn = getattr(state_engine, "make_id", None)
        utc_now_fn = getattr(state_engine, "utc_now", None)
        self.assertTrue(callable(make_id_fn))
        self.assertTrue(callable(utc_now_fn))
        self.assertTrue(make_id_fn("test").startswith("test_"))
        datetime.fromisoformat(utc_now_fn())

    def test_domain_callables_needed_by_codex_are_injected_after_main_import(self) -> None:
        for symbol in (
            "normalize_race_profile",
            "normalize_beast_profile",
            "normalize_element_profile",
            "normalize_dynamic_skill_state",
        ):
            self.assertTrue(callable(getattr(state_engine, symbol, None)), symbol)
            self.assertTrue(callable(getattr(codex, symbol, None)), symbol)

    def test_codex_runtime_dependencies_are_available_after_main_import(self) -> None:
        deps = codex._codex_deps()
        element_port = deps.element_normalization
        skill_port = deps.skill_normalization
        self.assertTrue(callable(deps.normalize_race_profile))
        self.assertTrue(callable(element_port.normalize_element_profile))
        self.assertTrue(callable(element_port.normalize_element_id_list))
        self.assertTrue(callable(element_port.normalize_skill_elements_for_world))
        self.assertTrue(callable(skill_port.normalize_resource_name))
        self.assertTrue(callable(skill_port.normalize_dynamic_skill_state))
        self.assertTrue(callable(skill_port.normalize_skill_store))
        self.assertTrue(callable(deps.npc_id_from_name))
        self.assertEqual(deps.codex_kind_race, "race")
        self.assertEqual(deps.codex_kind_beast, "beast")
        self.assertIn("identity", deps.race_codex_block_order)
        self.assertIn("identity", deps.beast_codex_block_order)
        self.assertIn(1, deps.race_blocks_by_level)
        self.assertIn(1, deps.beast_blocks_by_level)
        self.assertGreaterEqual(deps.codex_knowledge_level_max, deps.codex_knowledge_level_min)
        self.assertIn("Feuer", deps.element_core_names)
        self.assertIn("active", deps.npc_status_allowed)


if __name__ == "__main__":
    unittest.main()
