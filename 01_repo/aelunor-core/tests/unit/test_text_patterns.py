import unittest

from app import main
from app.services import state_engine
from app.services import turn_engine
from app.text import patterns


class TextPatternWiringTests(unittest.TestCase):
    def test_main_reexports_pattern_names_from_text_module(self) -> None:
        pattern_names = (
            "ABILITY_UNLOCK_TRIGGER_PATTERNS",
            "ABILITY_UNLOCK_GENERIC_NAMES",
            "AUTO_ITEM_ACQUIRE_PATTERNS",
            "AUTO_ITEM_EQUIP_PATTERNS",
            "AUTO_ITEM_GENERIC_NAMES",
            "AUTO_INJURY_PATTERNS",
            "ACTION_STOPWORDS",
            "ENGLISH_LANGUAGE_MARKERS",
            "GERMAN_LANGUAGE_MARKERS",
            "NPC_GENERIC_NAME_TOKENS",
            "STORY_ACTION_CUES",
            "STORY_EXPLORE_CUES",
            "STORY_LEARN_CUES",
            "CONTEXT_META_DRIFT_MARKERS",
            "MANIFESTATION_STRONG_CUES",
            "MANIFESTATION_EFFECT_CUES",
            "SKILL_MANIFESTATION_NAME_STOPWORDS",
        )

        for name in pattern_names:
            self.assertIs(getattr(main, name), getattr(patterns, name), name)

    def test_configured_engines_keep_pattern_globals_available(self) -> None:
        for name in (
            "ABILITY_UNLOCK_TRIGGER_PATTERNS",
            "AUTO_ITEM_ACQUIRE_PATTERNS",
            "AUTO_ITEM_EQUIP_PATTERNS",
            "AUTO_INJURY_PATTERNS",
            "MANIFESTATION_STRONG_CUES",
            "STORY_LEARN_CUES",
        ):
            self.assertIs(getattr(state_engine, name), getattr(main, name), name)

        for name in ("ACTION_STOPWORDS", "ENGLISH_LANGUAGE_MARKERS", "GERMAN_LANGUAGE_MARKERS"):
            self.assertIs(getattr(turn_engine, name), getattr(main, name), name)

    def test_auto_item_detection_matches_current_behavior(self) -> None:
        events = state_engine.extract_auto_story_item_events("Matchek findet den rostigen Dolch.", "Matchek")

        self.assertEqual(events, [{"name": "rostigen Dolch", "mode": "acquire", "sentence": "Matchek findet den rostigen Dolch."}])
        self.assertEqual(state_engine.extract_auto_story_items("Matchek findet den rostigen Dolch.", "Matchek"), ["rostigen Dolch"])

    def test_ability_detection_matches_current_behavior(self) -> None:
        abilities = state_engine.extract_auto_learned_abilities("Matchek erlernt die Technik Klingenfokus.", "Matchek")

        self.assertEqual([entry["name"] for entry in abilities], ["Klingenfokus", "Technik Klingenfokus"])
        self.assertEqual(abilities[0]["type"], "active")
        self.assertEqual(abilities[0]["tags"], ["story_auto", "auto_unlock", "kampf"])

    def test_injury_detection_matches_current_behavior(self) -> None:
        injuries = state_engine.extract_auto_story_injuries("Matchek erleidet einen tiefen Schnitt am linken Arm.", "Matchek")

        self.assertEqual(len(injuries), 1)
        self.assertEqual(injuries[0]["title"], "tiefen Schnitt am linken Arm")
        self.assertEqual(injuries[0]["severity"], "mittel")
        self.assertEqual(injuries[0]["effects"], ["Schmerz bei Kraft", "Belastung verschlimmert den Schmerz"])
        self.assertTrue(injuries[0]["will_scar"])

    def test_unrelated_story_text_does_not_match_auto_extractors(self) -> None:
        text = "Matchek blickt schweigend in den Nebel."

        self.assertEqual(state_engine.extract_auto_story_items(text, "Matchek"), [])
        self.assertEqual(state_engine.extract_auto_learned_abilities(text, "Matchek"), [])
        self.assertEqual(state_engine.extract_auto_story_injuries(text, "Matchek"), [])


if __name__ == "__main__":
    unittest.main()
