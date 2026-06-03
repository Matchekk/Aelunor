import copy
import unittest
from typing import Any, Dict, List

from app.services import state_engine
from app.services import state_basics
from app.services.world import appearance
from app.services.world import attribute_influence
from app.services.world import combat
from app.services.world import element_class_paths
from app.services.world import element_entities
from app.services.world import element_generation
from app.services.world import element_ids
from app.services.world import element_profiles
from app.services.world import element_relations
from app.services.world import element_skills
from app.services.world import injury_state
from app.services.world import progression
from app.services.world import state_defaults
from app.services.world import skill_costs
from app.services.world import skill_ranks
from app.services.world import skill_state
from app.services.world import species_profiles
from app.services.world import world_settings


class StateEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        state_engine.configure(
            {
                "SLOT_PREFIX": "slot_",
                "deep_copy": copy.deepcopy,
                "make_id": lambda prefix: f"{prefix}_test",
                "INJURY_SEVERITIES": {"leicht", "mittel", "schwer"},
                "INJURY_HEALING_STAGES": {"frisch", "heilend", "fast_heil", "geheilt"},
            }
        )

    def test_slot_helpers_roundtrip(self) -> None:
        self.assertEqual(state_engine.slot_id(3), "slot_3")
        self.assertEqual(state_engine.slot_index("slot_3"), 3)
        self.assertTrue(state_engine.is_slot_id("slot_3"))
        self.assertEqual(state_engine.slot_index("invalid"), 9999)
        self.assertFalse(state_engine.is_slot_id("invalid"))

    def test_skill_ranks_skill_rank_for_level_uses_threshold_order(self) -> None:
        thresholds = (("S", 20), ("A", 15), ("B", 10), ("F", 1))

        self.assertEqual(skill_ranks.skill_rank_for_level(0, skill_rank_thresholds=thresholds), "-")
        self.assertEqual(skill_ranks.skill_rank_for_level(1, skill_rank_thresholds=thresholds), "F")
        self.assertEqual(skill_ranks.skill_rank_for_level(16, skill_rank_thresholds=thresholds), "A")

    def test_state_engine_skill_rank_for_level_wrapper_preserves_contract(self) -> None:
        self.assertIn("skill_rank_for_level", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(state_engine.skill_rank_for_level(0), "-")

    def test_skill_ranks_next_skill_xp_for_level_preserves_formula(self) -> None:
        self.assertEqual(skill_ranks.next_skill_xp_for_level(0), 60)
        self.assertEqual(skill_ranks.next_skill_xp_for_level(1), 100)
        self.assertEqual(skill_ranks.next_skill_xp_for_level(3), 170)

    def test_state_engine_next_skill_xp_for_level_wrapper_preserves_contract(self) -> None:
        self.assertIn("next_skill_xp_for_level", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(state_engine.next_skill_xp_for_level(2), 135)

    def test_skill_ranks_normalize_skill_rank_uppercases_and_defaults(self) -> None:
        self.assertEqual(skill_ranks.normalize_skill_rank(" c ", skill_ranks=("F", "C")), "C")
        self.assertEqual(skill_ranks.normalize_skill_rank("x", skill_ranks=("F", "C")), "F")

    def test_state_engine_normalize_skill_rank_wrapper_preserves_contract(self) -> None:
        self.assertIn("normalize_skill_rank", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(state_engine.normalize_skill_rank("s"), "S")

    def test_skill_state_normalize_growth_potential_defaults_invalid_values(self) -> None:
        self.assertEqual(skill_state.normalize_growth_potential(" HOCH "), "hoch")
        self.assertEqual(skill_state.normalize_growth_potential("legendär"), "legendär")
        self.assertEqual(skill_state.normalize_growth_potential("mythisch"), "mittel")
        self.assertEqual(skill_state.normalize_growth_potential(""), "mittel")

    def test_state_engine_dynamic_skill_uses_extracted_growth_potential_normalizer(self) -> None:
        skill = state_engine.normalize_dynamic_skill_state({"name": "Funkenwurf", "growth_potential": "mythisch"})

        self.assertEqual(skill["growth_potential"], "mittel")

    def test_skill_state_normalize_cooldown_turns_preserves_none_and_bounds(self) -> None:
        self.assertIsNone(skill_state.normalize_cooldown_turns(None))
        self.assertIsNone(skill_state.normalize_cooldown_turns(""))
        self.assertEqual(skill_state.normalize_cooldown_turns("-2"), 0)
        self.assertEqual(skill_state.normalize_cooldown_turns("3"), 3)

    def test_state_engine_dynamic_skill_uses_extracted_cooldown_normalizer(self) -> None:
        skill = state_engine.normalize_dynamic_skill_state({"name": "Funkenwurf", "cooldown_turns": "-2"})

        self.assertEqual(skill["cooldown_turns"], 0)

    def test_skill_state_normalize_skill_element_fields_dedupes_and_inserts_primary(self) -> None:
        elements, primary = skill_state.normalize_skill_element_fields([" fire ", "water", "fire", ""], " air ")

        self.assertEqual(elements, ["air", "fire", "water"])
        self.assertEqual(primary, "air")

    def test_state_engine_dynamic_skill_uses_extracted_element_field_normalizer(self) -> None:
        skill = state_engine.normalize_dynamic_skill_state(
            {"name": "Funkenwurf", "elements": ["fire", "water", "fire"], "element_primary": "air"}
        )

        self.assertEqual(skill["elements"], ["air", "fire", "water"])
        self.assertEqual(skill["element_primary"], "air")

    def test_skill_state_normalize_optional_unique_strings_dedupes_or_returns_none(self) -> None:
        self.assertEqual(skill_state.normalize_optional_unique_strings([" a ", "b", "a", ""]), ["a", "b"])
        self.assertIsNone(skill_state.normalize_optional_unique_strings(["", "  "]))

    def test_state_engine_dynamic_skill_uses_extracted_synergy_normalizer(self) -> None:
        skill = state_engine.normalize_dynamic_skill_state(
            {"name": "Funkenwurf", "element_synergies": [" fire ", "water", "fire", ""]}
        )

        self.assertEqual(skill["element_synergies"], ["fire", "water"])

    def test_skill_state_normalize_optional_strings_preserves_duplicates(self) -> None:
        self.assertEqual(skill_state.normalize_optional_strings([" a ", "a", "", "b"]), ["a", "a", "b"])
        self.assertIsNone(skill_state.normalize_optional_strings(["", "  "]))

    def test_state_engine_dynamic_skill_uses_extracted_class_affinity_normalizer(self) -> None:
        skill = state_engine.normalize_dynamic_skill_state(
            {"name": "Funkenwurf", "class_affinity": [" mage ", "mage", ""]}
        )

        self.assertEqual(skill["class_affinity"], ["mage", "mage"])

    def test_skill_state_normalize_optional_text_strips_or_returns_none(self) -> None:
        self.assertEqual(skill_state.normalize_optional_text(" Story "), "Story")
        self.assertIsNone(skill_state.normalize_optional_text(""))

    def test_state_engine_dynamic_skill_uses_extracted_optional_text_normalizer(self) -> None:
        skill = state_engine.normalize_dynamic_skill_state(
            {"name": "Funkenwurf", "manifestation_source": " Story ", "synergy_notes": " Kombiniert "}
        )

        self.assertEqual(skill["manifestation_source"], "Story")
        self.assertEqual(skill["synergy_notes"], "Kombiniert")

    def test_skill_state_normalize_optional_lower_text_strips_lowercases_or_returns_none(self) -> None:
        self.assertEqual(skill_state.normalize_optional_lower_text(" Aktiv "), "aktiv")
        self.assertIsNone(skill_state.normalize_optional_lower_text(""))

    def test_state_engine_dynamic_skill_uses_extracted_category_normalizer(self) -> None:
        skill = state_engine.normalize_dynamic_skill_state({"name": "Funkenwurf", "category": " Aktiv "})

        self.assertEqual(skill["category"], "aktiv")

    def test_skill_state_normalize_power_rating_uses_fallback_and_bounds(self) -> None:
        self.assertEqual(
            skill_state.normalize_power_rating(
                None,
                rank="C",
                level=2,
                skill_rank_sort_value=lambda rank: {"F": 0, "C": 3}.get(rank, 0),
                clamp=lambda value, low, high: max(low, min(high, int(value))),
            ),
            22,
        )
        self.assertEqual(
            skill_state.normalize_power_rating(
                2000,
                rank="F",
                level=1,
                skill_rank_sort_value=lambda _rank: 0,
                clamp=lambda value, low, high: max(low, min(high, int(value))),
            ),
            999,
        )

    def test_state_engine_dynamic_skill_uses_extracted_power_rating_normalizer(self) -> None:
        skill = state_engine.normalize_dynamic_skill_state({"name": "Funkenwurf", "rank": "C", "level": 2})

        self.assertEqual(skill["power_rating"], 5)

    def test_skill_state_normalize_skill_progression_fields_caps_xp_and_mastery(self) -> None:
        xp, next_xp, mastery = skill_state.normalize_skill_progression_fields(
            {"level": 2, "xp": 500, "next_xp": 120},
            next_skill_xp_for_level=lambda level: 100 + level,
            clamp=lambda value, low, high: max(low, min(high, int(value))),
        )

        self.assertEqual((xp, next_xp, mastery), (120, 120, 100))

    def test_state_engine_dynamic_skill_uses_extracted_progression_normalizer(self) -> None:
        skill = state_engine.normalize_dynamic_skill_state({"name": "Funkenwurf", "level": 2, "xp": 500, "next_xp": 120})

        self.assertEqual(skill["xp"], 120)
        self.assertEqual(skill["next_xp"], 120)
        self.assertEqual(skill["mastery"], 0)

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

    def test_injury_state_defaults_preserve_state_engine_contract(self) -> None:
        self.assertIn("default_injury_state", state_engine.EXPORTED_SYMBOLS)
        self.assertIn("default_scar_state", state_engine.EXPORTED_SYMBOLS)
        self.assertIs(state_engine.default_injury_state, injury_state.default_injury_state)
        self.assertIs(state_engine.default_scar_state, injury_state.default_scar_state)
        self.assertEqual(
            state_engine.default_injury_state(),
            {
                "id": "",
                "title": "",
                "severity": "leicht",
                "effects": [],
                "healing_stage": "frisch",
                "will_scar": False,
                "created_turn": 0,
                "notes": "",
            },
        )
        self.assertEqual(
            state_engine.default_scar_state(),
            {
                "id": "",
                "title": "",
                "origin_injury_id": None,
                "description": "",
                "created_turn": 0,
            },
        )

    def test_injury_state_normalize_injury_state_preserves_valid_shape(self) -> None:
        payload = {
            "id": "inj_1",
            "title": "Schnittwunde",
            "severity": "SCHWER",
            "effects": [" Blutung ", "", "Schmerz"],
            "healing_stage": "heilend",
            "will_scar": 1,
            "created_turn": "3",
            "notes": "  verbunden ",
        }

        self.assertEqual(
            injury_state.normalize_injury_state(payload),
            {
                "id": "inj_1",
                "title": "Schnittwunde",
                "severity": "schwer",
                "effects": ["Blutung", "Schmerz"],
                "healing_stage": "heilend",
                "will_scar": True,
                "created_turn": 3,
                "notes": "verbunden",
            },
        )

    def test_state_engine_normalize_injury_state_wrapper_preserves_contract(self) -> None:
        self.assertIn("normalize_injury_state", state_engine.EXPORTED_SYMBOLS)
        self.assertIs(state_engine.normalize_injury_state, injury_state.normalize_injury_state)
        self.assertIsNone(state_engine.normalize_injury_state({}))
        self.assertEqual(
            state_engine.normalize_injury_state(
                {"title": "Prellung", "severity": "falsch", "healing_stage": "unknown"}
            ),
            {
                "id": "inj_test",
                "title": "Prellung",
                "severity": "leicht",
                "effects": [],
                "healing_stage": "frisch",
                "will_scar": False,
                "created_turn": 0,
                "notes": "",
            },
        )

    def test_injury_state_normalize_scar_state_preserves_valid_shape(self) -> None:
        payload = {
            "id": "scar_1",
            "label": "Wangenriss",
            "origin_injury_id": " inj_1 ",
            "source": "Duell",
            "turn_number": "4",
        }

        self.assertEqual(
            injury_state.normalize_scar_state(payload),
            {
                "id": "scar_1",
                "title": "Wangenriss",
                "origin_injury_id": "inj_1",
                "description": "Duell",
                "created_turn": 4,
                "label": "Wangenriss",
                "source": "Duell",
                "turn_number": "4",
            },
        )

    def test_state_engine_normalize_scar_state_wrapper_preserves_contract(self) -> None:
        self.assertIn("normalize_scar_state", state_engine.EXPORTED_SYMBOLS)
        self.assertIs(state_engine.normalize_scar_state, injury_state.normalize_scar_state)
        self.assertIsNone(state_engine.normalize_scar_state({}))
        self.assertEqual(
            state_engine.normalize_scar_state({"title": "Brandmal"}),
            {
                "id": "scar_test",
                "title": "Brandmal",
                "origin_injury_id": None,
                "description": "Brandmal",
                "created_turn": 0,
            },
        )

    def test_appearance_format_message_by_kind(self) -> None:
        self.assertEqual(
            appearance.format_appearance_message("Mira", "scar_added", "scar", "Wangenriss"),
            "Mira trägt nun eine neue Narbe: Wangenriss.",
        )
        self.assertEqual(
            appearance.format_appearance_message("Mira", "unknown", "x", "leuchtet"),
            "Miras Erscheinung verändert sich: leuchtet.",
        )

    def test_appearance_default_profile_preserves_state_engine_contract(self) -> None:
        self.assertIn("default_appearance_profile", state_engine.EXPORTED_SYMBOLS)
        self.assertIs(state_engine.default_appearance_profile, appearance.default_appearance_profile)
        self.assertEqual(
            state_engine.default_appearance_profile(),
            {
                "height": "average",
                "build": "neutral",
                "muscle": 0,
                "fat": 0,
                "scars": [],
                "aura": "none",
                "eyes": {
                    "base": "",
                    "current": "",
                },
                "hair": {
                    "color": "",
                    "style": "",
                    "current": "",
                },
                "skin_marks": [],
                "voice_tone": "",
                "visual_modifiers": [],
                "summary_short": "",
                "summary_full": "",
            },
        )

    def test_character_state_default_modifiers_preserve_state_engine_contract(self) -> None:
        self.assertIn("default_character_modifiers", state_engine.EXPORTED_SYMBOLS)
        self.assertIs(state_engine.default_character_modifiers, state_defaults.default_character_modifiers)
        self.assertEqual(
            state_engine.default_character_modifiers(),
            {
                "resource_max": [],
                "derived": [],
                "appearance_flags": [],
                "skill_effective": [],
            },
        )

    def test_time_state_default_world_time_preserves_state_engine_contract(self) -> None:
        self.assertIn("default_world_time", state_engine.EXPORTED_SYMBOLS)
        self.assertIs(state_engine.default_world_time, state_defaults.default_world_time)
        self.assertEqual(
            state_engine.default_world_time(),
            {
                "day": 1,
                "month": 1,
                "year": 1,
                "time_of_day": "night",
                "weather": "",
                "absolute_day": 1,
            },
        )

    def test_progression_default_class_current_preserves_state_engine_contract(self) -> None:
        self.assertIn("default_class_current", state_engine.EXPORTED_SYMBOLS)
        self.assertIs(state_engine.default_class_current, progression.default_class_current)
        self.assertEqual(
            state_engine.default_class_current(),
            {
                "id": "",
                "name": "",
                "rank": "F",
                "path_id": "",
                "path_rank": "F",
                "element_id": "",
                "element_tags": [],
                "level": 1,
                "level_max": 10,
                "xp": 0,
                "xp_next": 100,
                "class_id": "",
                "class_name": "",
                "class_rank": "F",
                "class_level": 1,
                "class_level_max": 10,
                "class_xp": 0,
                "class_xp_to_next": 100,
                "affinity_tags": [],
                "description": "",
                "class_traits": [],
                "class_mastery": 0,
                "ascension": {
                    "status": "none",
                    "quest_id": None,
                    "requirements": [],
                    "result_hint": None,
                },
            },
        )

    def test_intro_state_default_preserves_state_engine_contract(self) -> None:
        self.assertIn("default_intro_state", state_engine.EXPORTED_SYMBOLS)
        self.assertIs(state_engine.default_intro_state, state_defaults.default_intro_state)
        self.assertEqual(
            state_engine.default_intro_state(),
            {
                "status": "idle",
                "last_error": "",
                "last_attempt_at": "",
                "generated_turn_id": "",
            },
        )

    def test_state_engine_format_appearance_message_wrapper_preserves_contract(self) -> None:
        self.assertIn("format_appearance_message", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(
            state_engine.format_appearance_message("Mira", "aging_stage", "age_stage", "älter"),
            "Mira wirkt nun deutlich älter.",
        )

    def test_appearance_event_id_is_stable_and_prefixed(self) -> None:
        event_id = appearance.appearance_event_id("slot_1", "scar_added", "scar", 3, 10, "Wangenriss")

        self.assertTrue(event_id.startswith("app_"))
        self.assertEqual(event_id, appearance.appearance_event_id("slot_1", "scar_added", "scar", 3, 10, "Wangenriss"))

    def test_state_engine_appearance_event_id_wrapper_preserves_contract(self) -> None:
        self.assertIn("appearance_event_id", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(
            state_engine.appearance_event_id("slot_1", "scar_added", "scar", 3, 10, "Wangenriss"),
            appearance.appearance_event_id("slot_1", "scar_added", "scar", 3, 10, "Wangenriss"),
        )

    def test_appearance_record_change_appends_once(self) -> None:
        character = {"bio": {"name": "Mira"}}

        event = appearance.record_appearance_change(
            character,
            slot_name="slot_1",
            turn_number=3,
            absolute_day=10,
            kind="scar_added",
            source="scar",
            old_value="",
            new_value="Wangenriss",
        )
        duplicate = appearance.record_appearance_change(
            character,
            slot_name="slot_1",
            turn_number=3,
            absolute_day=10,
            kind="scar_added",
            source="scar",
            old_value="",
            new_value="Wangenriss",
        )

        self.assertIsNotNone(event)
        self.assertIsNone(duplicate)
        self.assertEqual(len(character["appearance_history"]), 1)

    def test_state_engine_record_appearance_change_wrapper_preserves_contract(self) -> None:
        character = {"bio": {"name": "Mira"}}

        event = state_engine.record_appearance_change(
            character,
            slot_name="slot_1",
            turn_number=3,
            absolute_day=10,
            kind="aging_stage",
            source="age_stage",
            old_value="jung",
            new_value="älter",
        )

        self.assertIn("record_appearance_change", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(event["message"], "Mira wirkt nun deutlich älter.")

    def test_appearance_active_faction_ids_filters_inactive_entries(self) -> None:
        factions = appearance.active_faction_ids(
            {
                "faction_memberships": [
                    {"faction_id": "guild", "active": True},
                    {"faction_id": "cult", "active": False},
                    {"faction_id": "order"},
                ]
            }
        )

        self.assertEqual(factions, {"guild", "order"})

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

    def test_element_relation_lookup_helper_returns_normalized_relation(self) -> None:
        world = {"element_relations": {"elem_fire": {"elem_water": " Strong "}}}

        relation = element_relations.resolve_element_relation(
            world,
            " elem_fire ",
            " elem_water ",
            normalize_element_relation=lambda value: element_relations.normalize_element_relation(
                value,
                element_relations={"neutral", "strong"},
            ),
        )

        self.assertEqual(relation, "strong")
        self.assertEqual(
            element_relations.get_element_relation(
                {},
                "elem_fire",
                "elem_water",
                normalize_element_relation=lambda value: element_relations.normalize_element_relation(
                    value,
                    element_relations={"neutral", "strong"},
                ),
            ),
            "neutral",
        )

    def test_state_engine_element_relation_lookup_wrappers_preserve_contract(self) -> None:
        world = {"element_relations": {"elem_fire": {"elem_water": "dominant"}}}

        self.assertIn("resolve_element_relation", state_engine.EXPORTED_SYMBOLS)
        self.assertIn("get_element_relation", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(state_engine.resolve_element_relation(world, "elem_fire", "elem_water"), "dominant")
        self.assertEqual(state_engine.get_element_relation(world, "elem_fire", "missing"), "neutral")

    def test_element_relation_profile_projection_reflects_strengths_and_weaknesses(self) -> None:
        elements = {"elem_fire": {"name": "Feuer"}, "elem_water": {"name": "Wasser"}, "elem_air": {"name": "Luft"}}

        element_relations.reflect_element_relation_profile_fields(
            elements,
            {
                "elem_fire": {"elem_fire": "dominant", "elem_water": "strong", "elem_air": "countered"},
                "elem_water": {"elem_fire": "weak"},
            },
            normalize_element_relation=lambda value: element_relations.normalize_element_relation(
                value,
                element_relations={"neutral", "strong", "weak", "dominant", "countered"},
            ),
        )

        self.assertEqual(elements["elem_fire"]["strengths_against"], ["elem_water"])
        self.assertEqual(elements["elem_fire"]["weaknesses_against"], ["elem_air"])
        self.assertEqual(elements["elem_water"]["weaknesses_against"], ["elem_fire"])

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

    def test_element_relations_generation_applies_profile_hints(self) -> None:
        elements = {
            "elem_a": {"name": "A", "strengths_against": ["B"], "synergies_with": ["C"]},
            "elem_b": {"name": "B", "weaknesses_against": ["A"]},
            "elem_c": {"name": "C"},
        }

        relations = element_relations.generate_element_relations(
            elements,
            build_default_element_relations=element_relations.build_default_element_relations,
            apply_element_anchor_relation_rules=lambda _elements, _relations: None,
            normalize_codex_alias_text=lambda value: str(value or "").strip().lower(),
            set_element_relation=lambda rels, source, target, relation: rels[source].__setitem__(target, relation),
            normalize_element_relations=lambda rels, _elements: rels,
        )

        self.assertEqual(relations["elem_a"]["elem_b"], "strong")
        self.assertEqual(relations["elem_a"]["elem_c"], "strong")
        self.assertEqual(relations["elem_b"]["elem_a"], "weak")

    def test_state_engine_generate_element_relations_wrapper_preserves_contract(self) -> None:
        relations = state_engine.generate_element_relations(
            {
                "elem_fire": {"name": "Feuer", "strengths_against": ["Wasser"]},
                "elem_water": {"name": "Wasser"},
            }
        )

        self.assertEqual(relations["elem_fire"]["elem_water"], "strong")
        self.assertEqual(relations["elem_water"]["elem_fire"], "strong")

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

    def test_element_generation_fallback_builds_six_distinct_candidates(self) -> None:
        candidates = element_generation.generate_world_elements_fallback(
            {"theme": "Wald", "tone": "dunkel", "premise": "Rituale"},
            deep_copy=copy.deepcopy,
            element_generated_names_fallback=["A", "B", "C", "D", "E", "F", "G"],
            pick_world_theme_anchor=lambda _summary: "Wald",
            generated_element_too_similar=lambda _candidate, _picked: (False, ""),
        )

        self.assertEqual(len(candidates), 6)
        self.assertEqual(len({candidate["name"] for candidate in candidates}), 6)
        self.assertTrue(all(candidate["origin"] == "generated" for candidate in candidates))
        self.assertTrue(all(candidate["environment_bias"] == "Wald" for candidate in candidates))

    def test_state_engine_fallback_element_generation_wrapper_preserves_contract(self) -> None:
        candidates = state_engine.generate_world_elements_fallback(
            {"theme": "Nebel", "tone": "mystisch", "premise": "Grenzen"}
        )

        self.assertEqual(len(candidates), 6)
        self.assertTrue(all(candidate["origin"] == "generated" for candidate in candidates))
        self.assertTrue(all(candidate["status_effect_tags"] for candidate in candidates))

    def test_element_generation_llm_normalizes_schema_rows(self) -> None:
        seen = {}

        def fake_schema(system, user, schema, **kwargs):
            seen["system"] = system
            seen["user"] = user
            seen["schema"] = schema
            seen["kwargs"] = kwargs
            return {
                "elements": [
                    {
                        "name": " Nebelglas ",
                        "rarity": "",
                        "description": "  Desc ",
                        "theme": " Täuschung ",
                        "status_effect_tags": [" Blind ", ""],
                        "class_affinities": [" Illusion "],
                        "skill_affinities": [" Schleier "],
                        "lore_notes": [" Notiz "],
                        "visual_motif": " Glas ",
                        "temperament": "still",
                        "environment_bias": "Nebel",
                        "aliases": [" Glas "],
                    },
                    "bad",
                ]
            }

        rows = element_generation.generate_world_elements_with_llm(
            {"theme": "Nebel", "tone": "leise", "premise": "Schwelle"},
            call_ollama_schema=fake_schema,
            element_generator_schema={"type": "object"},
        )

        self.assertEqual(seen["kwargs"], {"timeout": 120, "temperature": 0.55})
        self.assertIn("Nebel", seen["user"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Nebelglas")
        self.assertEqual(rows[0]["rarity"], "ungewöhnlich")
        self.assertEqual(rows[0]["status_effect_tags"], ["Blind"])
        self.assertEqual(rows[0]["aliases"], ["Glas"])

    def test_state_engine_llm_element_generation_wrapper_preserves_patchable_call(self) -> None:
        original_call = state_engine.call_ollama_schema
        try:
            state_engine.call_ollama_schema = lambda *_args, **_kwargs: {"elements": [{"name": "Traum", "theme": "Schlaf"}]}
            rows = state_engine.generate_world_elements_with_llm({"theme": "Traum"})
        finally:
            state_engine.call_ollama_schema = original_call

        self.assertEqual(rows[0]["name"], "Traum")
        self.assertEqual(rows[0]["theme"], "Schlaf")
        self.assertEqual(rows[0]["origin"], "generated")

    def test_element_generation_profiles_combines_core_and_generated_candidates(self) -> None:
        summary = {}

        profiles = element_generation.generate_world_element_profiles(
            summary,
            element_total_count=8,
            element_id_from_name=lambda name: f"elem_{str(name).strip().lower()}",
            normalize_element_profile=lambda raw, **_kwargs: dict(raw),
            default_element_profile=lambda element_id, name, **_kwargs: {"id": element_id, "name": name},
            normalize_codex_alias_text=lambda value: str(value or "").strip().lower(),
            generate_world_elements_with_llm=lambda _summary: [
                {"name": "Traum", "theme": "Schlaf"},
                {"name": "Traum", "theme": "Schlaf"},
            ],
            generate_world_elements_fallback=lambda _summary: [{"name": "Nebel", "theme": "Dunst"}],
            generated_element_too_similar=lambda candidate, existing: (
                (True, "DUPLICATE_NAME") if any(item.get("name") == candidate.get("name") for item in existing) else (False, "")
            ),
            stable_sorted_mapping=lambda mapping, key_fn: dict(sorted(mapping.items(), key=key_fn)),
            element_sort_key=lambda item: item[0],
        )

        self.assertIn("elem_feuer", profiles)
        self.assertIn("elem_traum", profiles)
        self.assertIn("elem_nebel", profiles)
        self.assertIn("DUPLICATE_NAME", summary["_element_generation_notes"])
        self.assertLessEqual(len(profiles), 8)

    def test_state_engine_element_profile_generation_wrapper_preserves_contract(self) -> None:
        original_call = state_engine.call_ollama_schema
        try:
            state_engine.call_ollama_schema = lambda *_args, **_kwargs: {"elements": []}
            profiles = state_engine.generate_world_element_profiles({"theme": "Nebel"})
        finally:
            state_engine.call_ollama_schema = original_call

        self.assertEqual(len(profiles), 12)
        self.assertIn("elem_feuer", profiles)
        self.assertTrue(any(profile.get("origin") == "generated" for profile in profiles.values()))

    def test_element_class_path_name_helper_preserves_rank_suffixes(self) -> None:
        self.assertEqual(element_class_paths.next_element_path_name("Feuer", "F", 0), "Feuer-Novize")
        self.assertEqual(element_class_paths.next_element_path_name("Feuer", "F", 1), "Feuer-Student")
        self.assertEqual(element_class_paths.next_element_path_name("Feuer", "S", 2), "Feuer-Ultimus")
        self.assertEqual(state_engine.next_element_path_name("Feuer", "X", 0), "Feuer-Adept")

    def test_element_class_path_generation_builds_rank_nodes(self) -> None:
        paths = element_class_paths.generate_element_class_paths(
            {"elem_fire": {"name": "Feuer", "theme": "Hitze", "class_affinities": ["flamme"]}},
            {"theme": "Feuer", "tone": "hell", "premise": "Probe"},
            clamp=lambda value, low, high: max(low, min(high, value)),
            element_class_path_min=1,
            element_class_path_max=1,
            element_class_path_ranks=["F", "C"],
            normalize_codex_alias_text=lambda value: str(value or "").strip().lower(),
            skill_rank_sort_value=lambda rank: {"F": 0, "C": 3}.get(rank, 0),
            next_element_path_name=element_class_paths.next_element_path_name,
            stable_sorted_mapping=lambda mapping, key_fn: dict(sorted(mapping.items(), key=key_fn)),
        )

        rank_f = paths["elem_fire"][0]["ranks"]["F"]
        rank_c = paths["elem_fire"][0]["ranks"]["C"]
        self.assertEqual(rank_f["required_level"], 1)
        self.assertEqual(rank_c["required_level"], 10)
        self.assertEqual(rank_c["required_class_level"], 4)
        self.assertEqual(rank_f["skill_prefix"], "feuer")
        self.assertEqual(rank_f["required_affinity_tags"], ["feuer", "flamme"])

    def test_element_class_path_rank_node_normalizer_preserves_shape(self) -> None:
        node = element_class_paths.normalize_class_path_rank_node(
            {
                "name": " Feuer Adept ",
                "rank": "c",
                "required_affinity_tags": [" flamme ", "flamme", ""],
                "required_skills": ["Glut", " Glut "],
                "core_skills_required": [" Funke ", "Funke"],
                "core_skills_unlockable": [" Schild "],
                "signature_skills": [" Signatur "],
                "next_paths": [" path_next ", ""],
                "required_level": 0,
                "required_class_level": 2,
            },
            default_rank="F",
            element_id="elem_fire",
            path_id="path_fire_1",
            normalize_skill_rank=lambda value: str(value or "").strip().upper() if str(value or "").strip().upper() in {"F", "C"} else "F",
        )

        self.assertIsNotNone(node)
        self.assertEqual(node["id"], "path_fire_1_c")
        self.assertEqual(node["name"], "Feuer Adept")
        self.assertEqual(node["rank"], "C")
        self.assertEqual(node["element_id"], "elem_fire")
        self.assertEqual(node["required_level"], 1)
        self.assertEqual(node["required_class_level"], 2)
        self.assertEqual(node["required_affinity_tags"], ["flamme"])
        self.assertEqual(node["required_skills"], ["Glut"])
        self.assertEqual(node["core_skills_required"], ["Funke"])
        self.assertEqual(node["core_skills_unlockable"], ["Schild"])
        self.assertEqual(node["signature_skills"], ["Signatur"])
        self.assertEqual(node["next_paths"], ["path_next"])

    def test_state_engine_class_path_rank_node_wrapper_preserves_contract(self) -> None:
        node = state_engine.normalize_class_path_rank_node(
            {"name": "Feuer Adept", "core_skills_required": ["Funke"], "rank": "c"},
            default_rank="F",
            element_id="elem_fire",
            path_id="path_fire_1",
        )

        self.assertIsNotNone(node)
        self.assertEqual(node["rank"], "C")
        self.assertIsNone(
            state_engine.normalize_class_path_rank_node(
                {"name": "Feuer Adept"},
                default_rank="F",
                element_id="elem_fire",
                path_id="path_fire_1",
            )
        )

    def test_element_class_path_normalizer_preserves_valid_paths(self) -> None:
        ranks = {
            rank: {"name": f" Feuer {rank} ", "rank": rank.lower(), "core_skills_required": [f" Kern {rank} "]}
            for rank in ["F", "C"]
        }

        normalized = element_class_paths.normalize_element_class_paths(
            {"elem_fire": [{"id": " path_fire ", "name": " Feuer-Pfad ", "ranks": ranks}]},
            {"elem_fire": {"theme": "Hitze"}},
            {"theme": "Feuer"},
            generate_element_class_paths=lambda _elements, _summary: {"elem_fire": [{"id": "default_path"}]},
            element_class_path_max=2,
            element_class_path_ranks=["F", "C"],
            normalize_skill_rank=lambda value: str(value or "").strip().upper(),
            deep_copy=copy.deepcopy,
            stable_sorted_mapping=lambda mapping, key_fn: dict(sorted(mapping.items(), key=key_fn)),
        )

        path = normalized["elem_fire"][0]
        self.assertEqual(path["id"], "path_fire")
        self.assertEqual(path["name"], "Feuer-Pfad")
        self.assertEqual(path["signature_theme"], "Hitze")
        self.assertEqual(path["ranks"]["F"]["name"], "Feuer F")
        self.assertEqual(path["ranks"]["F"]["core_skills_required"], ["Kern F"])
        self.assertEqual(path["ranks"]["C"]["rank"], "C")

    def test_state_engine_element_class_path_normalizer_wrapper_preserves_contract(self) -> None:
        ranks = {
            rank: {"name": f"Feuer {rank}", "rank": rank.lower(), "core_skills_required": [f"Kern {rank}"]}
            for rank in state_engine.ELEMENT_CLASS_PATH_RANKS
        }

        normalized = state_engine.normalize_element_class_paths(
            {"elem_fire": [{"id": "path_fire", "name": "Feuer-Pfad", "ranks": ranks}]},
            {"elem_fire": {"name": "Feuer", "theme": "Hitze"}},
            {"theme": "Feuer"},
        )

        self.assertIn("normalize_element_class_paths", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(normalized["elem_fire"][0]["id"], "path_fire")
        self.assertEqual(normalized["elem_fire"][0]["ranks"]["F"]["rank"], "F")

    def test_element_class_path_class_element_resolver_prefers_existing_id(self) -> None:
        resolved = element_class_paths.resolve_class_element_id(
            {"element_id": " elem_fire ", "element_tags": ["wasser"], "name": "Wasser"},
            {"elements": {"elem_fire": {}, "elem_water": {}}},
            normalize_class_current=lambda value: value,
            normalize_element_id_list=lambda values, _world: ["elem_water"] if values == ["wasser"] else [],
        )

        self.assertEqual(resolved, "elem_fire")

    def test_state_engine_class_element_resolver_wrapper_preserves_contract(self) -> None:
        world = {
            "elements": {"elem_fire": {"name": "Feuer"}},
            "element_alias_index": {"feuer": ["elem_fire"]},
        }

        resolved = state_engine.resolve_class_element_id(
            {"name": "Feuerklasse", "element_tags": ["Feuer"]},
            world,
        )

        self.assertIn("resolve_class_element_id", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(resolved, "elem_fire")

    def test_element_id_list_normalizer_uses_aliases_and_dedupes(self) -> None:
        normalized = element_ids.normalize_element_id_list(
            ["Feuer", "elem_water", "Feuer", "", "Unknown"],
            {
                "elements": {"elem_fire": {}, "elem_water": {}},
                "element_alias_index": {"feuer": ["elem_fire"]},
            },
            normalize_codex_alias_text=lambda value: str(value or "").strip().lower(),
            element_id_from_name=lambda name: f"elem_{str(name or '').strip().lower()}",
        )

        self.assertEqual(normalized, ["elem_fire", "elem_water"])

    def test_state_engine_element_id_list_wrapper_preserves_contract(self) -> None:
        world = {
            "elements": {"elem_fire": {"name": "Feuer"}, "elem_water": {"name": "Wasser"}},
            "element_alias_index": {"feuer": ["elem_fire"]},
        }

        normalized = state_engine.normalize_element_id_list(["Feuer", "elem_water", "Feuer"], world)

        self.assertIn("normalize_element_id_list", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(normalized, ["elem_fire", "elem_water"])

    def test_element_skill_normalizer_prefers_primary_element(self) -> None:
        normalized = element_skills.normalize_skill_elements_for_world(
            {
                "id": "skill_fire",
                "elements": ["wasser"],
                "element_primary": "feuer",
                "element_synergies": ["luft"],
            },
            {"elements": {"elem_fire": {}, "elem_water": {}, "elem_air": {}}},
            deep_copy=copy.deepcopy,
            normalize_element_id_list=lambda values, _world: [
                {"feuer": "elem_fire", "wasser": "elem_water", "luft": "elem_air"}.get(value)
                for value in values
                if {"feuer": "elem_fire", "wasser": "elem_water", "luft": "elem_air"}.get(value)
            ],
        )

        self.assertEqual(normalized["elements"], ["elem_fire", "elem_water"])
        self.assertEqual(normalized["element_primary"], "elem_fire")
        self.assertEqual(normalized["element_synergies"], ["elem_air"])

    def test_state_engine_skill_element_normalizer_wrapper_preserves_contract(self) -> None:
        world = {
            "elements": {"elem_fire": {"name": "Feuer"}, "elem_water": {"name": "Wasser"}},
            "element_alias_index": {"feuer": ["elem_fire"], "wasser": ["elem_water"]},
        }

        normalized = state_engine.normalize_skill_elements_for_world(
            {"id": "skill_fire", "elements": ["Wasser"], "element_primary": "Feuer"},
            world,
        )

        self.assertIn("normalize_skill_elements_for_world", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(normalized["elements"], ["elem_fire", "elem_water"])
        self.assertEqual(normalized["element_primary"], "elem_fire")
        self.assertIsNone(normalized["element_synergies"])

    def test_element_entity_profiles_include_class_element_tags(self) -> None:
        mapping = {"feuer": "elem_fire", "wasser": "elem_water", "luft": "elem_air", "erde": "elem_earth"}

        def normalize_ids(values: Any, _world: Dict[str, Any]) -> List[str]:
            out = []
            for value in values:
                text = str(value or "").strip()
                resolved = text if text in mapping.values() else mapping.get(text.lower())
                if resolved:
                    out.append(resolved)
            return list(dict.fromkeys(out))

        profile = element_entities.entity_element_profile_for_character(
            {
                "element_affinities": ["wasser"],
                "element_resistances": ["luft"],
                "element_weaknesses": ["erde"],
                "class_current": {"element_tags": ["feuer"]},
            },
            {"elements": {value: {} for value in mapping.values()}},
            normalize_class_current=lambda value: value,
            resolve_class_element_id=lambda _klass, _world: "elem_fire",
            normalize_element_id_list=normalize_ids,
        )

        self.assertEqual(profile["affinities"], ["elem_water", "elem_fire"])
        self.assertEqual(profile["resistances"], ["elem_air"])
        self.assertEqual(profile["weaknesses"], ["elem_earth"])

    def test_state_engine_element_entity_profile_wrappers_preserve_contract(self) -> None:
        world = {
            "elements": {"elem_fire": {"name": "Feuer"}, "elem_water": {"name": "Wasser"}},
            "element_alias_index": {"feuer": ["elem_fire"], "wasser": ["elem_water"]},
        }

        profile = state_engine.entity_element_profile_for_npc(
            {
                "element_affinities": ["Wasser"],
                "class_current": {"name": "Feuerklasse", "element_tags": ["Feuer"]},
            },
            world,
        )

        self.assertIn("entity_element_profile_for_character", state_engine.EXPORTED_SYMBOLS)
        self.assertIn("entity_element_profile_for_npc", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(profile["affinities"], ["elem_water", "elem_fire"])

    def test_element_matchup_multiplier_averages_relation_and_explicit_tags(self) -> None:
        multiplier = element_entities.element_matchup_multiplier(
            {},
            {"affinities": ["elem_fire"]},
            {"affinities": ["elem_water"], "resistances": ["elem_fire"], "weaknesses": []},
            resolve_element_relation=lambda _world, _source, _target: "strong",
            element_relation_score={"strong": 1.2},
        )

        self.assertAlmostEqual(multiplier, 1.025)

    def test_state_engine_element_matchup_wrapper_preserves_contract(self) -> None:
        state_engine.configure({"ELEMENT_RELATION_SCORE": {"strong": 1.2}})
        world = {"element_relations": {"elem_fire": {"elem_water": "strong"}}}

        multiplier = state_engine.element_matchup_multiplier(
            world,
            {"affinities": ["elem_fire"]},
            {"affinities": ["elem_water"], "resistances": ["elem_fire"], "weaknesses": []},
        )

        self.assertIn("element_matchup_multiplier", state_engine.EXPORTED_SYMBOLS)
        self.assertAlmostEqual(multiplier, 1.025)

    def test_combat_skill_rank_power_weight_uses_normalized_rank(self) -> None:
        self.assertEqual(
            combat.skill_rank_power_weight(" a ", normalize_skill_rank=lambda value: str(value or "").strip().upper()),
            7,
        )
        self.assertEqual(
            combat.skill_rank_power_weight("unknown", normalize_skill_rank=lambda _value: "unknown"),
            1,
        )

    def test_state_engine_skill_rank_power_weight_wrapper_preserves_contract(self) -> None:
        self.assertIn("skill_rank_power_weight", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(state_engine.skill_rank_power_weight("s"), 9)
        self.assertEqual(state_engine.skill_rank_power_weight("unknown"), 1)

    def test_combat_character_score_applies_stats_skills_and_penalties(self) -> None:
        score = combat.compute_character_combat_score(
            {
                "level": 2,
                "attributes": {"str": 1, "dex": 1, "con": 1, "int": 1, "wis": 1, "luck": 1},
                "hp_current": 10,
                "hp_max": 10,
                "sta_current": 10,
                "sta_max": 10,
                "res_current": 10,
                "res_max": 10,
                "class_current": {"level": 2, "rank": "C"},
                "skills": {"fire": {"level": 2, "rank": "F"}},
                "injuries": [{"severity": "mittel"}],
                "conditions": ["burning", "slowed"],
            },
            normalize_class_current=lambda value: value,
            skill_rank_power_weight=lambda rank: {"F": 1, "C": 4}.get(rank, 1),
            normalize_dynamic_skill_state=lambda value, **_kwargs: value,
            resource_name_for_character=lambda _character, _settings: "Aether",
            normalize_injury_state=lambda value: value,
        )

        self.assertEqual(score, 61)

    def test_state_engine_character_combat_score_wrapper_preserves_contract(self) -> None:
        score = state_engine.compute_character_combat_score(
            {
                "level": 1,
                "hp_current": 10,
                "hp_max": 10,
                "sta_current": 10,
                "sta_max": 10,
                "res_current": 10,
                "res_max": 10,
            }
        )

        self.assertIn("compute_character_combat_score", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(score, 47)

    def test_combat_npc_score_uses_class_resources_and_skills(self) -> None:
        score = combat.compute_npc_combat_score(
            {
                "level": 2,
                "hp_current": 10,
                "hp_max": 10,
                "sta_current": 10,
                "sta_max": 10,
                "res_current": 10,
                "res_max": 10,
                "class_current": {"level": 2, "rank": "C"},
                "progression": {"resource_name": "Mana"},
                "skills": {"fire": {"level": 2, "rank": "F"}},
            },
            normalize_class_current=lambda value: value,
            skill_rank_power_weight=lambda rank: {"F": 1, "C": 4}.get(rank, 1),
            normalize_dynamic_skill_state=lambda value, **_kwargs: value,
            normalize_resource_name=lambda value, _default: str(value or "").strip(),
        )

        self.assertEqual(score, 66)

    def test_state_engine_npc_combat_score_wrapper_preserves_contract(self) -> None:
        score = state_engine.compute_npc_combat_score(
            {
                "level": 1,
                "hp_current": 10,
                "hp_max": 10,
                "sta_current": 10,
                "sta_max": 10,
                "res_current": 10,
                "res_max": 10,
            }
        )

        self.assertIn("compute_npc_combat_score", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(score, 47)

    def test_combat_scaling_context_filters_scene_and_gone_threats(self) -> None:
        state = {
            "world": {"settings": {}},
            "characters": {
                "slot_1": {"scene_id": "scene_a"},
                "slot_2": {"scene_id": "scene_a"},
                "slot_3": {"scene_id": "scene_b"},
            },
            "npc_codex": {},
        }

        context = combat.build_combat_scaling_context(
            state,
            "slot_1",
            compute_character_combat_score=lambda character, _settings: {"slot_1": 100, "slot_2": 50, "slot_3": 10}.get(character.get("score_key"), 100 if character is state["characters"]["slot_1"] else 50),
            compute_npc_combat_score=lambda npc, _settings: int(npc.get("score", 1)),
            entity_element_profile_for_character=lambda character, _world: {"affinities": [character.get("scene_id", "")], "resistances": [], "weaknesses": []},
            entity_element_profile_for_npc=lambda npc, _world: {"affinities": [npc.get("last_seen_scene_id", "")], "resistances": [], "weaknesses": []},
            element_matchup_multiplier=lambda _world, _attacker, _defender: 1.0,
            sorted_npc_codex_entries=lambda _state: [
                {"last_seen_scene_id": "scene_a", "score": 70},
                {"last_seen_scene_id": "scene_a", "score": 90, "status": "gone"},
                {"last_seen_scene_id": "scene_b", "score": 20},
            ],
        )

        self.assertEqual(context["actor_score"], 100)
        self.assertEqual(context["threat_score"], 60)
        self.assertEqual(context["threat_count"], 2)
        self.assertEqual(context["pressure"], "low")
        self.assertEqual(context["element_factor"], 1.0)
        self.assertEqual(context["element_affinities"], ["scene_a"])

    def test_state_engine_combat_scaling_context_wrapper_preserves_contract(self) -> None:
        context = state_engine.build_combat_scaling_context(
            {
                "world": {"settings": {}},
                "characters": {
                    "slot_1": {
                        "hp_current": 10,
                        "hp_max": 10,
                        "sta_current": 10,
                        "sta_max": 10,
                        "res_current": 10,
                        "res_max": 10,
                    }
                },
            },
            "slot_1",
        )

        self.assertIn("build_combat_scaling_context", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(context["actor_score"], 47)
        self.assertEqual(context["threat_count"], 0)
        self.assertEqual(context["pressure"], "medium")

    def test_combat_scaling_patch_helper_scales_negative_actor_deltas(self) -> None:
        patch = {"characters": {"slot_1": {"hp_delta": -10, "resources_delta": {"sta": -2, "res": 3}}}}

        updated, meta = combat.apply_combat_scaling_to_patch(
            patch,
            actor="slot_1",
            combat_context={"active": True},
            scaling_context={"pressure": "high", "element_factor": 1.0},
            action_type="combat",
            deep_copy=copy.deepcopy,
            blank_patch=state_engine.blank_patch,
        )

        self.assertTrue(meta["applied"])
        self.assertEqual(meta["effective_multiplier"], 1.28)
        self.assertEqual(updated["characters"]["slot_1"]["hp_delta"], -13)
        self.assertEqual(updated["characters"]["slot_1"]["resources_delta"]["sta"], -3)
        self.assertEqual(updated["characters"]["slot_1"]["resources_delta"]["res"], 3)
        self.assertEqual(patch["characters"]["slot_1"]["hp_delta"], -10)

    def test_state_engine_combat_scaling_patch_wrapper_preserves_contract(self) -> None:
        updated, meta = state_engine.apply_combat_scaling_to_patch(
            {"characters": {"slot_1": {"stamina_delta": -1}}},
            actor="slot_1",
            combat_context={"hinted": True},
            scaling_context={"pressure": "low", "element_factor": 1.0},
            action_type="combat",
        )

        self.assertIn("apply_combat_scaling_to_patch", state_engine.EXPORTED_SYMBOLS)
        self.assertTrue(meta["applied"])
        self.assertEqual(meta["effective_multiplier"], 0.82)
        self.assertEqual(updated["characters"]["slot_1"]["stamina_delta"], -1)

    def test_combat_context_inference_uses_meta_actor_flag_and_hints(self) -> None:
        context = combat.infer_combat_context(
            {
                "meta": {"combat": {"active": False, "phase": "collecting"}},
                "characters": {"slot_1": {"derived": {"combat_flags": {"in_combat": True}}}},
            },
            "slot_1",
            "combat",
            "Ein Angriff beginnt.",
            normalized_eval_text=lambda value: str(value or "").strip().lower(),
            normalize_combat_meta=lambda meta: dict((meta.get("combat") or {}), phase="collecting"),
            combat_narrative_hints=("angriff",),
        )

        self.assertTrue(context["active"])
        self.assertTrue(context["hinted"])
        self.assertTrue(context["actor_in_combat"])
        self.assertEqual(context["phase"], "collecting")
        self.assertEqual(context["action_type"], "combat")

    def test_state_engine_combat_context_inference_wrapper_preserves_contract(self) -> None:
        state_engine.configure({"COMBAT_NARRATIVE_HINTS": ("angriff",)})

        context = state_engine.infer_combat_context(
            {"meta": {}, "characters": {"slot_1": {"derived": {"combat_flags": {"in_combat": True}}}}},
            "slot_1",
            "combat",
            "Angriff",
        )

        self.assertIn("infer_combat_context", state_engine.EXPORTED_SYMBOLS)
        self.assertTrue(context["active"])
        self.assertTrue(context["hinted"])

    def test_combat_patch_signal_helper_detects_resource_and_effect_signals(self) -> None:
        self.assertTrue(combat.patch_has_combat_signal({"characters": {"slot_1": {"resources_delta": {"hp": -1}}}}))
        self.assertTrue(combat.patch_has_combat_signal({"characters": {"slot_1": {"effects_add": [{"category": "combat"}]}}}))
        self.assertFalse(combat.patch_has_combat_signal({"characters": {"slot_1": {"resources_delta": {"hp": 1}}}}))

    def test_state_engine_combat_patch_signal_wrapper_preserves_contract(self) -> None:
        self.assertIn("patch_has_combat_signal", state_engine.EXPORTED_SYMBOLS)
        self.assertTrue(state_engine.patch_has_combat_signal({"characters": {"slot_1": {"hp_delta": -1}}}))

    def test_combat_meta_normalizer_filters_queue_and_defaults(self) -> None:
        meta = {
            "combat": {
                "active": True,
                "combat_id": " cmb_1 ",
                "round": -2,
                "phase": "BROKEN",
                "participants": [" slot_1 ", ""],
                "action_queue": [
                    {"turn": 2, "actor": " slot_1 ", "action_type": "combat", "summary": " Hit ", "created_at": ""},
                    {"turn": 3, "actor": "", "action_type": "combat"},
                    {"turn": 4, "actor": "slot_2", "action_type": "invalid"},
                ],
            }
        }

        normalized = combat.normalize_combat_meta(
            meta,
            default_combat_meta=lambda: combat.default_combat_meta(utc_now=lambda: "now"),
            deep_copy=copy.deepcopy,
            action_types={"combat"},
            utc_now=lambda: "now",
        )

        self.assertTrue(normalized["active"])
        self.assertEqual(normalized["combat_id"], "cmb_1")
        self.assertEqual(normalized["round"], 0)
        self.assertEqual(normalized["phase"], "idle")
        self.assertEqual(normalized["participants"], ["slot_1"])
        self.assertEqual(normalized["action_queue"], [{"turn": 2, "actor": "slot_1", "action_type": "combat", "summary": "Hit", "created_at": "now"}])
        self.assertEqual(meta["combat"], normalized)

    def test_state_engine_combat_meta_wrappers_preserve_contract(self) -> None:
        state_engine.configure({"utc_now": lambda: "now", "ACTION_TYPES": {"combat"}})

        default_meta = state_engine.default_combat_meta()
        normalized = state_engine.normalize_combat_meta({"combat": {"action_queue": [{"actor": "slot_1", "action_type": "combat"}]}})

        self.assertIn("default_combat_meta", state_engine.EXPORTED_SYMBOLS)
        self.assertIn("normalize_combat_meta", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(default_meta["updated_at"], "now")
        self.assertEqual(normalized["action_queue"][0]["created_at"], "now")

    def test_attribute_influence_normalizer_filters_profile_and_clamps_bias(self) -> None:
        meta = {
            "attribute_influence": {
                "last_turn": -2,
                "last_actor": " slot_1 ",
                "last_profile": {
                    "primary_attributes": [" STR ", "bogus"],
                    "influence_tier": "HIGH",
                    "narrative_bias": [" quick ", ""],
                    "mechanical_bias": {"damage_taken_mult": 9.0, "cost_mult": 0.1},
                },
            }
        }

        normalized = attribute_influence.normalize_attribute_influence_meta(
            meta,
            default_attribute_influence_meta=attribute_influence.default_attribute_influence_meta,
            deep_copy=copy.deepcopy,
            attribute_keys=("str", "dex"),
            clamp_float=lambda value, low, high: max(low, min(high, float(value))),
        )

        self.assertEqual(normalized["last_turn"], 0)
        self.assertEqual(normalized["last_actor"], "slot_1")
        self.assertEqual(normalized["last_profile"]["primary_attributes"], ["str"])
        self.assertEqual(normalized["last_profile"]["influence_tier"], "high")
        self.assertEqual(normalized["last_profile"]["narrative_bias"], ["quick"])
        self.assertEqual(normalized["last_profile"]["mechanical_bias"]["damage_taken_mult"], 1.35)
        self.assertEqual(normalized["last_profile"]["mechanical_bias"]["cost_mult"], 0.65)
        self.assertEqual(meta["attribute_influence"], normalized)

    def test_state_engine_attribute_influence_wrappers_preserve_contract(self) -> None:
        normalized = state_engine.normalize_attribute_influence_meta(
            {"attribute_influence": {"last_profile": {"primary_attributes": ["str"], "mechanical_bias": {}}}}
        )

        self.assertIn("default_attribute_influence_meta", state_engine.EXPORTED_SYMBOLS)
        self.assertIn("normalize_attribute_influence_meta", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(state_engine.default_attribute_influence_meta()["last_profile"]["influence_tier"], "none")
        self.assertEqual(normalized["last_profile"]["primary_attributes"], ["str"])

    def test_attribute_influence_derive_relevance_scores_action_context(self) -> None:
        profile = attribute_influence.derive_attribute_relevance(
            {"meta": {"turn": 2}, "characters": {"slot_1": {"attributes": {"str": 2, "dex": 6, "luck": 7}}}},
            "slot_1",
            "story",
            "Ein zufällig präzise Sprung gelingt.",
            {"active": True},
            normalized_eval_text=lambda value: str(value or "").lower(),
            hash_unit_interval=lambda _seed: 0.2,
            attribute_keys=("str", "dex", "con", "int", "wis", "cha", "luck"),
            attribute_influence_distribution=(("none", 0.1), ("low", 0.3), ("medium", 0.4), ("high", 0.2)),
        )

        self.assertEqual(profile["primary_attributes"], ["luck", "dex"])
        self.assertEqual(profile["influence_tier"], "low")
        self.assertEqual(profile["narrative_bias"][:2], ["fortunate_timing", "tempo_shift"])
        self.assertTrue(profile["combat_active"])

    def test_state_engine_derive_attribute_relevance_wrapper_preserves_contract(self) -> None:
        profile = state_engine.derive_attribute_relevance(
            {"meta": {"turn": 1}, "characters": {"slot_1": {"attributes": {"cha": 8}}}},
            "slot_1",
            "say",
            "Ich verhandle ruhig.",
        )

        self.assertIn("derive_attribute_relevance", state_engine.EXPORTED_SYMBOLS)
        self.assertIn("primary_attributes", profile)
        self.assertIn("influence_tier", profile)

    def test_attribute_influence_compute_bias_uses_primary_attributes(self) -> None:
        bias = attribute_influence.compute_attribute_bias(
            {"influence_tier": "high", "primary_attributes": ["str", "luck"]},
            {"attributes": {"str": 10, "luck": 2}},
            attribute_keys=("str", "luck"),
            attribute_influence_strength={"high": 1.0},
            clamp=lambda value, low, high: max(low, min(high, int(value))),
            clamp_float=lambda value, low, high: max(low, min(high, float(value))),
        )

        self.assertGreater(bias["outgoing_effect_mult"], 1.0)
        self.assertGreater(bias["complication_mult"], 1.0)
        self.assertLess(bias["damage_taken_mult"], 1.0)

    def test_state_engine_compute_attribute_bias_wrapper_preserves_contract(self) -> None:
        bias = state_engine.compute_attribute_bias(
            {"influence_tier": "none", "primary_attributes": ["str"]},
            {"attributes": {"str": 10}},
        )

        self.assertIn("compute_attribute_bias", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(bias["damage_taken_mult"], 1.0)
        self.assertEqual(bias["outgoing_effect_mult"], 1.0)

    def test_attribute_influence_compose_prompt_hints_formats_bias(self) -> None:
        text = attribute_influence.compose_attribute_prompt_hints(
            {"primary_attributes": ["str", "luck"], "narrative_bias": ["force_spike"], "influence_tier": "high"},
            {"damage_taken_mult": 0.9, "cost_mult": 1.0, "complication_mult": 1.1, "outgoing_effect_mult": 1.2},
        )

        self.assertIn("ATTRIBUTE INFLUENCE:", text)
        self.assertIn("- primary_attributes=STR, LUCK", text)
        self.assertIn("- influence_tier=high", text)
        self.assertIn("- mechanical_bias.outgoing_effect_mult=1.20", text)

    def test_state_engine_compose_attribute_prompt_hints_wrapper_preserves_contract(self) -> None:
        text = state_engine.compose_attribute_prompt_hints({"primary_attributes": []}, {})

        self.assertIn("compose_attribute_prompt_hints", state_engine.EXPORTED_SYMBOLS)
        self.assertIn("- primary_attributes=LUCK", text)

    def test_attribute_influence_apply_bias_to_resolution_scales_fields(self) -> None:
        resolution = {"damage_taken": 10, "cost": 6, "complication": 5, "outgoing_effect": 4, "note": "keep"}

        adjusted = attribute_influence.apply_attribute_bias_to_resolution(
            resolution,
            {"damage_taken_mult": 0.5, "cost_mult": 1.5, "complication_mult": 2.0, "outgoing_effect_mult": 1.25},
            deep_copy=copy.deepcopy,
        )

        self.assertEqual(adjusted["damage_taken"], 5)
        self.assertEqual(adjusted["cost"], 9)
        self.assertEqual(adjusted["complication"], 10)
        self.assertEqual(adjusted["outgoing_effect"], 5)
        self.assertEqual(adjusted["note"], "keep")
        self.assertEqual(resolution["damage_taken"], 10)

    def test_state_engine_apply_attribute_bias_to_resolution_wrapper_preserves_contract(self) -> None:
        adjusted = state_engine.apply_attribute_bias_to_resolution({"cost": 4}, {"cost_mult": 2.0})

        self.assertIn("apply_attribute_bias_to_resolution", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(adjusted["cost"], 8)

    def test_attribute_influence_scale_negative_delta_preserves_positive_and_min_negative(self) -> None:
        self.assertEqual(attribute_influence.scale_negative_delta(5, 3.0), 5)
        self.assertEqual(attribute_influence.scale_negative_delta(-10, 0.5), -5)
        self.assertEqual(attribute_influence.scale_negative_delta(-1, 0.1), -1)

    def test_state_engine_scale_negative_delta_wrapper_preserves_contract(self) -> None:
        self.assertIn("_scale_negative_delta", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(state_engine._scale_negative_delta(-4, 2.0), -8)

    def test_attribute_influence_apply_bias_to_patch_scales_actor_deltas(self) -> None:
        patch = {
            "characters": {
                "slot_1": {
                    "hp_delta": -10,
                    "stamina_delta": -4,
                    "resources_delta": {"hp": -2, "sta": -3, "res": -5, "gold": -9},
                }
            }
        }

        adjusted, applied = attribute_influence.apply_attribute_bias_to_patch(
            patch,
            "slot_1",
            {"damage_taken_mult": 0.5, "cost_mult": 2.0},
            deep_copy=copy.deepcopy,
            blank_patch=state_engine.blank_patch,
        )

        actor_patch = adjusted["characters"]["slot_1"]
        self.assertEqual(actor_patch["hp_delta"], -5)
        self.assertEqual(actor_patch["stamina_delta"], -8)
        self.assertEqual(actor_patch["resources_delta"]["hp"], -1)
        self.assertEqual(actor_patch["resources_delta"]["sta"], -6)
        self.assertEqual(actor_patch["resources_delta"]["res"], -10)
        self.assertEqual(actor_patch["resources_delta"]["gold"], -9)
        self.assertEqual(applied, {"hp_delta": 6, "stamina_delta": -7, "res_delta": -5})
        self.assertEqual(patch["characters"]["slot_1"]["hp_delta"], -10)

    def test_state_engine_apply_attribute_bias_to_patch_wrapper_preserves_contract(self) -> None:
        adjusted, applied = state_engine.apply_attribute_bias_to_patch(
            {"characters": {"slot_1": {"hp_delta": -4}}},
            "slot_1",
            {"damage_taken_mult": 2.0},
        )

        self.assertIn("apply_attribute_bias_to_patch", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(adjusted["characters"]["slot_1"]["hp_delta"], -8)
        self.assertEqual(applied, {"hp_delta": -4})

    def test_skill_costs_infer_deltas_from_combat_text(self) -> None:
        state = {
            "characters": {
                "slot_1": {
                    "skills": {
                        "s1": {"name": "Flammen Stoß", "cost": {"resource": "Stamina", "amount": 3}},
                        "s2": {"name": "Nebelgriff", "cost": {"resource": "Aether", "amount": 2}},
                    }
                }
            },
            "world": {"settings": {"resource_name": "Aether"}},
        }

        payload = skill_costs.infer_skill_cost_deltas_from_text(
            state,
            "slot_1",
            "combat",
            "Sie nutzt Flammen Stoß und aktiviert Nebelgriff.",
            combat_context={"active": True},
            resource_name_for_character=lambda _character, _settings: "Aether",
            normalized_eval_text=lambda value: str(value or "").lower(),
            normalize_dynamic_skill_state=lambda skill, **_kwargs: dict(skill),
        )

        self.assertEqual(payload["deltas"], {"sta": -3, "res": -2})
        self.assertEqual(payload["skills"], ["Flammen Stoß", "Nebelgriff"])

    def test_state_engine_infer_skill_cost_deltas_wrapper_preserves_contract(self) -> None:
        payload = state_engine.infer_skill_cost_deltas_from_text({}, "slot_1", "canon", "nutzt etwas")

        self.assertIn("infer_skill_cost_deltas_from_text", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(payload, {"deltas": {}, "skills": []})

    def test_skill_costs_apply_deltas_to_patch_merges_resources(self) -> None:
        patch = {"characters": {"slot_1": {"resources_delta": {"sta": -1}}}}

        adjusted = skill_costs.apply_skill_cost_deltas_to_patch(
            patch,
            "slot_1",
            {"deltas": {"sta": -3, "res": -2}},
            deep_copy=copy.deepcopy,
            blank_patch=state_engine.blank_patch,
        )

        self.assertEqual(adjusted["characters"]["slot_1"]["resources_delta"], {"sta": -4, "res": -2})
        self.assertEqual(patch["characters"]["slot_1"]["resources_delta"], {"sta": -1})

    def test_state_engine_apply_skill_cost_deltas_wrapper_preserves_contract(self) -> None:
        adjusted = state_engine.apply_skill_cost_deltas_to_patch({}, "slot_1", {"deltas": {"sta": -2}})

        self.assertIn("apply_skill_cost_deltas_to_patch", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(adjusted["characters"]["slot_1"]["resources_delta"]["sta"], -2)

    def test_skill_costs_normalize_skill_cost_bounds_amount_and_resource(self) -> None:
        self.assertEqual(
            skill_costs.normalize_skill_cost({"resource": " Mana ", "amount": "-3"}, resource_name="Aether"),
            {"resource": "Mana", "amount": 0},
        )
        self.assertEqual(
            skill_costs.normalize_skill_cost({"amount": 2}, resource_name="Aether"),
            {"resource": "Aether", "amount": 2},
        )
        self.assertIsNone(skill_costs.normalize_skill_cost(None, resource_name="Aether"))

    def test_state_engine_dynamic_skill_uses_extracted_cost_normalizer(self) -> None:
        skill = state_engine.normalize_dynamic_skill_state(
            {"name": "Funkenwurf", "cost": {"resource": " Mana ", "amount": 3}},
            resource_name="Aether",
        )

        self.assertEqual(skill["cost"], {"resource": "Mana", "amount": 3})

    def test_world_settings_normalizer_preserves_campaign_defaults_and_bounds(self) -> None:
        defaults = {
            "campaign_length": "medium",
            "target_turns": {"short": 12, "medium": 40, "open": None},
            "pacing_profile": {
                "short": {"beats_per_turn": 3, "detail_level": "high", "plot_density": "dense", "sideplot_limit": 0, "milestone_every_n_turns": 6, "min_story_chars": 800, "max_story_chars": 1400},
                "medium": {"beats_per_turn": 2, "detail_level": "medium", "plot_density": "balanced", "sideplot_limit": 2, "milestone_every_n_turns": 12, "min_story_chars": 900, "max_story_chars": 1800},
                "open": {"beats_per_turn": 1, "detail_level": "low", "plot_density": "loose", "sideplot_limit": None, "milestone_every_n_turns": 20, "min_story_chars": 700, "max_story_chars": 1600},
            },
        }

        normalized = world_settings.normalize_world_settings(
            {
                "campaign_length": "SHORT",
                "resource_name": " Mana ",
                "consequence_severity": "invalid",
                "offclass_xp_multiplier": 9,
                "onclass_xp_multiplier": 0.1,
                "target_turns": {"short": 0, "open": 99},
                "pacing_profile": {"short": {"beats_per_turn": 0, "sideplot_limit": -2, "min_story_chars": 10, "max_story_chars": 20}},
            },
            deep_copy=copy.deepcopy,
            default_campaign_length_settings=lambda: copy.deepcopy(defaults),
            normalize_resource_name=lambda value, _default: str(value or "").strip(),
            clamp_float=lambda value, low, high: max(low, min(high, float(value))),
            campaign_lengths=("short", "medium", "open"),
        )

        self.assertEqual(normalized["campaign_length"], "short")
        self.assertEqual(normalized["resource_name"], "Mana")
        self.assertEqual(normalized["consequence_severity"], "mittel")
        self.assertEqual(normalized["offclass_xp_multiplier"], 1.0)
        self.assertEqual(normalized["onclass_xp_multiplier"], 0.5)
        self.assertEqual(normalized["target_turns"]["short"], 12)
        self.assertIsNone(normalized["target_turns"]["open"])
        self.assertEqual(normalized["pacing_profile"]["short"]["beats_per_turn"], 3)
        self.assertEqual(normalized["pacing_profile"]["short"]["sideplot_limit"], 0)
        self.assertEqual(normalized["pacing_profile"]["short"]["min_story_chars"], 300)
        self.assertEqual(normalized["pacing_profile"]["short"]["max_story_chars"], 300)

    def test_state_engine_world_settings_wrappers_preserve_contract(self) -> None:
        settings = state_engine.normalize_world_settings({"campaign_length": "open"})

        self.assertIn("default_campaign_length_settings", state_engine.EXPORTED_SYMBOLS)
        self.assertIn("normalize_world_settings", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(state_engine.default_campaign_length_settings()["campaign_length"], "medium")
        self.assertEqual(settings["campaign_length"], "open")
        self.assertIsNone(settings["target_turns"]["open"])

    def test_world_settings_active_pacing_profile_selects_campaign_length(self) -> None:
        profile = world_settings.active_pacing_profile(
            {"world": {"settings": {"campaign_length": "short"}}},
            normalize_world_settings=lambda _settings: {
                "campaign_length": "short",
                "target_turns": {"short": 12},
                "pacing_profile": {"short": {"beats_per_turn": 3}},
            },
            deep_copy=copy.deepcopy,
            campaign_lengths=("short", "medium", "open"),
            pacing_profile_defaults={"short": {"beats_per_turn": 1}, "medium": {"beats_per_turn": 2}, "open": {"beats_per_turn": 1}},
        )

        self.assertEqual(profile["campaign_length"], "short")
        self.assertEqual(profile["target_turn"], 12)
        self.assertEqual(profile["beats_per_turn"], 3)

    def test_state_engine_active_pacing_profile_wrapper_preserves_contract(self) -> None:
        profile = state_engine.active_pacing_profile({"world": {"settings": {"campaign_length": "open"}}})

        self.assertIn("active_pacing_profile", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(profile["campaign_length"], "open")
        self.assertIsNone(profile["target_turn"])

    def test_world_settings_turn_budget_estimates_update_timing(self) -> None:
        state = {"meta": {"turn": 5}, "world": {"settings": {"campaign_length": "short"}}}

        timing = world_settings.compute_turn_budget_estimates(
            state,
            normalize_meta_timing=lambda meta: meta.setdefault("timing", {"ai_latency_ema_sec": 2.0, "player_latency_ema_sec": 3.0}),
            normalize_world_settings=lambda _settings: {"campaign_length": "short", "target_turns": {"short": 12}},
            target_turns_defaults={"short": 10, "medium": 40},
            timing_defaults={"ai_latency_ema_sec": 1.0, "player_latency_ema_sec": 1.0},
        )

        self.assertEqual(timing["turns_target_est"], 12)
        self.assertEqual(timing["turns_left_est"], 7)
        self.assertEqual(timing["cycle_ema_sec"], 5.0)
        self.assertEqual(state["meta"]["timing"], timing)

    def test_state_engine_turn_budget_estimates_wrapper_preserves_contract(self) -> None:
        timing = state_engine.compute_turn_budget_estimates(
            {"meta": {"turn": 2}, "world": {"settings": {"campaign_length": "open"}}}
        )

        self.assertIn("compute_turn_budget_estimates", state_engine.EXPORTED_SYMBOLS)
        self.assertIsNone(timing["turns_target_est"])
        self.assertIsNone(timing["turns_left_est"])

    def test_world_settings_normalize_meta_timing_coerces_existing_values(self) -> None:
        meta = {
            "timing": {
                "ai_latency_ema_sec": "2.5",
                "player_latency_ema_sec": "",
                "cycle_ema_sec": "9",
                "turns_target_est": "-3",
                "turns_left_est": None,
                "last_response_ready_ts": "",
            }
        }

        timing = world_settings.normalize_meta_timing(
            meta,
            deep_copy=copy.deepcopy,
            default_meta_timing=lambda: {
                "ai_latency_ema_sec": 1.0,
                "player_latency_ema_sec": 3.0,
                "cycle_ema_sec": 4.0,
                "turns_target_est": 8,
                "turns_left_est": 5,
                "last_response_ready_ts": None,
            },
        )

        self.assertEqual(timing["ai_latency_ema_sec"], 2.5)
        self.assertEqual(timing["player_latency_ema_sec"], 3.0)
        self.assertEqual(timing["cycle_ema_sec"], 9.0)
        self.assertEqual(timing["turns_target_est"], 0)
        self.assertIsNone(timing["turns_left_est"])
        self.assertIsNone(timing["last_response_ready_ts"])
        self.assertEqual(meta["timing"], timing)

    def test_state_engine_normalize_meta_timing_wrapper_preserves_contract(self) -> None:
        timing = state_engine.normalize_meta_timing({"timing": {"last_response_ready_ts": "12.5"}})

        self.assertIn("normalize_meta_timing", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(timing["last_response_ready_ts"], 12.5)

    def test_world_settings_update_turn_timing_ema_updates_cycle(self) -> None:
        state = {
            "meta": {
                "timing": {
                    "ai_latency_ema_sec": 2.0,
                    "player_latency_ema_sec": 4.0,
                    "last_response_ready_ts": 8.0,
                }
            }
        }

        timing = world_settings.update_turn_timing_ema(
            state,
            13.0,
            16.0,
            normalize_meta_timing=lambda meta: meta["timing"],
            clamp_float=lambda value, low, high: max(low, min(high, float(value))),
            ai_latency_clamp=(0.0, 10.0),
            player_latency_clamp=(0.0, 10.0),
            timing_ema_alpha=0.25,
            timing_defaults={"ai_latency_ema_sec": 1.0, "player_latency_ema_sec": 1.0},
        )

        self.assertEqual(timing["ai_latency_ema_sec"], 2.25)
        self.assertEqual(timing["player_latency_ema_sec"], 4.25)
        self.assertEqual(timing["last_response_ready_ts"], 16.0)
        self.assertEqual(timing["cycle_ema_sec"], 6.5)

    def test_state_engine_update_turn_timing_ema_wrapper_preserves_contract(self) -> None:
        timing = state_engine.update_turn_timing_ema({"meta": {}}, 10.0, 12.0)

        self.assertIn("update_turn_timing_ema", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(timing["last_response_ready_ts"], 12.0)
        self.assertEqual(timing["cycle_ema_sec"], timing["ai_latency_ema_sec"] + timing["player_latency_ema_sec"])

    def test_world_settings_milestone_state_for_turn_tracks_previous_and_next(self) -> None:
        self.assertEqual(
            world_settings.milestone_state_for_turn(7, {"milestone_every_n_turns": 5}),
            {"is_milestone": False, "last": 5, "next": 10},
        )
        self.assertEqual(
            world_settings.milestone_state_for_turn(10, {"milestone_every_n_turns": 5}),
            {"is_milestone": True, "last": 10, "next": 15},
        )

    def test_state_engine_milestone_state_for_turn_wrapper_preserves_contract(self) -> None:
        milestone = state_engine.milestone_state_for_turn(0, {"milestone_every_n_turns": 0})

        self.assertIn("milestone_state_for_turn", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(milestone, {"is_milestone": False, "last": 0, "next": 18})

    def test_world_settings_build_pacing_instruction_block_formats_profile(self) -> None:
        block = world_settings.build_pacing_instruction_block(
            {"meta": {"turn": 6}},
            active_pacing_profile=lambda _state: {
                "campaign_length": "short",
                "beats_per_turn": 3,
                "detail_level": "high",
                "plot_density": "dense",
                "sideplot_limit": 0,
                "milestone_every_n_turns": 6,
                "min_story_chars": 800,
                "max_story_chars": 1400,
            },
            milestone_state_for_turn=lambda _turn, _profile: {"is_milestone": True, "last": 6, "next": 12},
        )

        self.assertEqual(block["profile"]["campaign_length"], "short")
        self.assertEqual(block["milestone"], {"is_milestone": True, "last": 6, "next": 12})
        self.assertIn("PACING INSTRUCTIONS:", block["text"])
        self.assertIn("- campaign_length=short", block["text"])
        self.assertIn("- is_milestone_turn=yes", block["text"])
        self.assertIn("Für SHORT", block["text"])

    def test_state_engine_build_pacing_instruction_block_wrapper_preserves_contract(self) -> None:
        block = state_engine.build_pacing_instruction_block({"meta": {"turn": 1}, "world": {"settings": {"campaign_length": "open"}}})

        self.assertIn("build_pacing_instruction_block", state_engine.EXPORTED_SYMBOLS)
        self.assertIn("profile", block)
        self.assertIn("milestone", block)
        self.assertIn("text", block)

    def test_combat_meta_update_starts_combat_and_records_queue(self) -> None:
        def normalize_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
            combat_meta = copy.deepcopy(
                meta.get("combat")
                or {"active": False, "combat_id": "", "round": 0, "phase": "idle", "action_queue": [], "participants": [], "last_resolution": {}}
            )
            combat_meta.setdefault("action_queue", [])
            combat_meta.setdefault("participants", [])
            combat_meta.setdefault("last_resolution", {})
            return combat_meta

        state = {
            "meta": {"turn": 7},
            "characters": {"slot_1": {"derived": {"combat_flags": {"in_combat": True}}}},
        }

        combat_meta = combat.update_combat_meta_after_turn(
            state,
            actor="slot_1",
            action_type="combat",
            input_text="",
            story_text="Ein Angriff beginnt. Danach passiert mehr.",
            patch={},
            combat_context={"hinted": False},
            resolution_summary={"outcome": "started"},
            normalize_combat_meta=normalize_meta,
            utc_now=lambda: "now",
            normalized_eval_text=lambda value: str(value or "").strip().lower(),
            patch_has_combat_signal=lambda _patch: False,
            combat_narrative_hints=("angriff",),
            combat_end_hints=("ende",),
            make_id=lambda prefix: f"{prefix}_1",
            first_sentences=lambda text, _count: str(text).split(".")[0],
            deep_copy=copy.deepcopy,
        )

        self.assertTrue(combat_meta["active"])
        self.assertEqual(combat_meta["combat_id"], "cmb_1")
        self.assertEqual(combat_meta["round"], 1)
        self.assertEqual(combat_meta["phase"], "collecting")
        self.assertEqual(combat_meta["participants"], ["slot_1"])
        self.assertEqual(combat_meta["action_queue"][-1]["turn"], 7)
        self.assertEqual(combat_meta["action_queue"][-1]["summary"], "Ein Angriff beginnt")
        self.assertEqual(combat_meta["last_resolution"], {"outcome": "started"})
        self.assertEqual(state["meta"]["combat"], combat_meta)

    def test_state_engine_combat_meta_update_wrapper_preserves_contract(self) -> None:
        state_engine.configure(
            {
                "COMBAT_NARRATIVE_HINTS": ("angriff",),
                "COMBAT_END_HINTS": ("ende",),
                "make_id": lambda prefix: f"{prefix}_1",
                "utc_now": lambda: "now",
                "first_sentences": lambda text, _count: str(text).split(".")[0],
            }
        )

        combat_meta = state_engine.update_combat_meta_after_turn(
            {"meta": {"turn": 1}, "characters": {}},
            actor="slot_1",
            action_type="combat",
            input_text="",
            story_text="Angriff.",
            patch={},
            combat_context={},
            resolution_summary={},
        )

        self.assertIn("update_combat_meta_after_turn", state_engine.EXPORTED_SYMBOLS)
        self.assertTrue(combat_meta["active"])
        self.assertEqual(combat_meta["phase"], "collecting")
        self.assertEqual(combat_meta["participants"], ["slot_1"])

    def test_element_class_path_rank_lookup_selects_requested_path(self) -> None:
        world = {
            "element_class_paths": {
                "elem_fire": [
                    {"id": "path_a", "name": "Pfad A", "ranks": {"F": {"id": "node_a"}}},
                    {"id": "path_b", "name": "Pfad B", "ranks": {"C": {"id": "node_b"}}},
                ]
            }
        }

        resolved = element_class_paths.resolve_class_path_rank_node(
            world,
            {"path_id": "path_b", "rank": "c"},
            normalize_class_current=lambda value: value,
            resolve_class_element_id=lambda _klass, _world: "elem_fire",
            normalize_skill_rank=lambda value: str(value or "").strip().upper(),
            deep_copy=copy.deepcopy,
        )

        self.assertEqual(resolved["path_id"], "path_b")
        self.assertEqual(resolved["path_name"], "Pfad B")
        self.assertEqual(resolved["element_id"], "elem_fire")
        self.assertEqual(resolved["rank"], "C")
        self.assertEqual(resolved["node"], {"id": "node_b"})
        world["element_class_paths"]["elem_fire"][1]["ranks"]["C"]["id"] = "changed"
        self.assertEqual(resolved["node"], {"id": "node_b"})

    def test_state_engine_class_path_rank_lookup_wrapper_preserves_contract(self) -> None:
        world = {
            "elements": {"elem_fire": {"name": "Feuer"}},
            "element_class_paths": {
                "elem_fire": [
                    {"id": "path_a", "name": "Pfad A", "ranks": {"F": {"id": "node_a"}}},
                    {"id": "path_b", "name": "Pfad B", "ranks": {"C": {"id": "node_b"}}},
                ]
            },
        }

        resolved = state_engine.resolve_class_path_rank_node(
            world,
            {"name": "Feuerklasse", "element_id": "elem_fire", "path_id": "path_b", "rank": "c"},
        )

        self.assertIn("resolve_class_path_rank_node", state_engine.EXPORTED_SYMBOLS)
        self.assertEqual(resolved["path_id"], "path_b")
        self.assertEqual(resolved["rank"], "C")
        self.assertEqual(resolved["node"], {"id": "node_b"})

    def test_state_engine_element_class_path_generation_wrapper_preserves_contract(self) -> None:
        paths = state_engine.generate_element_class_paths(
            {"elem_fire": {"name": "Feuer", "theme": "Hitze"}},
            {"theme": "Feuer"},
        )

        self.assertIn("elem_fire", paths)
        self.assertTrue(1 <= len(paths["elem_fire"]) <= 3)
        self.assertIn("F", paths["elem_fire"][0]["ranks"])
        self.assertEqual(paths["elem_fire"][0]["ranks"]["F"]["element_id"], "elem_fire")

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
