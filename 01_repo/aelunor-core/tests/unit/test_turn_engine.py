import copy
import logging
import unittest

import requests
from fastapi import HTTPException

from app.services import state_engine
from app.services import turn_engine


def configure_engine_for_tests() -> None:
    engine_symbols = {
        "ERROR_CODE_TURN_INTERNAL": "turn_internal",
        "ERROR_CODE_NARRATOR_RESPONSE": "narrator_response",
        "ERROR_CODE_JSON_REPAIR": "json_repair",
        "TURN_ERROR_USER_MESSAGES": {
            "turn_internal": "Interner Fehler.",
            "narrator_response": "Narrator nicht erreichbar.",
            "json_repair": "JSON-Reparatur fehlgeschlagen.",
        },
        "make_id": lambda prefix: f"{prefix}_test",
        "utc_now": lambda: "2026-03-10T00:00:00+00:00",
        "deep_copy": copy.deepcopy,
        "LOGGER": logging.getLogger("turn-engine-test"),
        "requests": requests,
        "remember_recent_story": lambda _campaign: None,
        "rebuild_memory_summary": lambda _campaign: None,
        "EQUIPMENT_SLOT_ALIASES": {
            "weapon": "weapon",
            "mainhand": "weapon",
            "offhand": "offhand",
            "shield": "offhand",
            "head": "head",
            "chest": "chest",
            "trinket": "trinket",
            "amulet": "amulet",
        },
        "EQUIPMENT_CANONICAL_SLOTS": {"weapon", "offhand", "head", "chest", "amulet", "ring_1", "ring_2", "trinket"},
        "ITEM_WEAPON_KEYWORDS": {"schwert", "klinge"},
        "ITEM_OFFHAND_KEYWORDS": {"schild", "fokus"},
        "ITEM_CHEST_KEYWORDS": {"rüstung", "ruestung", "mantel"},
        "ITEM_TRINKET_KEYWORDS": {"amulett", "ring", "talisman"},
        "ITEM_DETAIL_CLAUSE_MARKERS": (" mit ", " für ", " fuer "),
        "AUTO_ITEM_GENERIC_NAMES": {"gegenstand", "objekt", "item", "waffe", "rüstung", "ruestung", "ding"},
        "UNIVERSAL_SKILL_LIKE_NAMES": {"ausdauer"},
        "INJURY_SEVERITIES": {"leicht", "mittel", "schwer"},
        "INJURY_HEALING_STAGES": {"frisch", "heilend", "fast_heil", "geheilt"},
        "RESOURCE_KEYS": ("hp", "stamina", "aether", "stress", "corruption", "wounds"),
        "RESISTANCE_KEYS": ("physical", "fire", "cold", "lightning", "poison", "bleed", "shadow", "holy", "curse", "fear"),
        "ATTRIBUTE_KEYS": ("str", "dex", "con", "int", "wis", "cha", "luck"),
        "SKILL_RANKS": ("F", "E", "D", "C", "B", "A", "S"),
        "SKILL_RANK_ORDER": {"F": 0, "E": 1, "D": 2, "C": 3, "B": 4, "A": 5, "S": 6},
        "DEFAULT_DYNAMIC_SKILL_LEVEL_MAX": 10,
        "DEFAULT_NUMERIC_SKILL_DELTA_XP": 20,
        "ENABLE_LEGACY_SHADOW_WRITEBACK": False,
        "ABILITY_UNLOCK_GENERIC_NAMES": {
            "faehigkeit",
            "technik",
            "zauber",
            "magie",
            "gabe",
            "kunst",
            "ritual",
            "form",
            "formel",
        },
        "ABILITY_UNLOCK_TRIGGER_PATTERNS": [],
        "normalize_patch_semantics": state_engine.normalize_patch_semantics,
        "clean_auto_item_name": state_engine.clean_auto_item_name,
        "clean_creator_item_name": state_engine.clean_creator_item_name,
        "ensure_item_shape": state_engine.ensure_item_shape,
        "infer_item_slot_from_definition": state_engine.infer_item_slot_from_definition,
        "normalize_equipment_slot_key": state_engine.normalize_equipment_slot_key,
        "normalize_equipment_update_payload": state_engine.normalize_equipment_update_payload,
        "item_matches_equipment_slot": state_engine.item_matches_equipment_slot,
        "normalize_class_current": state_engine.normalize_class_current,
        "skill_id_from_name": state_engine.skill_id_from_name,
        "normalize_dynamic_skill_state": state_engine.normalize_dynamic_skill_state,
        "resource_name_for_character": state_engine.resource_name_for_character,
        "normalize_skill_elements_for_world": state_engine.normalize_skill_elements_for_world,
        "normalize_progression_event_list": state_engine.normalize_progression_event_list,
        "normalize_injury_state": state_engine.normalize_injury_state,
        "normalize_scar_state": state_engine.normalize_scar_state,
        "normalize_plotpoint_entry": state_engine.normalize_plotpoint_entry,
        "normalize_plotpoint_update_entry": state_engine.normalize_plotpoint_update_entry,
        "clean_scene_name": state_engine.clean_scene_name,
        "is_plausible_scene_name": state_engine.is_plausible_scene_name,
        "is_generic_scene_identifier": state_engine.is_generic_scene_identifier,
        "clamp": state_engine.clamp,
        "normalize_event_entry": state_engine.normalize_event_entry,
        "normalized_eval_text": state_engine.normalized_eval_text,
        "resolve_class_element_id": state_engine.resolve_class_element_id,
        "normalize_skill_rank": state_engine.normalize_skill_rank,
        "is_skill_manifestation_name_plausible": state_engine.is_skill_manifestation_name_plausible,
    }
    for name in state_engine.EXPORTED_SYMBOLS:
        engine_symbols.setdefault(name, getattr(state_engine, name))
    state_engine.configure(engine_symbols)
    turn_engine.configure(
        engine_symbols
    )


class TurnEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        configure_engine_for_tests()

    def _base_apply_state(self) -> dict:
        character = state_engine.blank_character_state("slot_1")
        character["bio"]["name"] = "Mati"
        character["scene_id"] = "scene_start"
        return {
            "meta": {
                "turn": 2,
                "phase": "active",
                "world_time": state_engine.default_world_time(),
            },
            "world": {"settings": {}},
            "characters": {"slot_1": character},
            "items": {},
            "plotpoints": [],
            "map": {"nodes": {}, "edges": []},
            "scenes": {"scene_start": {"name": "Start", "danger": 0, "notes": ""}},
            "events": [],
        }

    def test_classify_transport_runtime_error(self) -> None:
        err = turn_engine.classify_turn_exception(
            RuntimeError("ollama error 500"),
            phase="narrator_call",
            trace_ctx={"trace_id": "trace_1"},
        )
        self.assertIsInstance(err, turn_engine.TurnFlowError)
        self.assertEqual(err.error_code, "narrator_response")
        self.assertEqual(err.phase, "narrator_call")

    def test_find_turn_not_found(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            turn_engine.find_turn({"turns": []}, "turn_missing")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_reset_turn_branch_marks_following_turns(self) -> None:
        campaign = {
            "state": {"meta": {"turn": 2}},
            "turns": [
                {
                    "turn_id": "turn_1",
                    "turn_number": 1,
                    "status": "active",
                    "state_before": {"meta": {"turn": 0}},
                    "updated_at": "",
                },
                {
                    "turn_id": "turn_2",
                    "turn_number": 2,
                    "status": "active",
                    "state_before": {"meta": {"turn": 1}},
                    "updated_at": "",
                },
            ],
        }
        turn = campaign["turns"][0]
        turn_engine.reset_turn_branch(campaign, turn, "undone")
        self.assertEqual(campaign["state"]["meta"]["turn"], 0)
        self.assertEqual(campaign["turns"][0]["status"], "undone")
        self.assertEqual(campaign["turns"][1]["status"], "undone")

    def test_sanitize_patch_prunes_invalid_character_item_refs(self) -> None:
        state = {
            "meta": {"turn": 2},
            "world": {"settings": {}},
            "characters": {
                "slot_1": {
                    "resources": {"resource_name": "Mana"},
                }
            },
            "items": {
                "item_sword": {
                    "id": "item_sword",
                    "name": "Altes Schwert",
                    "slot": "weapon",
                }
            },
        }
        patch = {
            "characters": {
                "slot_1": {
                    "derived": {"armor": 99},
                    "inventory_add": ["item_sword", "item_missing", "item_shield"],
                    "equip_set": {
                        "weapon": "item_sword",
                        "offhand": "item_shield",
                        "head": "item_missing",
                    },
                },
                "slot_9": {
                    "inventory_add": ["item_sword"],
                },
            },
            "items_new": {
                "item_broken": "not-an-item",
                "item_shield": {
                    "name": "der Schild mit Kratzern",
                    "tags": ["offhand"],
                },
            },
        }

        sanitized = turn_engine.sanitize_patch(state, patch)

        self.assertNotIn("slot_9", sanitized["characters"])
        slot_patch = sanitized["characters"]["slot_1"]
        self.assertNotIn("derived", slot_patch)
        self.assertEqual(slot_patch["inventory_add"], ["item_sword", "item_shield"])
        self.assertEqual(slot_patch["equipment_set"], {"weapon": "item_sword", "offhand": "item_shield"})
        self.assertNotIn("equip_set", slot_patch)
        self.assertNotIn("item_broken", sanitized["items_new"])
        self.assertEqual(sanitized["items_new"]["item_shield"]["name"], "Schild")
        self.assertEqual(sanitized["items_new"]["item_shield"]["slot"], "offhand")

    def test_apply_patch_adds_new_items_inventory_and_equipment(self) -> None:
        state = self._base_apply_state()
        patch = {
            "items_new": {
                "item_sword": {
                    "name": "Mondklinge",
                    "slot": "weapon",
                    "weight": 2,
                }
            },
            "characters": {
                "slot_1": {
                    "inventory_add": ["item_sword"],
                    "equipment_set": {"weapon": "item_sword"},
                }
            },
        }

        applied = turn_engine.apply_patch(state, patch)
        character = applied["characters"]["slot_1"]

        self.assertIn("item_sword", applied["items"])
        self.assertEqual(applied["items"]["item_sword"]["name"], "Mondklinge")
        self.assertEqual(applied["items"]["item_sword"]["slot"], "weapon")
        self.assertIn({"item_id": "item_sword", "stack": 1}, character["inventory"]["items"])
        self.assertEqual(character["equipment"]["weapon"], "item_sword")

    def test_apply_patch_items_new_only_adds_normalized_item_to_state_items(self) -> None:
        state = self._base_apply_state()
        patch = {
            "items_new": {
                "item_lantern": {
                    "name": "Sturmlaterne",
                    "slot": "trinket",
                    "weight": 1,
                    "tags": ["tool"],
                }
            }
        }

        applied = turn_engine.apply_patch(state, patch)

        self.assertEqual(applied["items"]["item_lantern"]["id"], "item_lantern")
        self.assertEqual(applied["items"]["item_lantern"]["name"], "Sturmlaterne")
        self.assertEqual(applied["items"]["item_lantern"]["slot"], "trinket")
        self.assertEqual(applied["items"]["item_lantern"]["weight"], 1)
        self.assertEqual(applied["characters"]["slot_1"]["inventory"]["items"], [])

    def test_apply_patch_inventory_remove_keeps_other_items(self) -> None:
        state = self._base_apply_state()
        character = state["characters"]["slot_1"]
        character["inventory"]["items"] = [
            {"item_id": "item_keep", "stack": 1},
            {"item_id": "item_remove", "stack": 2},
            {"item_id": "item_other", "stack": 1},
        ]
        patch = {
            "characters": {
                "slot_1": {
                    "inventory_remove": ["item_remove"],
                }
            }
        }

        applied = turn_engine.apply_patch(state, patch)

        self.assertEqual(
            applied["characters"]["slot_1"]["inventory"]["items"],
            [
                {"item_id": "item_keep", "stack": 1},
                {"item_id": "item_other", "stack": 1},
            ],
        )

    def test_apply_patch_inventory_set_replaces_items_and_quick_slots(self) -> None:
        state = self._base_apply_state()
        character = state["characters"]["slot_1"]
        character["inventory"]["items"] = [{"item_id": "item_old", "stack": 1}]
        character["inventory"]["quick_slots"] = {"slot_1": "item_old", "slot_2": "item_keep"}
        replacement_items = [
            {"item_id": "item_new", "stack": 3},
            {"item_id": "item_tool", "stack": 1},
        ]
        patch = {
            "characters": {
                "slot_1": {
                    "inventory_set": {
                        "items": replacement_items,
                        "quick_slots": {"slot_1": "item_new"},
                    },
                }
            }
        }

        applied = turn_engine.apply_patch(state, patch)

        self.assertEqual(applied["characters"]["slot_1"]["inventory"]["items"], replacement_items)
        self.assertEqual(applied["characters"]["slot_1"]["inventory"]["quick_slots"], {"slot_1": "item_new"})

    def test_apply_patch_inventory_set_then_equipment_set_auto_adds_equipped_item(self) -> None:
        state = self._base_apply_state()
        character = state["characters"]["slot_1"]
        character["inventory"]["items"] = [{"item_id": "item_old", "stack": 1}]
        replacement_items = [{"item_id": "item_new", "stack": 2}]
        patch = {
            "characters": {
                "slot_1": {
                    "inventory_set": {"items": replacement_items},
                    "equipment_set": {"weapon": "item_equipped_missing"},
                }
            }
        }

        applied = turn_engine.apply_patch(state, patch)
        character = applied["characters"]["slot_1"]

        self.assertEqual(
            character["inventory"]["items"],
            [
                {"item_id": "item_new", "stack": 2},
                {"item_id": "item_equipped_missing", "stack": 1},
            ],
        )
        self.assertEqual(character["equipment"]["weapon"], "item_equipped_missing")

    def test_apply_patch_conditions_add_preserves_existing_and_dedupes(self) -> None:
        state = self._base_apply_state()
        state["characters"]["slot_1"]["conditions"] = ["blessed", "tired"]
        patch = {
            "characters": {
                "slot_1": {
                    "conditions_add": ["tired", "hidden"],
                }
            }
        }

        applied = turn_engine.apply_patch(state, patch)

        self.assertEqual(applied["characters"]["slot_1"]["conditions"], ["blessed", "tired", "hidden"])

    def test_apply_patch_conditions_remove_only_matching_conditions(self) -> None:
        state = self._base_apply_state()
        state["characters"]["slot_1"]["conditions"] = ["blessed", "tired", "hidden"]
        patch = {
            "characters": {
                "slot_1": {
                    "conditions_remove": ["tired", "missing"],
                }
            }
        }

        applied = turn_engine.apply_patch(state, patch)

        self.assertEqual(applied["characters"]["slot_1"]["conditions"], ["blessed", "hidden"])

    def test_apply_patch_effects_add_preserves_existing_and_dedupes_by_id(self) -> None:
        state = self._base_apply_state()
        state["characters"]["slot_1"]["effects"] = [
            {"id": "effect_old", "name": "Alter Effekt"},
            {"id": "effect_keep", "name": "Bleibt"},
        ]
        patch = {
            "characters": {
                "slot_1": {
                    "effects_add": [
                        {"id": "effect_old", "name": "Duplikat"},
                        {"id": "effect_new", "name": "Neuer Effekt"},
                    ],
                }
            }
        }

        applied = turn_engine.apply_patch(state, patch)

        self.assertEqual(
            applied["characters"]["slot_1"]["effects"],
            [
                {"id": "effect_old", "name": "Alter Effekt"},
                {"id": "effect_keep", "name": "Bleibt"},
                {"id": "effect_new", "name": "Neuer Effekt"},
            ],
        )

    def test_apply_patch_effects_remove_only_matching_ids(self) -> None:
        state = self._base_apply_state()
        state["characters"]["slot_1"]["effects"] = [
            {"id": "effect_remove", "name": "Weg"},
            {"id": "effect_keep", "name": "Bleibt"},
        ]
        patch = {
            "characters": {
                "slot_1": {
                    "effects_remove": ["effect_remove", "effect_missing"],
                }
            }
        }

        applied = turn_engine.apply_patch(state, patch)

        self.assertEqual(
            applied["characters"]["slot_1"]["effects"],
            [{"id": "effect_keep", "name": "Bleibt"}],
        )

    def test_apply_patch_effects_add_then_remove_uses_final_remove_order(self) -> None:
        state = self._base_apply_state()
        state["characters"]["slot_1"]["effects"] = [{"id": "effect_keep", "name": "Bleibt"}]
        patch = {
            "characters": {
                "slot_1": {
                    "effects_add": [
                        {"id": "effect_added_then_removed", "name": "Kurz da"},
                        {"id": "effect_added", "name": "Bleibt neu"},
                    ],
                    "effects_remove": ["effect_added_then_removed"],
                }
            }
        }

        applied = turn_engine.apply_patch(state, patch)

        self.assertEqual(
            applied["characters"]["slot_1"]["effects"],
            [
                {"id": "effect_keep", "name": "Bleibt"},
                {"id": "effect_added", "name": "Bleibt neu"},
            ],
        )

    def test_apply_patch_equipment_set_normalizes_slots_and_adds_missing_item_to_inventory(self) -> None:
        state = self._base_apply_state()
        character = state["characters"]["slot_1"]
        character["inventory"]["items"] = [{"item_id": "item_existing", "stack": 1}]
        character["equipment"] = {"weapon": "item_existing", "offhand": ""}
        patch = {
            "characters": {
                "slot_1": {
                    "equipment_set": {
                        "mainhand": "item_blade",
                        "shield": "item_shield",
                    },
                }
            }
        }

        applied = turn_engine.apply_patch(state, patch)
        character = applied["characters"]["slot_1"]

        self.assertEqual(character["equipment"]["weapon"], "item_blade")
        self.assertEqual(character["equipment"]["offhand"], "item_shield")
        self.assertIn({"item_id": "item_blade", "stack": 1}, character["inventory"]["items"])
        self.assertIn({"item_id": "item_shield", "stack": 1}, character["inventory"]["items"])
        self.assertIn({"item_id": "item_existing", "stack": 1}, character["inventory"]["items"])

    def test_apply_patch_equip_set_uses_legacy_contract_and_adds_missing_item_to_inventory(self) -> None:
        state = self._base_apply_state()
        patch = {
            "characters": {
                "slot_1": {
                    "equip_set": {
                        "weapon": "item_legacy_sword",
                        "amulet": "item_legacy_amulet",
                    },
                }
            }
        }

        applied = turn_engine.apply_patch(state, patch)
        character = applied["characters"]["slot_1"]

        self.assertEqual(character["equipment"]["weapon"], "item_legacy_sword")
        self.assertEqual(character["equipment"]["amulet"], "item_legacy_amulet")
        self.assertIn({"item_id": "item_legacy_sword", "stack": 1}, character["inventory"]["items"])
        self.assertIn({"item_id": "item_legacy_amulet", "stack": 1}, character["inventory"]["items"])

    def test_apply_patch_map_add_nodes_creates_map_node_and_scene(self) -> None:
        state = self._base_apply_state()
        patch = {
            "map_add_nodes": [
                {
                    "id": "scene_ruins",
                    "name": "Alte Ruinen",
                    "type": "location",
                    "danger": 4,
                    "discovered": True,
                }
            ]
        }

        applied = turn_engine.apply_patch(state, patch)

        self.assertEqual(
            applied["map"]["nodes"]["scene_ruins"],
            {"name": "Alte Ruinen", "type": "location", "danger": 4, "discovered": True},
        )
        self.assertEqual(
            applied["scenes"]["scene_ruins"],
            {"name": "Alte Ruinen", "danger": 4, "notes": ""},
        )

    def test_apply_patch_plotpoints_add_dedupes_and_update_modifies_existing(self) -> None:
        state = self._base_apply_state()
        state["plotpoints"] = [
            {
                "id": "pp_gate",
                "type": "story",
                "title": "Tor finden",
                "status": "active",
                "owner": None,
                "notes": "Das Tor ist verborgen.",
                "requirements": [],
            }
        ]
        patch = {
            "plotpoints_add": [
                {"id": "pp_gate", "title": "Tor finden", "status": "active"},
                {"id": "pp_key", "title": "Schlüssel sichern", "status": "active"},
            ],
            "plotpoints_update": [
                {"id": "pp_gate", "status": "done", "notes": "Das Tor wurde geöffnet."},
            ],
        }

        applied = turn_engine.apply_patch(state, patch)
        plotpoints = {entry["id"]: entry for entry in applied["plotpoints"]}

        self.assertEqual([entry["id"] for entry in applied["plotpoints"]].count("pp_gate"), 1)
        self.assertIn("pp_key", plotpoints)
        self.assertEqual(plotpoints["pp_gate"]["status"], "done")
        self.assertEqual(plotpoints["pp_gate"]["notes"], "Das Tor wurde geöffnet.")

    def test_apply_patch_events_add_normalizes_and_appends_events(self) -> None:
        state = self._base_apply_state()
        state["events"] = ["Vorheriges Ereignis"]
        patch = {
            "events_add": [
                "Neues Ereignis",
                {"text": "Ereignis aus Dict"},
                "",
            ],
        }

        applied = turn_engine.apply_patch(state, patch)

        self.assertEqual(
            applied["events"],
            ["Vorheriges Ereignis", "Neues Ereignis", "Ereignis aus Dict"],
        )

    def test_apply_patch_time_advance_updates_world_time_and_appends_reason_event(self) -> None:
        state = self._base_apply_state()
        patch = {
            "meta": {
                "time_advance": {
                    "days": 2,
                    "time_of_day": "morning",
                    "reason": "Rast im Lager",
                }
            }
        }

        applied = turn_engine.apply_patch(state, patch)

        self.assertEqual(applied["meta"]["world_time"]["absolute_day"], 3)
        self.assertEqual(applied["meta"]["world_time"]["time_of_day"], "morning")
        self.assertEqual(applied["world"]["day"], 3)
        self.assertEqual(applied["world"]["time"], "morning")
        self.assertIn("Zeit vergeht: +2 Tage (Rast im Lager).", applied["events"])

    def test_apply_patch_meta_phase_updates_state_phase(self) -> None:
        state = self._base_apply_state()
        patch = {"meta": {"phase": "ready_to_start"}}

        applied = turn_engine.apply_patch(state, patch)

        self.assertEqual(applied["meta"]["phase"], "ready_to_start")

    def test_apply_patch_resources_and_skills_are_normalized_after_apply(self) -> None:
        state = self._base_apply_state()
        patch = {
            "characters": {
                "slot_1": {
                    "resources_set": {
                        "hp_current": 8,
                        "hp_max": 12,
                        "sta_current": 6,
                        "sta_max": 9,
                        "res_current": 4,
                        "res_max": 7,
                    },
                    "skills_set": {
                        "flammenstoss": {
                            "name": "Flammenstoß",
                            "rank": "E",
                            "level": 2,
                            "tags": ["magie"],
                            "description": "Ein kurzer Feuerstoß.",
                        }
                    },
                }
            },
        }

        applied = turn_engine.apply_patch(state, patch)
        character = applied["characters"]["slot_1"]
        matching_skills = [
            skill
            for skill in character["skills"].values()
            if skill.get("name") == "Flammenstoß"
        ]
        self.assertEqual(len(matching_skills), 1)
        skill = matching_skills[0]

        self.assertEqual(character["hp_current"], 8)
        self.assertEqual(character["sta_current"], 6)
        self.assertEqual(character["res_current"], 4)
        self.assertGreaterEqual(character["hp_max"], character["hp_current"])
        self.assertGreaterEqual(character["sta_max"], character["sta_current"])
        self.assertGreaterEqual(character["res_max"], character["res_current"])
        self.assertTrue(skill["id"].startswith("skill_"))
        self.assertEqual(skill["name"], "Flammenstoß")
        self.assertEqual(skill["rank"], "E")
        self.assertEqual(skill["level"], 2)
        self.assertIn("next_xp", skill)
        self.assertNotIn("hp", character)
        self.assertNotIn("stamina", character)
        self.assertNotIn("aether", character)


if __name__ == "__main__":
    unittest.main()
