import unittest

from app.services.extraction import classes


class AutoClassExtractionServiceTests(unittest.TestCase):
    def test_auto_class_detection_matches_current_behavior(self) -> None:
        result = classes.extract_auto_class_change("Matchek wird zum Schattenritter (C-Rang).", "Matchek")

        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "class_schattenritter")
        self.assertEqual(result["name"], "Schattenritter")
        self.assertEqual(result["rank"], "C")
        self.assertEqual(result["affinity_tags"], ["schatten"])

    def test_unrelated_story_text_does_not_match_class(self) -> None:
        self.assertIsNone(classes.extract_auto_class_change("Matchek blickt schweigend in den Nebel.", "Matchek"))


if __name__ == "__main__":
    unittest.main()
