import unittest

from app.services.extraction import items


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


if __name__ == "__main__":
    unittest.main()
