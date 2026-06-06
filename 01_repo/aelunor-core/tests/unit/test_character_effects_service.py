import unittest

from app.services.characters import effects


class CharacterEffectsServiceTests(unittest.TestCase):
    def test_migrate_effects_from_conditions_adds_missing_conditions(self) -> None:
        character = {"conditions": ["Vergiftet", "Geblendet"], "effects": []}
        effects.migrate_effects_from_conditions(character)
        names = [effect["name"] for effect in character["effects"]]
        self.assertEqual(names, ["Vergiftet", "Geblendet"])
        for effect in character["effects"]:
            self.assertEqual(effect["category"], "condition")
            self.assertEqual(effect["source"], "legacy_condition")
            self.assertTrue(effect["visible"])
            self.assertEqual(effect["modifiers"], [])

    def test_migrate_effects_from_conditions_is_idempotent_on_existing_names(self) -> None:
        character = {
            "conditions": ["Vergiftet"],
            "effects": [{"name": "Vergiftet", "category": "combat"}],
        }
        effects.migrate_effects_from_conditions(character)
        self.assertEqual(len(character["effects"]), 1)
        self.assertEqual(character["effects"][0]["category"], "combat")

    def test_migrate_effects_handles_empty_conditions(self) -> None:
        character = {"effects": []}
        effects.migrate_effects_from_conditions(character)
        self.assertEqual(character["effects"], [])


if __name__ == "__main__":
    unittest.main()
