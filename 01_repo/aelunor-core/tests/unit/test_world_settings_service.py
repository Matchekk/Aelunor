import unittest

from app.services.world.world_settings import normalize_world_settings


class WorldSettingsServiceTests(unittest.TestCase):
    def test_normalize_world_settings_stabilizes_minimal_payload(self) -> None:
        settings = normalize_world_settings({"campaign_length": "OPEN", "offclass_xp_multiplier": 9})

        self.assertEqual(settings["campaign_length"], "open")
        self.assertEqual(settings["resource_name"], "Aether")
        self.assertEqual(settings["offclass_xp_multiplier"], 1.0)
        self.assertIsNone(settings["target_turns"]["open"])
        self.assertIn("open", settings["pacing_profile"])


if __name__ == "__main__":
    unittest.main()
