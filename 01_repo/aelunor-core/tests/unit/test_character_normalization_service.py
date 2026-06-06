import unittest

# Importing app.main wires configure_dependencies for the appearance/resource/
# injury/progression submodules that normalize_character_state depends on.
from app.services import state_engine
from app.services.characters import normalization


class CharacterNormalizationServiceTests(unittest.TestCase):
    def test_blank_character_state_shape_is_stable(self) -> None:
        blank = state_engine.blank_character_state("slot_1")
        self.assertEqual(blank["slot_id"], "slot_1")
        for key in ("bio", "resources", "attributes", "progression", "inventory", "equipment", "journal"):
            self.assertIn(key, blank)

    def test_normalize_character_state_stabilizes_minimal_fixture(self) -> None:
        character = normalization.normalize_character_state(
            {"bio": {"name": "Aria"}}, "slot_1", {}, None
        )
        self.assertEqual(character["slot_id"], "slot_1")
        self.assertEqual(character["bio"]["name"], "Aria")
        self.assertIn("derived", character)
        self.assertIn("combat_flags", character["derived"])
        self.assertIn("defense", character["derived"])
        # Idempotent: re-normalizing the result keeps the slot/bio stable.
        again = normalization.normalize_character_state(character, "slot_1", {}, None)
        self.assertEqual(again["slot_id"], "slot_1")
        self.assertEqual(again["bio"]["name"], "Aria")

    def test_rebuild_all_character_derived_stabilizes_minimal_campaign(self) -> None:
        campaign = {
            "state": {
                "meta": {},
                "items": {},
                "characters": {"slot_1": {"slot_id": "slot_1", "bio": {"name": "Aria"}}},
            }
        }

        normalization.rebuild_all_character_derived(campaign)

        character = campaign["state"]["characters"]["slot_1"]
        self.assertEqual(character["slot_id"], "slot_1")
        self.assertIn("derived", character)
        self.assertIn("combat_flags", character["derived"])

    def test_sync_scars_into_appearance_maps_character_scars(self) -> None:
        character = {"scars": [{"id": "scar_1", "title": "Narbe", "description": "alt", "created_turn": 3}]}
        normalization.sync_scars_into_appearance(character)
        appearance_scars = character["appearance"]["scars"]
        self.assertEqual(len(appearance_scars), 1)
        self.assertEqual(appearance_scars[0]["label"], "Narbe")
        self.assertEqual(appearance_scars[0]["turn_number"], 3)
        self.assertTrue(appearance_scars[0]["visible"])

    def test_looks_like_legacy_seeded_skills_rejects_empty_and_partial(self) -> None:
        self.assertFalse(normalization.looks_like_legacy_seeded_skills({}))
        self.assertFalse(normalization.looks_like_legacy_seeded_skills({"stealth": {"level": 1}}))

    def test_normalization_logic_lives_in_character_module(self) -> None:
        self.assertIs(state_engine.sync_scars_into_appearance, normalization.sync_scars_into_appearance)
        self.assertIs(state_engine.resolve_injury_healing, normalization.resolve_injury_healing)


if __name__ == "__main__":
    unittest.main()
