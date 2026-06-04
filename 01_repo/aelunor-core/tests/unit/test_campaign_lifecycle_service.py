import unittest

from fastapi import HTTPException

from app.core.ids import hash_secret
from app.services.campaigns import lifecycle


class CampaignLifecycleServiceTests(unittest.TestCase):
    def test_authenticate_player_updates_last_seen_and_rejects_bad_token(self) -> None:
        campaign = {
            "players": {
                "player_1": {
                    "player_token_hash": hash_secret("token"),
                    "last_seen_at": "old",
                }
            }
        }

        player = lifecycle.authenticate_player(campaign, "player_1", "token")

        self.assertIs(player, campaign["players"]["player_1"])
        self.assertNotEqual(campaign["players"]["player_1"]["last_seen_at"], "old")
        with self.assertRaises(HTTPException) as ctx:
            lifecycle.authenticate_player(campaign, "player_1", "bad")
        self.assertEqual(ctx.exception.status_code, 401)

    def test_start_guard_requires_completed_world_claims_and_characters(self) -> None:
        campaign = {
            "setup": {
                "world": {"completed": True, "summary": {"player_count": "1"}},
                "characters": {"slot_1": {"completed": True}},
            },
            "claims": {"slot_1": "player_1"},
            "state": {"characters": {"slot_1": {}}},
        }

        self.assertTrue(lifecycle.can_start_adventure(campaign))
        campaign["claims"]["slot_1"] = None
        self.assertFalse(lifecycle.can_start_adventure(campaign))

    def test_require_host_and_claim_keep_http_error_contracts(self) -> None:
        campaign = {
            "campaign_meta": {"host_player_id": "host"},
            "claims": {"slot_1": "player_1"},
        }

        lifecycle.require_host(campaign, "host")
        lifecycle.require_claim(campaign, "player_1", "slot_1")
        with self.assertRaises(HTTPException) as host_ctx:
            lifecycle.require_host(campaign, "player_1")
        self.assertEqual(host_ctx.exception.status_code, 403)
        with self.assertRaises(HTTPException) as claim_ctx:
            lifecycle.require_claim(campaign, "player_2", "slot_1")
        self.assertEqual(claim_ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
