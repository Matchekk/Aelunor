import unittest

from app.services import state_engine
from app.dependencies import factories
from app.services.sheets import character as character_sheet
from app.services.sheets import npc as npc_sheet


class SheetViewsServiceTests(unittest.TestCase):
    def test_character_sheet_service_matches_state_engine_facade_shape(self) -> None:
        character = state_engine.blank_character_state("slot_1")
        character["bio"]["name"] = "Aria"
        character["scene_id"] = "scene_1"
        campaign = {
            "players": {"player_1": {"display_name": "Mira"}},
            "claims": {"slot_1": "player_1"},
            "state": {
                "characters": {"slot_1": character},
                "items": {},
                "world": {"settings": {"resource_name": "Aether"}},
                "plotpoints": [],
                "scenes": {"scene_1": {"name": "Hain"}},
            },
        }

        result = character_sheet.build_character_sheet_view(
            campaign,
            "slot_1",
            ports=factories._character_sheet_ports({}),
        )

        self.assertEqual(result["slot_id"], "slot_1")
        self.assertEqual(result["display_name"], "Aria")
        self.assertIn("overview", result["sheet"])
        self.assertIn("gear_inventory", result["sheet"])
        self.assertEqual(result["sheet"]["overview"]["claim_status"], "geclaimt")

    def test_npc_sheet_service_preserves_public_npc_fields(self) -> None:
        campaign = {
            "state": {
                "world": {"settings": {"resource_name": "Aether"}},
                "scenes": {"scene_1": {"name": "Markt"}},
                "npc_codex": {
                    "npc_mira": {
                        "npc_id": "npc_mira",
                        "name": "Mira",
                        "last_seen_scene_id": "scene_1",
                        "level": 2,
                        "skills": {},
                    }
                },
            }
        }

        result = npc_sheet.build_npc_sheet_view(campaign, "npc_mira", ports=factories._npc_sheet_ports({}))

        self.assertEqual(result["npc_id"], "npc_mira")
        self.assertEqual(result["name"], "Mira")
        self.assertEqual(result["last_seen_scene_name"], "Markt")
        self.assertIn("resources", result)


if __name__ == "__main__":
    unittest.main()
