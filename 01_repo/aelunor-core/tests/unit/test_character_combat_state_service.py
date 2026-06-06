import unittest

from app.services.characters.combat_state import calculate_combat_flags


class CharacterCombatStateServiceTests(unittest.TestCase):
    def test_calculate_combat_flags_handles_downed_and_stunned(self) -> None:
        flags = calculate_combat_flags(
            {
                "hp_current": 0,
                "combat_state": {"in_combat": False},
                "effects": [{"category": "stun", "tags": []}],
            }
        )

        self.assertEqual(flags, {"in_combat": False, "downed": True, "can_act": False})

    def test_calculate_combat_flags_marks_combat_effect(self) -> None:
        flags = calculate_combat_flags({"hp_current": 3, "effects": [{"category": "combat"}]})

        self.assertEqual(flags, {"in_combat": True, "downed": False, "can_act": True})


if __name__ == "__main__":
    unittest.main()
