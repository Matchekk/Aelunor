import unittest

from app.services.turn.runtime_inventory import (
    TURN_ENGINE_RUNTIME_DEPENDENCY_GROUPS,
    all_dependency_names,
    dependency_names_for_group,
)


class TurnEngineRuntimeDependencyInventoryTests(unittest.TestCase):
    def test_inventory_groups_keep_runtime_bridge_targets_visible(self) -> None:
        self.assertIn("call_ollama_json", dependency_names_for_group("llm_explicit_ports"))
        self.assertIn("OLLAMA_TEMPERATURE", dependency_names_for_group("llm_runtime_config"))
        self.assertIn("call_canon_extractor", dependency_names_for_group("extraction"))
        self.assertIn("build_patch_summary", dependency_names_for_group("turn_materialization"))
        self.assertIn("run_canon_gate", dependency_names_for_group("canon_progression"))
        self.assertIn("clean_auto_item_name", dependency_names_for_group("domain_helpers"))

    def test_inventory_deduplicates_all_dependency_names(self) -> None:
        names = all_dependency_names()

        self.assertEqual(len(names), len(set(names)))
        self.assertIn("call_ollama_schema", names)
        self.assertIn("build_extractor_context_packet", names)

    def test_lorus_campaign_dependencies_are_marked_as_deferred(self) -> None:
        deferred = set(dependency_names_for_group("campaign_lorus_defer"))

        self.assertLess(deferred, set(all_dependency_names()))
        self.assertTrue({"active_turns", "campaign_slots", "remember_recent_story"} <= deferred)

    def test_no_empty_inventory_groups(self) -> None:
        for group, names in TURN_ENGINE_RUNTIME_DEPENDENCY_GROUPS.items():
            self.assertTrue(names, group)


if __name__ == "__main__":
    unittest.main()
