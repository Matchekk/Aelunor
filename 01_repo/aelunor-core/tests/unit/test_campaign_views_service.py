import unittest

from app.services import state_engine
from app.services.campaigns import views


class CampaignViewsServiceTests(unittest.TestCase):
    def test_slot_and_player_projection_helpers_live_in_campaign_views(self) -> None:
        campaign = {
            "campaign_meta": {"host_player_id": "player_host"},
            "claims": {"slot_1": "player_1"},
            "players": {"player_1": {"display_name": "Aria"}},
            "setup": {
                "world": {"summary": {"player_count": "1"}},
                "characters": {"slot_1": {"completed": True}},
            },
            "state": {"characters": {"slot_1": {"bio": {"name": "Aria"}}}},
        }

        self.assertEqual(views.campaign_slots(campaign), ["slot_1"])
        self.assertEqual(views.player_claim(campaign, "player_1"), "slot_1")
        self.assertEqual(views.display_name_for_slot(campaign, "slot_1"), "Aria")
        self.assertEqual(views.setup_slot_statuses(campaign)[0]["status"], "ready")

    def test_state_engine_keeps_build_campaign_view_public_facade(self) -> None:
        self.assertEqual(state_engine.EXPORTED_SYMBOLS, ["public_turn", "build_campaign_view"])
        self.assertNotIn("save_campaign", state_engine.runtime_symbols())
        self.assertIsNotNone(state_engine.build_campaign_view)


if __name__ == "__main__":
    unittest.main()
