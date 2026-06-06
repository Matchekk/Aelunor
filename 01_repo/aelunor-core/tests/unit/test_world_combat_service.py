import unittest

from app.services.world.combat import normalize_combat_meta


class WorldCombatServiceTests(unittest.TestCase):
    def test_normalize_combat_meta_stabilizes_minimal_meta(self) -> None:
        meta = {"combat": {"active": True, "round": "2", "phase": "collecting", "action_queue": []}}

        combat = normalize_combat_meta(meta)

        self.assertTrue(combat["active"])
        self.assertEqual(combat["round"], 2)
        self.assertEqual(combat["phase"], "collecting")
        self.assertEqual(combat["participants"], [])
        self.assertEqual(meta["combat"], combat)


if __name__ == "__main__":
    unittest.main()
