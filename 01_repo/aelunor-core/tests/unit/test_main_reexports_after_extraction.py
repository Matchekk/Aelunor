import re
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from app import main
from app.adapters import ollama_config
from app.catalogs import runtime_catalogs
from app.config import feature_flags
from app.core import ids, paths
from app.services import state_engine
from app.services import turn_engine


class MainReexportsAfterExtractionTests(unittest.TestCase):
    def test_main_reexports_core_helpers(self) -> None:
        for name in ("SLOT_PREFIX", "utc_now", "deep_copy", "hash_secret", "make_id"):
            self.assertIs(getattr(main, name), getattr(ids, name), name)

    def test_core_helper_behavior_is_unchanged(self) -> None:
        self.assertEqual(main.SLOT_PREFIX, "slot_")
        self.assertEqual(
            main.hash_secret("secret"),
            "2bb80d537b1da3e38bd30361aa855686bde0eacd7162fef6a25fe97bf527a25b",
        )
        original = {"nested": {"value": 1}}
        copied = main.deep_copy(original)
        copied["nested"]["value"] = 2
        self.assertEqual(original, {"nested": {"value": 1}})
        self.assertRegex(main.make_id("trace"), re.compile(r"^trace_[0-9a-f]{10}$"))
        parsed = datetime.fromisoformat(main.utc_now())
        self.assertIsNotNone(parsed.tzinfo)

    def test_main_reexports_path_wiring(self) -> None:
        for name in (
            "RUNTIME_CONFIG",
            "BASE_DIR",
            "STATIC_DIR",
            "UI_V1_DIST_DIR",
            "UI_V1_ASSETS_DIR",
            "DATA_DIR",
            "LEGACY_STATE_PATH",
            "CAMPAIGNS_DIR",
        ):
            self.assertIs(getattr(main, name), getattr(paths, name), name)
        self.assertTrue(callable(main.ensure_data_dirs))
        self.assertTrue(main.LEGACY_STATE_PATH.endswith("state.json"))

    def test_main_ensure_data_dirs_still_uses_patchable_main_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aelunor-paths-") as temp_dir:
            campaigns_dir = str(Path(temp_dir) / "campaigns")
            with (
                patch.object(main, "DATA_DIR", temp_dir),
                patch.object(main, "CAMPAIGNS_DIR", campaigns_dir),
            ):
                main.ensure_data_dirs()
            self.assertTrue(Path(campaigns_dir).is_dir())

    def test_feature_flag_defaults_and_reexports_are_stable(self) -> None:
        for name in (
            "ENABLE_HEURISTIC_NORMALIZE_BACKFILL",
            "ENABLE_LEGACY_SHADOW_WRITEBACK",
        ):
            self.assertIs(getattr(main, name), getattr(feature_flags, name), name)

        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(feature_flags.env_flag_enabled("ENABLE_HEURISTIC_NORMALIZE_BACKFILL"))
            self.assertFalse(feature_flags.env_flag_enabled("ENABLE_LEGACY_SHADOW_WRITEBACK"))
        with patch.dict("os.environ", {"FLAG": "yes"}, clear=True):
            self.assertTrue(feature_flags.env_flag_enabled("FLAG"))
        with patch.dict("os.environ", {"FLAG": "off"}, clear=True):
            self.assertFalse(feature_flags.env_flag_enabled("FLAG"))

    def test_main_reexports_ollama_config(self) -> None:
        for name in (
            "OLLAMA_URL",
            "OLLAMA_MODEL",
            "_OLLAMA_SEED_RAW",
            "OLLAMA_SEED",
            "OLLAMA_TEMPERATURE",
            "OLLAMA_NUM_CTX",
            "OLLAMA_REPEAT_PENALTY",
            "OLLAMA_REPEAT_LAST_N",
            "OLLAMA_TIMEOUT_SEC",
            "OLLAMA_ADAPTER",
        ):
            self.assertIs(getattr(main, name), getattr(ollama_config, name), name)

        settings = main.OLLAMA_ADAPTER.settings
        self.assertEqual(ollama_config.DEFAULT_OLLAMA_MODEL, "gemma4:e4b")
        self.assertEqual(settings.url, main.OLLAMA_URL)
        self.assertEqual(settings.model, main.OLLAMA_MODEL)
        self.assertEqual(settings.timeout_sec, main.OLLAMA_TIMEOUT_SEC)
        self.assertEqual(settings.seed, main.OLLAMA_SEED)

    def test_main_reexports_catalog_and_schema_wiring(self) -> None:
        for name in (
            "PROMPTS",
            "SETUP_CATALOG",
            "SYSTEM_PROMPT",
            "RESPONSE_SCHEMA",
            "INITIAL_STATE",
            "CATALOG_VERSION",
            "WORLD_FORM_CATALOG",
            "CHARACTER_FORM_CATALOG",
            "WORLD_QUESTION_MAP",
            "CHARACTER_QUESTION_MAP",
            "CANON_EXTRACTOR_SCHEMA",
            "PROGRESSION_EXTRACTOR_SCHEMA",
        ):
            self.assertIs(getattr(main, name), getattr(runtime_catalogs, name), name)

        self.assertEqual(main.SYSTEM_PROMPT, main.PROMPTS["system_prompt"])
        self.assertIs(main.INITIAL_STATE, main.PROMPTS["initial_state"])
        self.assertEqual(main.CATALOG_VERSION, main.SETUP_CATALOG["version"])
        self.assertEqual(main.WORLD_FORM_CATALOG, main.SETUP_CATALOG["world_form_catalog"])
        self.assertEqual(main.CHARACTER_FORM_CATALOG, main.SETUP_CATALOG["character_form_catalog"])
        self.assertIs(main.WORLD_QUESTION_MAP[main.WORLD_FORM_CATALOG[0]["id"]], main.WORLD_FORM_CATALOG[0])
        self.assertIs(main.CHARACTER_QUESTION_MAP[main.CHARACTER_FORM_CATALOG[0]["id"]], main.CHARACTER_FORM_CATALOG[0])

    def test_configured_engines_still_see_extracted_runtime_globals(self) -> None:
        for name in (
            "SLOT_PREFIX",
            "deep_copy",
            "make_id",
            "utc_now",
            "DATA_DIR",
            "CAMPAIGNS_DIR",
            "LEGACY_STATE_PATH",
            "INITIAL_STATE",
            "RESPONSE_SCHEMA",
            "PROGRESSION_EXTRACTOR_SCHEMA",
            "ENABLE_HEURISTIC_NORMALIZE_BACKFILL",
            "ENABLE_LEGACY_SHADOW_WRITEBACK",
            "OLLAMA_ADAPTER",
            "OLLAMA_TEMPERATURE",
        ):
            self.assertIs(getattr(state_engine, name), getattr(main, name), name)

        for name in (
            "deep_copy",
            "make_id",
            "utc_now",
            "SYSTEM_PROMPT",
            "RESPONSE_SCHEMA",
            "CANON_EXTRACTOR_SCHEMA",
            "ENABLE_LEGACY_SHADOW_WRITEBACK",
            "OLLAMA_ADAPTER",
            "OLLAMA_TEMPERATURE",
        ):
            self.assertIs(getattr(turn_engine, name), getattr(main, name), name)

    def test_dependency_factory_wrappers_keep_expected_bindings(self) -> None:
        runtime = main.state_engine_runtime()

        setup_deps = main.setup_service_dependencies()
        self.assertNotIn("load_campaign", runtime)
        self.assertTrue(callable(setup_deps.load_campaign))
        self.assertIs(setup_deps.clear_live_activity, main.live_state_service.clear_live_activity)
        self.assertIs(setup_deps.world_question_map, main.WORLD_QUESTION_MAP)

        turn_deps = main.turn_service_dependencies()
        self.assertIs(turn_deps.create_turn_record, main.create_turn_record)
        self.assertIs(turn_deps.turn_flow_error_cls, main.TurnFlowError)
        self.assertIs(turn_deps.utc_now, main.utc_now)

        campaign_deps = main.campaign_service_dependencies()
        self.assertIs(campaign_deps.hash_secret, main.hash_secret)
        self.assertIs(campaign_deps.clear_live_campaign_state, main.live_state_service.clear_campaign_state)

        boards_deps = main.boards_service_dependencies()
        self.assertNotIn("default_player_diary_entry", runtime)
        self.assertTrue(callable(boards_deps.default_player_diary_entry))
        self.assertIs(boards_deps.make_id, main.make_id)


if __name__ == "__main__":
    unittest.main()
