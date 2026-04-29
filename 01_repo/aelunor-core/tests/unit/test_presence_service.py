import time
import unittest
from typing import Any, Dict, Optional

from fastapi import HTTPException

from app.services import presence_service


def make_campaign() -> Dict[str, Any]:
    return {
        "campaign_meta": {"campaign_id": "camp_presence", "host_player_id": "host_1"},
        "players": {
            "host_1": {"player_token_hash": "hash:host"},
            "player_1": {"player_token_hash": "hash:token_1"},
            "player_2": {"player_token_hash": "hash:token_2"},
        },
        "claims": {"slot_aria": "player_1", "slot_borin": "player_2"},
    }


class PresenceServiceTests(unittest.TestCase):
    def tearDown(self) -> None:
        presence_service.clear_stream_tickets()

    def build_deps(self, campaign: Dict[str, Any]) -> presence_service.PresenceServiceDependencies:
        def authenticate_player(
            _campaign: Dict[str, Any],
            player_id: Optional[str],
            token: Optional[str],
            *,
            required: bool = True,
        ) -> None:
            if required and (not player_id or not token):
                raise HTTPException(status_code=401, detail="missing auth")
            player = _campaign.get("players", {}).get(player_id or "")
            if not player or player.get("player_token_hash") != f"hash:{token}":
                raise HTTPException(status_code=401, detail="bad auth")

        return presence_service.PresenceServiceDependencies(
            load_campaign=lambda _campaign_id: campaign,
            authenticate_player=authenticate_player,
            set_live_activity=lambda _campaign, player_id, kind, **kwargs: {
                "player_id": player_id,
                "kind": kind,
                **kwargs,
            },
            clear_live_activity=lambda *_args, **_kwargs: None,
            live_snapshot=lambda _campaign_id: {"version": 1, "activities": {}, "blocking_action": None},
        )

    def test_issue_and_validate_stream_ticket(self) -> None:
        campaign = make_campaign()
        result = presence_service.issue_event_stream_ticket(
            campaign_id="camp_presence",
            player_id="player_1",
            player_token="token_1",
            deps=self.build_deps(campaign),
        )

        self.assertTrue(result["stream_token"])
        self.assertEqual(result["expires_in_sec"], presence_service.STREAM_TICKET_TTL_SEC)
        player_id = presence_service.authenticate_event_stream_ticket(
            campaign_id="camp_presence",
            stream_token=result["stream_token"],
            deps=self.build_deps(campaign),
        )
        self.assertEqual(player_id, "player_1")

    def test_stream_ticket_rejects_wrong_campaign_and_expiry(self) -> None:
        ticket = presence_service.create_stream_ticket(campaign_id="camp_presence", player_id="player_1")
        with self.assertRaises(HTTPException) as wrong_campaign:
            presence_service.validate_stream_ticket(campaign_id="other_campaign", stream_token=ticket["stream_token"])
        self.assertEqual(wrong_campaign.exception.status_code, 401)

        with presence_service._STREAM_TICKET_LOCK:
            presence_service._STREAM_TICKETS[ticket["stream_token"]]["expires_at_ts"] = time.time() - 1
        with self.assertRaises(HTTPException) as expired:
            presence_service.validate_stream_ticket(campaign_id="camp_presence", stream_token=ticket["stream_token"])
        self.assertEqual(expired.exception.status_code, 401)

    def test_presence_activity_allows_own_slot_and_rejects_foreign_slot(self) -> None:
        campaign = make_campaign()
        deps = self.build_deps(campaign)

        allowed = presence_service.set_presence_activity(
            campaign_id="camp_presence",
            kind="typing_turn",
            slot_id="slot_aria",
            target_turn_id=None,
            player_id="player_1",
            player_token="token_1",
            deps=deps,
        )
        self.assertEqual(allowed["activity"]["slot_id"], "slot_aria")

        with self.assertRaises(HTTPException) as foreign_slot:
            presence_service.set_presence_activity(
                campaign_id="camp_presence",
                kind="typing_turn",
                slot_id="slot_borin",
                target_turn_id=None,
                player_id="player_1",
                player_token="token_1",
                deps=deps,
            )
        self.assertEqual(foreign_slot.exception.status_code, 403)

    def test_presence_activity_allows_host_for_any_campaign_slot(self) -> None:
        campaign = make_campaign()
        result = presence_service.set_presence_activity(
            campaign_id="camp_presence",
            kind="reviewing_choices",
            slot_id="slot_borin",
            target_turn_id=None,
            player_id="host_1",
            player_token="host",
            deps=self.build_deps(campaign),
        )
        self.assertEqual(result["activity"]["slot_id"], "slot_borin")


if __name__ == "__main__":
    unittest.main()
