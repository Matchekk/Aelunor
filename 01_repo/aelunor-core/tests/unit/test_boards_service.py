import unittest
from typing import Any, Dict, Optional

from app.services import boards_service


def make_campaign() -> Dict[str, Any]:
    return {
        "players": {"player_1": {"display_name": "Mati"}},
        "boards": {
            "plot_essentials": {"premise": "", "updated_at": "", "updated_by": ""},
            "authors_note": {"content": "", "updated_at": "", "updated_by": ""},
            "player_diaries": {},
            "story_cards": [],
            "world_info": [],
        },
    }


class BoardsServiceTests(unittest.TestCase):
    def build_deps(self, campaign: Dict[str, Any]) -> boards_service.BoardsServiceDependencies:
        return boards_service.BoardsServiceDependencies(
            load_campaign=lambda _campaign_id: campaign,
            authenticate_player=lambda *_args, **_kwargs: None,
            require_host=lambda *_args, **_kwargs: None,
            save_campaign=lambda *_args, **_kwargs: None,
            utc_now=lambda: "2026-01-01T00:00:00Z",
            deep_copy=lambda value: __import__("copy").deepcopy(value),
            log_board_revision=lambda *_args, **_kwargs: None,
            default_player_diary_entry=lambda player_id, display_name: {
                "player_id": player_id,
                "display_name": display_name,
                "content": "",
                "updated_at": "",
                "updated_by": "",
            },
            make_id=lambda prefix: f"{prefix}_1",
        )

    def test_patch_plot_essentials(self) -> None:
        campaign = make_campaign()
        deps = self.build_deps(campaign)
        result = boards_service.patch_plot_essentials(
            campaign_id="cmp_1",
            payload={"premise": "Neue Prämisse"},
            player_id="player_1",
            player_token="token",
            deps=deps,
        )
        self.assertEqual(result["boards"]["plot_essentials"]["premise"], "Neue Prämisse")
        self.assertEqual(result["boards"]["plot_essentials"]["updated_by"], "player_1")

    def test_create_story_card(self) -> None:
        campaign = make_campaign()
        deps = self.build_deps(campaign)
        result = boards_service.create_story_card(
            campaign_id="cmp_1",
            title="Karte",
            kind="npc",
            content="Inhalt",
            tags=["x"],
            player_id="player_1",
            player_token="token",
            deps=deps,
        )
        self.assertEqual(len(result["boards"]["story_cards"]), 1)
        self.assertEqual(result["boards"]["story_cards"][0]["card_id"], "card_1")


if __name__ == "__main__":
    unittest.main()

