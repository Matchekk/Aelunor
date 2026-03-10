import copy
import unittest

from app.serializers import campaign_view


class CampaignViewSerializerTests(unittest.TestCase):
    def test_public_turn_keeps_contract_and_permissions(self) -> None:
        turn = {
            "turn_id": "turn_1",
            "turn_number": 7,
            "status": "active",
            "actor": "slot_aria",
            "action_type": "do",
            "player_id": "player_1",
            "input_text_display": "Aria studies the sigils.",
            "gm_text_display": "The glyphs answer with a pale hum.",
            "requests": [{"type": "clarify"}],
            "created_at": "2026-03-10T10:00:00Z",
            "updated_at": "2026-03-10T10:00:01Z",
            "edit_history": [{"at": "x"}],
            "patch": {
                "characters": {"slot_aria": {"scene_id": "vault"}},
                "items_new": {"item_1": {}},
                "plotpoints_add": [{"id": "p1"}],
                "plotpoints_update": [],
                "map_add_nodes": [],
                "map_add_edges": [{"from": "a", "to": "b"}],
                "events_add": ["rumble"],
            },
            "attribute_profile": {"focus": "high"},
            "combat_resolution": {"resolved": False},
            "resource_deltas_applied": {"hp": -2},
            "progression_events": [{"kind": "xp"}],
            "canon_gate": {"ok": True},
            "codex_updates": [{"kind": "race"}],
        }
        campaign = {
            "campaign_meta": {"host_player_id": "player_host"},
            "players": {"player_1": {"display_name": "Player One"}},
        }
        blank_patch = {
            "characters": {},
            "items_new": {},
            "plotpoints_add": [],
            "plotpoints_update": [],
            "map_add_nodes": [],
            "map_add_edges": [],
            "events_add": [],
        }
        captured = {}

        def normalize_requests_payload(payload, *, default_actor):  # type: ignore[no-untyped-def]
            captured["default_actor"] = default_actor
            return payload

        rendered = campaign_view.public_turn(
            turn,
            campaign,
            "player_1",
            display_name_for_slot=lambda _campaign, _slot: "Aria",
            is_slot_id=lambda actor: actor.startswith("slot_"),
            normalize_requests_payload=normalize_requests_payload,
            blank_patch=lambda: copy.deepcopy(blank_patch),
            is_campaign_player_fn=campaign_view.is_campaign_player,
        )

        self.assertEqual(rendered["mode"], "TUN")
        self.assertEqual(rendered["actor_display"], "Aria")
        self.assertEqual(rendered["edit_count"], 1)
        self.assertEqual(rendered["patch_summary"]["characters_changed"], 1)
        self.assertEqual(rendered["patch_summary"]["items_added"], 1)
        self.assertTrue(rendered["can_edit"])
        self.assertTrue(rendered["can_undo"])
        self.assertTrue(rendered["can_retry"])
        self.assertEqual(captured["default_actor"], "slot_aria")
        self.assertIsNot(rendered["attribute_profile"], turn["attribute_profile"])

    def test_build_public_boards_hides_comment_lines_for_non_owner(self) -> None:
        campaign = {
            "boards": {
                "player_diaries": {
                    "player_1": {"content": "public line\n// private note"},
                    "player_2": {"content": "other line\n// hidden detail"},
                }
            }
        }

        result = campaign_view.build_public_boards(
            campaign,
            "player_1",
            deep_copy=copy.deepcopy,
            filter_private_diary_content_fn=campaign_view.filter_private_diary_content,
        )

        self.assertEqual(result["player_diaries"]["player_1"]["content"], "public line\n// private note")
        self.assertEqual(result["player_diaries"]["player_2"]["content"], "other line")
        self.assertEqual(campaign["boards"]["player_diaries"]["player_2"]["content"], "other line\n// hidden detail")

    def test_build_campaign_view_uses_deps_and_does_not_mutate_input(self) -> None:
        campaign = {
            "campaign_meta": {
                "campaign_id": "cmp_1",
                "title": "Aelunor",
                "created_at": "2026-03-10T10:00:00Z",
                "updated_at": "2026-03-10T10:00:00Z",
                "status": "active",
                "host_player_id": "player_host",
            },
            "state": {"meta": {"day": 1}},
            "setup": {"world": {"completed": True}},
            "claims": {},
            "players": {"player_1": {"display_name": "Player One"}},
            "turns": [{"turn_id": "turn_1"}],
        }

        def normalize_campaign(value):  # type: ignore[no-untyped-def]
            value["state"]["normalized"] = True
            return value

        deps = campaign_view.CampaignViewDependencies(
            normalize_campaign=normalize_campaign,
            deep_copy=copy.deepcopy,
            build_setup_runtime=lambda _campaign, _viewer: {"phase": "active"},
            available_slots=lambda _campaign: [{"slot_id": "slot_aria"}],
            active_party=lambda _campaign: ["slot_aria"],
            display_name_for_slot=lambda _campaign, _slot: "Aria",
            normalize_world_time=lambda _meta: {"day": 1},
            build_public_boards=lambda _campaign, _viewer: {"authors_note": {"content": "note"}},
            active_turns=lambda _campaign: [{"turn_id": "turn_1"}],
            public_turn=lambda _turn, _campaign, _viewer: {"turn_id": "turn_1", "status": "active"},
            build_party_overview=lambda _campaign: [{"slot_id": "slot_aria"}],
            campaign_slots=lambda _campaign: ["slot_aria"],
            public_player=lambda player_id, player: {"player_id": player_id, "display_name": player.get("display_name")},
            build_viewer_context=lambda _campaign, viewer_id: {"player_id": viewer_id},
            live_snapshot=lambda _campaign_id: {"version": 1},
        )

        result = campaign_view.build_campaign_view(campaign, "player_1", deps=deps)

        self.assertEqual(result["campaign_meta"]["campaign_id"], "cmp_1")
        self.assertEqual(result["active_party"], ["slot_aria"])
        self.assertEqual(result["display_party"], [{"slot_id": "slot_aria", "display_name": "Aria"}])
        self.assertEqual(result["active_turns"], [{"turn_id": "turn_1", "status": "active"}])
        self.assertEqual(result["players"], [{"player_id": "player_1", "display_name": "Player One"}])
        self.assertNotIn("normalized", campaign["state"])
        self.assertEqual(result["viewer_context"]["player_id"], "player_1")


if __name__ == "__main__":
    unittest.main()

