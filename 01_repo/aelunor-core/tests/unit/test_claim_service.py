import unittest
from typing import Any, Dict, Optional

from app.services import claim_service


def make_campaign() -> Dict[str, Any]:
    return {
        "setup": {
            "world": {"completed": True},
            "characters": {
                "slot_aria": {"question_order": ["q_name"], "answers": {}},
                "slot_borin": {"question_order": [], "answers": {}},
            },
        },
        "claims": {"slot_aria": None, "slot_borin": "player_2"},
        "players": {"player_1": {"display_name": "Player One"}, "player_2": {"display_name": "Player Two"}},
        "campaign_meta": {"host_player_id": "player_host"},
    }


class ClaimServiceTests(unittest.TestCase):
    def build_dependencies(self, campaign: Dict[str, Any], *, host_player_id: str = "player_host") -> tuple[claim_service.ClaimServiceDependencies, Dict[str, Any]]:
        calls: Dict[str, Any] = {
            "authenticated": 0,
            "saved": 0,
            "ensure_calls": [],
        }

        def load_campaign(_campaign_id: str) -> Dict[str, Any]:
            return campaign

        def authenticate_player(_campaign: Dict[str, Any], _player_id: Optional[str], _player_token: Optional[str], *, required: bool = False) -> None:
            if required and not _player_id:
                raise AssertionError("player id required for this test")
            calls["authenticated"] += 1

        def player_claim(_campaign: Dict[str, Any], player_id: Optional[str]) -> Optional[str]:
            for slot_name, owner in (_campaign.get("claims") or {}).items():
                if owner == player_id:
                    return slot_name
            return None

        def current_question_id(setup_node: Dict[str, Any]) -> str:
            order = setup_node.get("question_order") or []
            answers = setup_node.get("answers") or {}
            for qid in order:
                if qid not in answers:
                    return qid
            return ""

        def ensure_question_ai_copy(_campaign: Dict[str, Any], *, setup_type: str, question_id: str, slot_name: str) -> None:
            calls["ensure_calls"].append((setup_type, question_id, slot_name))

        def save_campaign(_campaign: Dict[str, Any], *args: Any, **kwargs: Any) -> None:
            calls["saved"] += 1

        def is_host(_campaign: Dict[str, Any], player_id: Optional[str]) -> bool:
            return bool(player_id) and player_id == host_player_id

        deps = claim_service.ClaimServiceDependencies(
            load_campaign=load_campaign,
            authenticate_player=authenticate_player,
            player_claim=player_claim,
            current_question_id=current_question_id,
            ensure_question_ai_copy=ensure_question_ai_copy,
            save_campaign=save_campaign,
            is_host=is_host,
        )
        return deps, calls

    def test_claim_success_path(self) -> None:
        campaign = make_campaign()
        deps, calls = self.build_dependencies(campaign)

        updated = claim_service.claim_slot(
            campaign_id="cmp_1",
            slot_name="slot_aria",
            player_id="player_1",
            player_token="token",
            deps=deps,
        )

        self.assertEqual(updated["claims"]["slot_aria"], "player_1")
        self.assertEqual(calls["authenticated"], 1)
        self.assertEqual(calls["saved"], 1)
        self.assertEqual(calls["ensure_calls"], [("character", "q_name", "slot_aria")])

    def test_takeover_success_path_releases_previous_claim(self) -> None:
        campaign = make_campaign()
        campaign["claims"]["slot_aria"] = "player_3"
        campaign["claims"]["slot_borin"] = "player_1"
        deps, calls = self.build_dependencies(campaign)

        updated = claim_service.takeover_slot(
            campaign_id="cmp_1",
            slot_name="slot_aria",
            player_id="player_1",
            player_token="token",
            deps=deps,
        )

        self.assertEqual(updated["claims"]["slot_borin"], None)
        self.assertEqual(updated["claims"]["slot_aria"], "player_1")
        self.assertEqual(calls["saved"], 1)
        self.assertEqual(calls["ensure_calls"], [("character", "q_name", "slot_aria")])

    def test_unclaim_success_path(self) -> None:
        campaign = make_campaign()
        campaign["claims"]["slot_aria"] = "player_1"
        deps, calls = self.build_dependencies(campaign)

        updated = claim_service.unclaim_slot(
            campaign_id="cmp_1",
            slot_name="slot_aria",
            player_id="player_1",
            player_token="token",
            deps=deps,
        )

        self.assertEqual(updated["claims"]["slot_aria"], None)
        self.assertEqual(calls["saved"], 1)


if __name__ == "__main__":
    unittest.main()
