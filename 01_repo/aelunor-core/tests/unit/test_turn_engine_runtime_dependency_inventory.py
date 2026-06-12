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
        self.assertIn("call_canon_extractor", dependency_names_for_group("extraction_explicit_ports"))
        self.assertIn("build_patch_summary", dependency_names_for_group("turn_materialization"))
        self.assertIn("run_canon_gate", dependency_names_for_group("extraction_explicit_ports"))
        self.assertIn("apply_progression_events", dependency_names_for_group("progression_explicit_ports"))
        self.assertIn("apply_skill_events", dependency_names_for_group("progression_explicit_ports"))
        self.assertIn("apply_codex_triggers", dependency_names_for_group("codex_explicit_ports"))
        self.assertIn("collect_codex_triggers", dependency_names_for_group("codex_explicit_ports"))
        self.assertIn("milestone_state_for_turn", dependency_names_for_group("pacing_timing_explicit_ports"))
        self.assertIn("update_turn_timing_ema", dependency_names_for_group("pacing_timing_explicit_ports"))
        self.assertIn("normalize_attribute_influence_meta", dependency_names_for_group("attribute_meta_explicit_ports"))
        self.assertIn("collect_turn_rag_context", dependency_names_for_group("rag_explicit_ports"))
        self.assertIn("build_turn_rag_prompt_block", dependency_names_for_group("rag_explicit_ports"))
        self.assertIn("clean_auto_item_name", dependency_names_for_group("domain_helpers"))

    def test_inventory_deduplicates_all_dependency_names(self) -> None:
        names = all_dependency_names()

        self.assertEqual(len(names), len(set(names)))
        self.assertIn("call_ollama_schema", names)
        self.assertIn("build_extractor_context_packet", names)

    def test_explicit_ports_are_not_runtime_required_dependencies(self) -> None:
        runtime_required = set(dependency_names_for_group("runtime_dependencies"))
        explicit_ports = set()
        for group in (
            "llm_explicit_ports",
            "extraction_explicit_ports",
            "progression_explicit_ports",
            "codex_explicit_ports",
            "pacing_timing_explicit_ports",
            "attribute_meta_explicit_ports",
            "rag_explicit_ports",
        ):
            explicit_ports.update(dependency_names_for_group(group))

        self.assertTrue(explicit_ports)
        self.assertTrue(explicit_ports.isdisjoint(runtime_required))

    def test_lorus_campaign_dependencies_are_marked_as_deferred(self) -> None:
        deferred = set(dependency_names_for_group("campaign_lorus_defer"))

        self.assertLess(deferred, set(all_dependency_names()))
        self.assertTrue({"active_turns", "campaign_slots", "remember_recent_story"} <= deferred)

    def test_no_empty_inventory_groups(self) -> None:
        for group, names in TURN_ENGINE_RUNTIME_DEPENDENCY_GROUPS.items():
            self.assertTrue(names, group)


if __name__ == "__main__":
    unittest.main()
