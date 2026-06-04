import unittest

from app import main
from app.config import attributes as attribute_config
from app.config import combat as combat_config
from app.config import setup as setup_config
from app.services import state_engine


class DomainConfigWiringTests(unittest.TestCase):
    def test_main_reexports_attribute_config_names(self) -> None:
        for name in (
            "ATTRIBUTE_INFLUENCE_DISTRIBUTION",
            "ATTRIBUTE_INFLUENCE_STRENGTH",
        ):
            self.assertIs(getattr(main, name), getattr(attribute_config, name), name)

    def test_main_reexports_combat_config_names(self) -> None:
        for name in (
            "COMBAT_NARRATIVE_HINTS",
            "COMBAT_END_HINTS",
        ):
            self.assertIs(getattr(main, name), getattr(combat_config, name), name)

    def test_main_reexports_setup_config_names(self) -> None:
        for name in (
            "WORLD_SETUP_CHAPTERS",
            "CHAR_SETUP_CHAPTERS",
            "LEGACY_SELECT_ALIASES",
        ):
            self.assertIs(getattr(main, name), getattr(setup_config, name), name)

    def test_configured_state_engine_keeps_domain_globals_available(self) -> None:
        for name in (
            "ATTRIBUTE_INFLUENCE_DISTRIBUTION",
            "ATTRIBUTE_INFLUENCE_STRENGTH",
            "COMBAT_NARRATIVE_HINTS",
            "COMBAT_END_HINTS",
            "WORLD_SETUP_CHAPTERS",
            "CHAR_SETUP_CHAPTERS",
            "LEGACY_SELECT_ALIASES",
        ):
            self.assertIs(getattr(state_engine, name), getattr(main, name), name)

    def test_attribute_combat_and_setup_values_keep_current_behavior(self) -> None:
        self.assertEqual(
            main.ATTRIBUTE_INFLUENCE_DISTRIBUTION,
            (
                ("none", 0.15),
                ("low", 0.25),
                ("medium", 0.35),
                ("high", 0.25),
            ),
        )
        self.assertEqual(main.ATTRIBUTE_INFLUENCE_STRENGTH["high"], 0.35)
        self.assertIn("angriff", main.COMBAT_NARRATIVE_HINTS)
        self.assertEqual(main.COMBAT_END_HINTS[-1], "ruhe kehrt ein")
        self.assertEqual(main.WORLD_SETUP_CHAPTERS["foundations"]["label"], "Grundton der Welt")
        self.assertEqual(main.CHAR_SETUP_CHAPTERS["drive"]["label"], "Motivation und Einstieg")
        self.assertEqual(main.LEGACY_SELECT_ALIASES["char_gender"]["nonbinary"], "Nichtbinär")


if __name__ == "__main__":
    unittest.main()
