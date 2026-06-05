import unittest

from app.services.extraction import injuries


class AutoInjuryExtractionServiceTests(unittest.TestCase):
    def test_auto_injury_detection_matches_current_behavior(self) -> None:
        result = injuries.extract_auto_story_injuries("Matchek erleidet einen tiefen Schnitt am linken Arm.", "Matchek")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "tiefen Schnitt am linken Arm")
        self.assertEqual(result[0]["severity"], "mittel")
        self.assertEqual(result[0]["effects"], ["Schmerz bei Kraft", "Belastung verschlimmert den Schmerz"])
        self.assertTrue(result[0]["will_scar"])

    def test_unrelated_story_text_does_not_match_injuries(self) -> None:
        self.assertEqual(injuries.extract_auto_story_injuries("Matchek blickt schweigend in den Nebel.", "Matchek"), [])


if __name__ == "__main__":
    unittest.main()
