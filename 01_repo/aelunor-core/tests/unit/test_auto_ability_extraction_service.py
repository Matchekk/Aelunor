import unittest

from app.services.extraction import abilities


class AutoAbilityExtractionServiceTests(unittest.TestCase):
    def test_auto_ability_detection_matches_current_behavior(self) -> None:
        result = abilities.extract_auto_learned_abilities("Matchek erlernt die Technik Klingenfokus.", "Matchek")

        self.assertEqual([entry["name"] for entry in result], ["Klingenfokus", "Technik Klingenfokus"])
        self.assertEqual(result[0]["type"], "active")
        self.assertEqual(result[0]["tags"], ["story_auto", "auto_unlock", "kampf"])

    def test_unrelated_story_text_does_not_match_abilities(self) -> None:
        self.assertEqual(abilities.extract_auto_learned_abilities("Matchek blickt schweigend in den Nebel.", "Matchek"), [])


if __name__ == "__main__":
    unittest.main()
