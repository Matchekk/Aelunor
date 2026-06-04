import unittest

from app import main
from app.config import canon as canon_config
from app.config import injuries as injury_config
from app.config import migrations as migration_config
from app.services import state_engine
from app.services import turn_engine
from app.services.world import injury_state


class CanonMigrationInjuryConfigWiringTests(unittest.TestCase):
    def test_main_reexports_canon_config_names(self) -> None:
        for name in (
            "CANON_GATE_DOMAINS_SUPPORTED",
            "CANON_GATE_ACTIVE_DOMAINS",
            "CANON_CHARACTER_FIELDS",
        ):
            self.assertIs(getattr(main, name), getattr(canon_config, name), name)

    def test_main_reexports_migration_config_names(self) -> None:
        for name in (
            "LEGACY_SHADOW_FIELDS",
            "MIGRATION_ONLY_FIELDS",
        ):
            self.assertIs(getattr(main, name), getattr(migration_config, name), name)

    def test_main_reexports_injury_config_names(self) -> None:
        for name in (
            "INJURY_SEVERITIES",
            "INJURY_HEALING_STAGES",
        ):
            self.assertIs(getattr(main, name), getattr(injury_config, name), name)

    def test_configured_engines_keep_extracted_globals_available(self) -> None:
        for name in (
            "CANON_GATE_DOMAINS_SUPPORTED",
            "CANON_GATE_ACTIVE_DOMAINS",
            "CANON_CHARACTER_FIELDS",
            "LEGACY_SHADOW_FIELDS",
            "MIGRATION_ONLY_FIELDS",
            "INJURY_SEVERITIES",
            "INJURY_HEALING_STAGES",
        ):
            self.assertIs(getattr(state_engine, name), getattr(main, name), name)

        for name in (
            "INJURY_SEVERITIES",
            "INJURY_HEALING_STAGES",
        ):
            self.assertIs(getattr(turn_engine, name), getattr(main, name), name)
            self.assertIs(getattr(injury_state, name), getattr(main, name), name)

    def test_canon_migration_and_injury_values_keep_current_behavior(self) -> None:
        self.assertEqual(
            main.CANON_GATE_DOMAINS_SUPPORTED,
            ("progression", "items", "location", "faction", "injury", "spellschool"),
        )
        self.assertEqual(main.CANON_GATE_ACTIVE_DOMAINS, {"progression"})
        self.assertIn("inventory", main.CANON_CHARACTER_FIELDS)
        self.assertIn("resources", main.LEGACY_SHADOW_FIELDS)
        self.assertIn("bio.party_role", main.MIGRATION_ONLY_FIELDS)
        self.assertEqual(main.INJURY_SEVERITIES, {"leicht", "mittel", "schwer"})
        self.assertEqual(main.INJURY_HEALING_STAGES, {"frisch", "heilend", "fast_heil", "geheilt"})


if __name__ == "__main__":
    unittest.main()
