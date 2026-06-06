import inspect
import unittest

from app.config.runtime import LEGACY_CHARACTERS
from app.services import state_engine
from app.services.campaigns import normalization
from app.services.state.dependencies import StateEngineDependencies


class CampaignNormalizationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        state_engine.configure_dependencies(StateEngineDependencies())

    def test_state_engine_normalize_campaign_is_thin_wrapper(self) -> None:
        source = inspect.getsource(state_engine.normalize_campaign)

        self.assertIn("campaign_normalization.normalize_campaign", source)
        self.assertNotIn('campaign.setdefault("state"', source)
        self.assertTrue(callable(normalization.normalize_campaign))

    def test_minimal_campaign_shape_is_preserved(self) -> None:
        campaign = {
            "campaign_meta": {"campaign_id": "camp_1", "host_player_id": "player_host"},
            "players": {"player_host": {"display_name": "Host"}},
        }

        normalized = state_engine.normalize_campaign(campaign)

        self.assertIs(normalized, campaign)
        self.assertIn("state", normalized)
        self.assertIn("setup", normalized)
        self.assertIn("boards", normalized)
        self.assertIn("claims", normalized)
        self.assertIn("turns", normalized)
        self.assertIn("world", normalized["state"])
        self.assertIn("characters", normalized["state"])
        self.assertIn("player_host", normalized["boards"]["player_diaries"])

    def test_legacy_characters_migrate_to_dynamic_slots(self) -> None:
        legacy_name = LEGACY_CHARACTERS[0]
        campaign = {
            "campaign_meta": {"campaign_id": "camp_legacy", "host_player_id": "player_host"},
            "players": {"player_host": {"display_name": "Host"}},
            "claims": {legacy_name: "player_host"},
            "setup": {
                "world": {"theme": "Alt", "completed": True},
                "characters": {},
            },
            "state": {
                "meta": {"phase": "adventure", "turn": 0},
                "world": {"settings": {"resource_name": "Aether"}},
                "characters": {legacy_name: {"bio": {"name": "Aria"}}},
            },
            "turns": [{"actor": legacy_name, "patch": {"characters": {legacy_name: {}}}}],
        }

        normalized = state_engine.normalize_campaign(campaign)
        first_slot = state_engine.slot_id(1)

        self.assertIn(first_slot, normalized["state"]["characters"])
        self.assertNotIn(legacy_name, normalized["state"]["characters"])
        self.assertEqual(normalized["claims"][first_slot], "player_host")
        self.assertEqual(normalized["turns"][0]["actor"], first_slot)
        self.assertEqual(normalized["legacy_migration"]["original_schema"], "fixed_3_slots_v1")

    def test_public_exports_and_runtime_bridge_remain_small(self) -> None:
        runtime = state_engine.runtime_symbols()

        self.assertEqual(state_engine.EXPORTED_SYMBOLS, ["public_turn", "build_campaign_view"])
        self.assertEqual(len(runtime), 42)
        for name in (
            "create_campaign_record",
            "load_campaign",
            "save_campaign",
            "campaign_path",
            "player_claim",
            "require_host",
            "require_claim",
        ):
            self.assertNotIn(name, runtime)


if __name__ == "__main__":
    unittest.main()
