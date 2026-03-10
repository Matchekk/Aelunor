import unittest
from typing import Any, Dict, Optional

from app.services import campaign_service


def make_campaign() -> Dict[str, Any]:
    return {
        "campaign_meta": {"campaign_id": "cmp_1", "title": "Test", "status": "lobby"},
        "players": {},
        "state": {"meta": {"phase": "lobby", "turn": 0}, "characters": {"slot_aria": {}}, "items": {}},
        "turns": [],
    }


class CampaignServiceTests(unittest.TestCase):
    def build_deps(self, campaign: Dict[str, Any]) -> campaign_service.CampaignServiceDependencies:
        return campaign_service.CampaignServiceDependencies(
            ensure_campaign_storage=lambda: None,
            create_campaign_record=lambda title, display_name: {
                "campaign": campaign,
                "join_code": "JOIN1",
                "player_id": "player_1",
                "player_token": "token_1",
            },
            find_campaign_by_join_code=lambda _code: campaign,
            new_player=lambda display_name: {"player_id": "player_2", "player_token": "token_2", "display_name": display_name},
            utc_now=lambda: "2026-01-01T00:00:00Z",
            hash_secret=lambda value: f"hash:{value}",
            save_campaign=lambda *_args, **_kwargs: None,
            load_campaign=lambda _campaign_id: campaign,
            authenticate_player=lambda *_args, **_kwargs: None,
            require_host=lambda *_args, **_kwargs: None,
            deep_copy=lambda value: __import__("copy").deepcopy(value),
            intro_state=lambda _campaign: {"status": "idle"},
            active_turns=lambda _campaign: [],
            can_start_adventure=lambda _campaign: False,
            clear_live_activity=lambda *_args, **_kwargs: None,
            start_blocking_action=lambda *_args, **_kwargs: None,
            clear_blocking_action=lambda *_args, **_kwargs: None,
            try_generate_adventure_intro=lambda _campaign: None,
            apply_world_time_advance=lambda *_args, **_kwargs: None,
            rebuild_all_character_derived=lambda *_args, **_kwargs: None,
            append_character_change_events=lambda *_args, **_kwargs: None,
            normalize_class_current=lambda payload: payload,
            rebuild_character_derived=lambda *_args, **_kwargs: None,
            normalize_world_time=lambda *_args, **_kwargs: {},
            campaign_path=lambda _campaign_id: "",
            clear_live_campaign_state=lambda _campaign_id: None,
        )

    def test_create_campaign_happy_path(self) -> None:
        campaign = make_campaign()
        deps = self.build_deps(campaign)
        result = campaign_service.create_campaign(title="Neue", display_name="Mati", deps=deps)
        self.assertEqual(result["campaign"]["campaign_meta"]["campaign_id"], "cmp_1")
        self.assertEqual(result["join_code"], "JOIN1")

    def test_join_campaign_happy_path(self) -> None:
        campaign = make_campaign()
        deps = self.build_deps(campaign)
        result = campaign_service.join_campaign(join_code=" abcd ", display_name="Mati", deps=deps)
        self.assertEqual(result["join_code"], "ABCD")
        self.assertEqual(result["player_id"], "player_2")
        self.assertIn("player_2", campaign["players"])


if __name__ == "__main__":
    unittest.main()

