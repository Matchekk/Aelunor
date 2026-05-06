import copy
import unittest

from app.services import state_engine
from app.services import state_basics
from app.services.world import element_class_paths
from app.services.world import element_generation
from app.services.world import element_profiles
from app.services.world import element_relations
from app.services.world import element_skills
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
