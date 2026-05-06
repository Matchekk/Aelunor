import copy
import unittest

from app.services import state_engine
from app.services import state_basics
from app.services.world import element_generation
from app.services.world import element_profiles
from app.services.world import element_relations
from app.services.world import species_profiles


class StateEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        state_engine.configure(
            {
                "SLOT_PREFIX": "slot_",
                "deep_copy": copy.deepcopy,
            }
        )

    def test_slot_helpers_roundtrip(self) -> None:
        self.assertEqual(state_engine.slot_id(3), "slot_3")
        self.assertEqual(state_engine.slot_index("slot_3"), 3)
        self.assertTrue(state_engine.is_slot_id("slot_3"))
        self.assertEqual(state_engine.slot_index("invalid"), 9999)
        self.assertFalse(state_engine.is_slot_id("invalid"))

    def test_state_basics_preserves_slot_and_patch_shapes(self) -> None:
        self.assertEqual(state_basics.slot_id(2, slot_prefix="slot_"), "slot_2")
        self.assertEqual(state_basics.slot_index("slot_2", slot_prefix="slot_"), 2)
        self.assertEqual(state_basics.slot_index("invalid", slot_prefix="slot_"), 9999)
        self.assertEqual(state_basics.ordered_slots(["slot_10", "slot_2"], slot_prefix="slot_"), ["slot_2", "slot_10"])
        self.assertTrue(state_basics.is_slot_id("slot_2"))
        self.assertFalse(state_basics.is_slot_id("slot_0"))
        self.assertEqual(
            state_basics.blank_patch(),
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

    def test_species_profiles_normalize_race_and_beast(self) -> None:
        race = species_profiles.normalize_race_profile(
            {
                "name": "  Mond Volk ",
                "strength_tags": [" Nacht ", "Nacht", ""],
                "playable": False,
            },
            race_id_from_name=lambda name: f"race_{name.strip().lower().replace(' ', '_')}",
            default_race_profile=species_profiles.default_race_profile,
        )
        beast = species_profiles.normalize_beast_profile(
            {
                "name": "Dornwolf",
                "danger_rating": 99,
                "known_abilities": ["Biss", " Biss ", ""],
            },
            beast_id_from_name=lambda name: f"beast_{name.lower()}",
            default_beast_profile=species_profiles.default_beast_profile,
            clamp=lambda value, low, high: max(low, min(high, value)),
        )

        self.assertEqual(race["id"], "race_mond_volk")
        self.assertEqual(race["name"], "Mond Volk")
        self.assertEqual(race["strength_tags"], ["Nacht"])
        self.assertFalse(race["playable"])
        self.assertEqual(beast["id"], "beast_dornwolf")
        self.assertEqual(beast["danger_rating"], 20)
        self.assertEqual(beast["known_abilities"], ["Biss"])

    def test_state_engine_species_wrappers_preserve_exported_contract(self) -> None:
        race = state_engine.normalize_race_profile(
            {
                "name": "Sternenvolk",
                "aliases": [" Sternenleute ", "Sternenleute"],
            }
        )
        beast = state_engine.normalize_beast_profile(
            {
                "name": "Aschewolf",
                "danger_rating": 0,
                "loot_tags": ["Fell", " Fell "],
            }
        )

        self.assertEqual(race["id"], "race_sternenvolk")
        self.assertEqual(race["aliases"], ["Sternenleute"])
        self.assertEqual(beast["id"], "beast_aschewolf")
        self.assertEqual(beast["danger_rating"], 1)
        self.assertEqual(beast["loot_tags"], ["Fell"])

    def test_element_profiles_normalize_shape_and_lists(self) -> None:
        element = element_profiles.normalize_element_profile(
            {
                "name": "  Mondlicht ",
                "origin": "weird",
                "aliases": [" Luna ", "Luna", ""],
                "discoverable": 0,
            },
            fallback_origin="generated",
            element_id_from_name=lambda name: f"elem_{name.strip().lower()}",
            default_element_profile=element_profiles.default_element_profile,
        )

        self.assertEqual(element["id"], "elem_mondlicht")
        self.assertEqual(element["name"], "Mondlicht")
        self.assertEqual(element["origin"], "generated")
        self.assertEqual(element["aliases"], ["Luna"])
        self.assertFalse(element["discoverable"])

    def test_state_engine_element_wrappers_preserve_exported_contract(self) -> None:
        element = state_engine.normalize_element_profile(
            {
                "name": "Feuer Herz",
                "origin": "core",
                "strengths_against": [" Eis ", "Eis"],
            }
        )

        self.assertEqual(state_engine.element_id_from_name("Feuer Herz"), "elem_feuer_herz")
        self.assertEqual(element["id"], "elem_feuer_herz")
        self.assertEqual(element["origin"], "core")
        self.assertEqual(element["strengths_against"], ["Eis"])

    def test_element_relation_helpers_normalize_and_sort(self) -> None:
        self.assertEqual(
            element_relations.element_sort_key(
                ("elem_b", {"name": "Äther"}),
                normalize_codex_alias_text=lambda value: str(value).lower().replace("ä", "ae"),
            ),
            ("aether", "elem_b"),
        )
        self.assertEqual(element_relations.relation_sort_value("dominant"), 4)
        self.assertEqual(element_relations.relation_sort_value("unknown"), 2)
        self.assertEqual(
            element_relations.normalize_element_relation(" Strong ", element_relations={"neutral", "strong"}),
            "strong",
        )
        self.assertEqual(
            element_relations.normalize_element_relation("unknown", element_relations={"neutral", "strong"}),
            "neutral",
        )

    def test_element_alias_index_helper_dedupes_and_sorts(self) -> None:
        index = element_relations.build_element_alias_index(
            {
                "elem_b": {"name": "Wasser", "aliases": ["Flut", "Flut"]},
                "elem_a": {"name": "Feuer", "aliases": ["Glut"]},
                "broken": "not-a-dict",
            },
            build_entity_alias_variants=lambda name, aliases: [name, *aliases],
            normalize_codex_alias_text=lambda value: str(value or "").strip().lower(),
            stable_sorted_mapping=lambda mapping, key_fn: dict(sorted(mapping.items(), key=key_fn)),
        )

        self.assertEqual(list(index.keys()), ["feuer", "flut", "glut", "wasser"])
        self.assertEqual(index["flut"], ["elem_b"])

    def test_state_engine_element_relation_wrappers_preserve_contract(self) -> None:
        self.assertEqual(state_engine.relation_sort_value("countered"), 0)
        self.assertEqual(state_engine.normalize_element_relation("dominant"), "dominant")
        self.assertEqual(state_engine.normalize_element_relation("invalid"), "neutral")
        self.assertEqual(state_engine.element_sort_key(("elem_fire", {"name": "Feuer"})), ("feuer", "elem_fire"))
        alias_index = state_engine.build_element_alias_index({"elem_fire": {"name": "Feuer", "aliases": ["Glut"]}})
        self.assertEqual(alias_index["feuer"], ["elem_fire"])
        self.assertEqual(alias_index["glut"], ["elem_fire"])

    def test_element_relation_matrix_helpers_normalize_maps(self) -> None:
        elements = {"elem_b": {"name": "B"}, "elem_a": {"name": "A"}}
        relations = element_relations.normalize_element_relations(
            {"elem_a": {"elem_b": " Strong ", "missing": "weak"}},
            elements,
            build_default_element_relations=element_relations.build_default_element_relations,
            normalize_element_relation=lambda value: element_relations.normalize_element_relation(
                value,
                element_relations={"neutral", "strong", "weak"},
            ),
            stable_sorted_mapping=lambda mapping, key_fn: dict(sorted(mapping.items(), key=key_fn)),
        )

        self.assertEqual(list(relations.keys()), ["elem_a", "elem_b"])
        self.assertEqual(relations["elem_a"]["elem_b"], "strong")
        self.assertEqual(relations["elem_a"]["elem_a"], "neutral")
        self.assertEqual(relations["elem_b"]["elem_a"], "neutral")

    def test_state_engine_element_anchor_rules_preserve_contract(self) -> None:
        elements = {
            "elem_fire": {"name": "Feuer"},
            "elem_water": {"name": "Wasser"},
        }
        relations = state_engine.build_default_element_relations(elements)

        state_engine.apply_element_anchor_relation_rules(elements, relations)

        self.assertEqual(relations["elem_fire"]["elem_water"], "weak")
        self.assertEqual(relations["elem_water"]["elem_fire"], "strong")
        self.assertEqual(
            state_engine.normalize_element_relations({"elem_fire": {"elem_water": "dominant"}}, elements)["elem_fire"]["elem_water"],
            "dominant",
        )

    def test_generated_element_similarity_helper_detects_core_and_duplicates(self) -> None:
        normalize = lambda value: str(value or "").strip().lower()

        self.assertEqual(
            element_generation.generated_element_too_similar(
                {"name": ""},
                [],
                normalize_codex_alias_text=normalize,
                element_similarity_blacklist={"feuer": ["brand"]},
            ),
            (True, "EMPTY_NAME"),
        )
        self.assertEqual(
            element_generation.generated_element_too_similar(
                {"name": "Brandglas"},
                [],
                normalize_codex_alias_text=normalize,
                element_similarity_blacklist={"feuer": ["brand"]},
            ),
            (True, "TOO_SIMILAR_TO_CORE"),
        )
        self.assertEqual(
            element_generation.generated_element_too_similar(
                {"name": "Traum", "theme": "Nebel"},
                [{"name": "Traum", "theme": "Nebel"}],
                normalize_codex_alias_text=normalize,
                element_similarity_blacklist={},
            ),
            (True, "DUPLICATE_NAME"),
        )

    def test_state_engine_generated_element_similarity_wrapper_preserves_contract(self) -> None:
        self.assertEqual(
            state_engine.generated_element_too_similar({"name": ""}, []),
            (True, "EMPTY_NAME"),
        )
        self.assertEqual(
            state_engine.generated_element_too_similar(
                {"name": "Stern"},
                [{"name": "Sternenstaub", "theme": "kosmisch"}],
            ),
            (True, "DUPLICATE_THEME"),
        )

    def test_normalize_patch_semantics_scene_set_alias(self) -> None:
        patch = {
            "characters": {
                "slot_1": {
                    "scene_set": "scene_forest",
                    "bio_set": {"name": "Mati"},
                }
            }
        }
        normalized = state_engine.normalize_patch_semantics(patch)
        char_patch = normalized["characters"]["slot_1"]
        self.assertEqual(char_patch["scene_id"], "scene_forest")
        self.assertNotIn("scene_set", char_patch)

    def test_merge_patch_payloads_combines_lists_and_maps(self) -> None:
        first = {
            "characters": {"slot_1": {"inventory_add": ["item_a"]}},
            "items_new": {"item_a": {"name": "A"}},
            "events_add": ["e1"],
        }
        second = {
            "characters": {"slot_1": {"inventory_add": ["item_b"]}},
            "items_new": {"item_b": {"name": "B"}},
            "events_add": ["e2"],
        }
        merged = state_engine.merge_patch_payloads(first, second)
        self.assertIn("item_a", merged["items_new"])
        self.assertIn("item_b", merged["items_new"])
        self.assertEqual(merged["events_add"], ["e1", "e2"])
        self.assertEqual(merged["characters"]["slot_1"]["inventory_add"], ["item_a", "item_b"])

    def test_setup_phase_display_distinguishes_ready_and_active(self) -> None:
        self.assertEqual(state_engine.setup_phase_display("world_setup"), "Weltaufbau")
        self.assertEqual(state_engine.setup_phase_display("character_setup_open"), "Charakterwerdung")
        self.assertEqual(state_engine.setup_phase_display("ready_to_start"), "Bereit zum Start")
        self.assertEqual(state_engine.setup_phase_display("active"), "Aktive Spielphase")


if __name__ == "__main__":
    unittest.main()
