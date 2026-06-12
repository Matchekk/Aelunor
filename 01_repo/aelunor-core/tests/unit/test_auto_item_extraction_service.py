import unittest

from app.services.extraction import items


def _campaign_with_turn(gm_text: str, *, character=None):
    return {
        "state": {
            "items": {},
            "characters": {"slot_p1": character if character is not None else {}},
        },
        "players": {},
        "turns": [
            {
                "turn_id": "turn-1",
                "status": "active",
                "actor": "slot_p1",
                "action_type": "do",
                "gm_text_display": gm_text,
                "input_text_display": "",
            }
        ],
    }


class AutoItemExtractionServiceTests(unittest.TestCase):
    def test_auto_item_detection_matches_current_behavior(self) -> None:
        events = items.extract_auto_story_item_events("Matchek findet den rostigen Dolch.", "Matchek")

        self.assertEqual(
            events,
            [{"name": "rostigen Dolch", "mode": "acquire", "sentence": "Matchek findet den rostigen Dolch."}],
        )
        self.assertEqual(items.extract_auto_story_items("Matchek findet den rostigen Dolch.", "Matchek"), ["rostigen Dolch"])

    def test_unrelated_story_text_does_not_match_items(self) -> None:
        self.assertEqual(items.extract_auto_story_items("Matchek blickt schweigend in den Nebel.", "Matchek"), [])

    def test_equip_event_lands_in_inventory_and_canonical_slot(self) -> None:
        campaign = _campaign_with_turn(
            "Matchek zieht das geschwungene Langschwert.",
            character={"bio": {"name": "Matchek"}},
        )
        items.materialize_story_items_from_turn_history(campaign)

        character = campaign["state"]["characters"]["slot_p1"]
        inventory_ids = [entry["item_id"] for entry in character["inventory"]["items"]]
        self.assertEqual(len(inventory_ids), 1)
        item_id = inventory_ids[0]
        self.assertEqual(character["equipment"].get("weapon"), item_id)
        self.assertEqual(campaign["state"]["items"][item_id]["slot"], "weapon")

    def test_reequip_of_known_item_does_not_duplicate_or_skip(self) -> None:
        campaign = _campaign_with_turn(
            "Matchek zieht das geschwungene Langschwert.",
            character={"bio": {"name": "Matchek"}},
        )
        items.materialize_story_items_from_turn_history(campaign)
        character = campaign["state"]["characters"]["slot_p1"]
        item_id = character["inventory"]["items"][0]["item_id"]

        character["equipment"] = {}
        items.materialize_story_items_from_turn_history(campaign)

        self.assertEqual(character["equipment"].get("weapon"), item_id)
        self.assertEqual(len(character["inventory"]["items"]), 1)


if __name__ == "__main__":
    unittest.main()
