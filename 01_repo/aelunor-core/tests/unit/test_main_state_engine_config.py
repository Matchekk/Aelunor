import tempfile
import unittest
import inspect
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
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

    def test_main_uses_explicit_state_engine_dependency_configuration(self) -> None:
        source = inspect.getsource(main)

        self.assertIn("state_engine.configure_dependencies(", source)
        self.assertIn("StateEngineDependencies(", source)
        self.assertNotIn("state_engine.configure(globals())", source)

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

    def test_root_redirects_to_v1_after_legacy_ui_removal(self) -> None:
        with TestClient(main.app, follow_redirects=False) as client:
            response = client.get("/")
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers.get("location"), "/v1")

    def test_legacy_state_endpoint_is_removed(self) -> None:
        with TestClient(main.app) as client:
            response = client.get("/api/state")
        self.assertEqual(response.status_code, 410)

    def test_campaign_repository_respects_patched_data_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aelunor-repo-path-") as temp_dir:
            campaigns_dir = str(Path(temp_dir) / "campaigns")
            with (
                patch.object(main, "DATA_DIR", temp_dir),
                patch.object(main, "CAMPAIGNS_DIR", campaigns_dir),
                patch.object(state_engine, "DATA_DIR", temp_dir),
                patch.object(state_engine, "CAMPAIGNS_DIR", campaigns_dir),
            ):
                runtime = state_engine.runtime_symbols()
                runtime["ensure_campaign_storage"]()
                created = runtime["create_campaign_record"]("Path Check", "Host")
                campaign_id = created["campaign"]["campaign_meta"]["campaign_id"]
                self.assertTrue((Path(campaigns_dir) / f"{campaign_id}.json").is_file())


if __name__ == "__main__":
    unittest.main()
