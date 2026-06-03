import unittest

from app import main
from app.config import progression
from app.services import state_engine
from app.services import turn_engine


class ProgressionConfigWiringTests(unittest.TestCase):
    def test_main_reexports_progression_config_names(self) -> None:
        config_names = (
            "PROGRESSION_CLAIM_TYPES",
            "PROGRESSION_EXTRACTOR_CONFIDENCE_ORDER",
            "PROGRESSION_EXTRACTOR_CONFIDENCE_SCORE",
            "PROGRESSION_EXTRACTOR_CONFIDENCE_THRESHOLDS",
            "RESOURCE_KEYS",
            "ATTRIBUTE_KEYS",
            "PROGRESSION_EVENT_TYPES",
            "PROGRESSION_EVENT_SEVERITIES",
            "PROGRESSION_EVENT_SEVERITY_MULTIPLIER",
            "PROGRESSION_EVENT_BASE_XP",
            "PROGRESSION_EVENT_PRIORITY",
            "PROGRESSION_DENSITY_CAP_NON_MILESTONE",
            "PROGRESSION_DENSITY_CAP_MILESTONE",
            "PROGRESSION_SET_DIRECT_KEYS",
            "FIRST_SKILL_FORCE_PROBABILITY",
            "SKILL_KEYS",
            "SKILL_RANKS",
            "SKILL_RANK_ORDER",
            "CLASS_ASCENSION_STATUSES",
            "LEGACY_ROLE_CLASS_MAP",
            "LEGACY_SKILL_NAME_MAP",
            "LEGACY_SKILL_TAGS",
            "RESISTANCE_KEYS",
            "SKILL_ATTRIBUTE_MAP",
            "SKILL_RANK_THRESHOLDS",
            "SKILL_OUTCOME_XP",
            "SKILL_PATHS",
            "SKILL_EVOLUTIONS",
            "SKILL_FUSIONS",
            "DEFAULT_DYNAMIC_SKILL_LEVEL_MAX",
            "DEFAULT_NUMERIC_SKILL_DELTA_XP",
        )

        for name in config_names:
            self.assertIs(getattr(main, name), getattr(progression, name), name)

    def test_configured_engines_keep_progression_config_globals_available(self) -> None:
        for name in (
            "SKILL_RANKS",
            "SKILL_RANK_ORDER",
            "SKILL_RANK_THRESHOLDS",
            "SKILL_KEYS",
            "RESOURCE_KEYS",
            "ATTRIBUTE_KEYS",
            "PROGRESSION_EVENT_BASE_XP",
            "PROGRESSION_SET_DIRECT_KEYS",
            "DEFAULT_DYNAMIC_SKILL_LEVEL_MAX",
            "DEFAULT_NUMERIC_SKILL_DELTA_XP",
        ):
            self.assertIs(getattr(state_engine, name), getattr(main, name), name)

        for name in (
            "ATTRIBUTE_KEYS",
            "PROGRESSION_SET_DIRECT_KEYS",
            "DEFAULT_DYNAMIC_SKILL_LEVEL_MAX",
            "DEFAULT_NUMERIC_SKILL_DELTA_XP",
        ):
            self.assertIs(getattr(turn_engine, name), getattr(main, name), name)

    def test_skill_and_xp_calculations_keep_current_results(self) -> None:
        self.assertEqual(state_engine.next_skill_xp_for_level(2), 135)
        self.assertEqual(state_engine.skill_rank_for_level(12), "A")
        self.assertEqual(state_engine.skill_rank_sort_value("S"), 6)

        skill = state_engine.normalize_dynamic_skill_state({"name": "Funkenwurf", "level": 12})
        self.assertEqual(skill["level_max"], 10)
        self.assertEqual(skill["level"], 10)


if __name__ == "__main__":
    unittest.main()
