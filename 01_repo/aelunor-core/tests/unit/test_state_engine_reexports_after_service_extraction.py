import re
import unittest

from app import main
from app.services import state_engine, turn_engine
from app.services.characters import appearance_state, appearance_summary, defaults, resource_maxima, resources
from app.services.world import naming


class StateEngineServiceExtractionTests(unittest.TestCase):
    def test_state_engine_reexports_extracted_state_basics(self) -> None:
        self.assertIn("blank_patch", state_engine.EXPORTED_SYMBOLS)
        self.assertIs(state_engine.blank_patch, main.blank_patch)
        self.assertIs(state_engine.make_join_code, main.make_join_code)
        self.assertIs(state_engine.is_slot_id, main.is_slot_id)

        self.assertEqual(state_engine.slot_id(3), "slot_3")
        self.assertEqual(state_engine.slot_index("slot_10"), 10)
        self.assertEqual(state_engine.slot_index("invalid"), 9999)
        self.assertEqual(state_engine.ordered_slots(["slot_10", "slot_2", "slot_1"]), ["slot_1", "slot_2", "slot_10"])
        self.assertRegex(state_engine.make_join_code(), re.compile(r"^[A-HJ-NP-Z2-9]{6}$"))
        self.assertEqual(
            state_engine.blank_patch(),
            {
                "meta": {},
                "characters": {},
                "items_new": {},
                "plotpoints_add": [],
                "plotpoints_update": [],
                "map_add_nodes": [],
                "map_add_edges": [],
                "events_add": [],
            },
        )

    def test_character_default_builder_preserves_shape_and_fresh_mutables(self) -> None:
        self.assertIn("blank_character_state", state_engine.EXPORTED_SYMBOLS)
        self.assertIs(state_engine.blank_character_state, defaults.blank_character_state)

        first = state_engine.blank_character_state("slot_1")
        second = state_engine.blank_character_state("slot_1")
        self.assertEqual(first["slot_id"], "slot_1")
        self.assertEqual(first["hp_current"], 10)
        self.assertEqual(first["resources"]["aether"]["current"], 5)
        self.assertEqual(first["progression"]["resource_name"], "Aether")
        self.assertEqual(first["bio"]["age_stage"], "young")

        first["inventory"]["items"].append({"id": "item_1"})
        self.assertEqual(second["inventory"]["items"], [])

    def test_resource_helpers_preserve_reexports_and_behavior(self) -> None:
        for name, module in {
            "resource_name_for_character": resources,
            "canonical_resource_field_name": resources,
            "sync_canonical_resources": resources,
            "strip_legacy_resource_shadows": resources,
            "rebuild_resource_maxima": resource_maxima,
            "calculate_base_resource_maxima": resource_maxima,
        }.items():
            self.assertIn(name, state_engine.EXPORTED_SYMBOLS)
            self.assertIs(getattr(state_engine, name), getattr(module, name), name)

        character = state_engine.blank_character_state("slot_1")
        character["progression"]["resource_name"] = "Mana"
        self.assertEqual(state_engine.resource_name_for_character(character, {"resource_name": "Aether"}), "Mana")
        self.assertEqual(state_engine.canonical_resource_field_name("Lebenspunkte"), "hp")

        state_engine.sync_canonical_resources(character)
        self.assertEqual(character["hp_current"], 10)
        self.assertEqual(character["hp_max"], 10)
        self.assertEqual(character["progression"]["resource_current"], 5)
        self.assertNotIn("hp", character["resources"])

    def test_world_naming_and_species_wrappers_preserve_constraints(self) -> None:
        self.assertIn("fantasy_syllables_for_anchor", state_engine.EXPORTED_SYMBOLS)
        self.assertIs(state_engine.fantasy_syllables_for_anchor, naming.fantasy_syllables_for_anchor)

        summary = {"theme": "Nebel", "tone": "dunkel", "central_conflict": "Grenzkrieg", "monsters_density": "hoch"}
        world_name = state_engine.generate_world_name(summary, "seed-a")
        self.assertEqual(world_name, state_engine.generate_world_name(summary, "seed-a"))
        self.assertGreaterEqual(len(world_name), 4)

        races = state_engine.generate_world_race_profiles(summary, seed_hint="seed-a")
        beasts = state_engine.generate_world_beast_profiles(summary, seed_hint="seed-a")
        self.assertGreaterEqual(len(races), 5)
        self.assertLessEqual(len(races), 7)
        self.assertGreaterEqual(len(beasts), 6)
        self.assertLessEqual(len(beasts), 12)
        self.assertTrue(all(key.startswith("race_") for key in races))
        self.assertTrue(all(key.startswith("beast_") for key in beasts))

    def test_appearance_helpers_preserve_reexports_and_behavior(self) -> None:
        for name, module in {
            "infer_age_years": appearance_state,
            "derive_age_stage": appearance_state,
            "normalize_appearance_state": appearance_state,
            "build_appearance_summary_short": appearance_summary,
            "rebuild_character_appearance": appearance_summary,
        }.items():
            self.assertIn(name, state_engine.EXPORTED_SYMBOLS)
            self.assertIs(getattr(state_engine, name), getattr(module, name), name)

        self.assertEqual(state_engine.infer_age_years("42 Jahre"), 42)
        self.assertEqual(state_engine.derive_age_stage(42), "adult")
        appearance = state_engine.normalize_appearance_state({"appearance": {"muscle": 99, "scars_visible": ["Wangenriss"]}})
        self.assertEqual(appearance["muscle"], 5)
        self.assertEqual(appearance["scars_visible"], ["Wangenriss"])

        character = state_engine.blank_character_state("slot_1")
        state_engine.rebuild_character_appearance(character, {"absolute_day": 1})
        self.assertIn("summary_short", character["appearance"])
        self.assertIn("summary_full", character["appearance"])

    def test_configure_bridge_still_exposes_extracted_names(self) -> None:
        self.assertTrue(getattr(state_engine, "_CONFIGURED", False))
        self.assertTrue(getattr(turn_engine, "_CONFIGURED", False))
        for name in (
            "blank_character_state",
            "resource_name_for_character",
            "rebuild_resource_maxima",
            "normalize_appearance_state",
            "generate_world_race_profiles",
        ):
            self.assertTrue(callable(getattr(main, name)), name)
            self.assertTrue(callable(getattr(state_engine, name)), name)


if __name__ == "__main__":
    unittest.main()
