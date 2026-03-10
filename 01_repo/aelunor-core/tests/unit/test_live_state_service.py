import unittest
from typing import Any, Dict

from app.services import live_state_service


def make_campaign(campaign_id: str = "camp_live_1") -> Dict[str, Any]:
    return {
        "campaign_meta": {"campaign_id": campaign_id},
        "players": {"p1": {"display_name": "Mati"}},
    }


class LiveStateServiceTests(unittest.TestCase):
    def tearDown(self) -> None:
        live_state_service.clear_campaign_state("camp_live_1")

    def test_set_and_clear_activity(self) -> None:
        campaign = make_campaign()
        activity = live_state_service.set_live_activity(campaign, "p1", "typing_turn")
        self.assertEqual(activity["kind"], "typing_turn")

        snapshot = live_state_service.live_snapshot("camp_live_1")
        self.assertIn("p1", snapshot["activities"])

        live_state_service.clear_live_activity("camp_live_1", "p1")
        snapshot_after = live_state_service.live_snapshot("camp_live_1")
        self.assertNotIn("p1", snapshot_after["activities"])

    def test_blocking_action_lifecycle(self) -> None:
        campaign = make_campaign()
        live_state_service.start_blocking_action(campaign, player_id="p1", kind="submit_turn")
        snapshot = live_state_service.live_snapshot("camp_live_1")
        self.assertIsNotNone(snapshot["blocking_action"])
        self.assertEqual(snapshot["blocking_action"]["kind"], "submit_turn")

        live_state_service.clear_blocking_action("camp_live_1")
        cleared = live_state_service.live_snapshot("camp_live_1")
        self.assertIsNone(cleared["blocking_action"])


if __name__ == "__main__":
    unittest.main()
