import copy
import unittest
from typing import Any, Dict, List

from app.services import state_engine
from app.services import state_basics
from app.services.world import attribute_influence
from app.services.world import combat
from app.services.world import element_class_paths
from app.services.world import element_entities
from app.services.world import element_generation
from app.services.world import element_ids
from app.services.world import element_profiles
from app.services.world import element_relations
from app.services.world import element_skills
from app.services.world import species_profiles
from app.services.world import world_settings


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
