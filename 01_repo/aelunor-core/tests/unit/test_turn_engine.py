import copy
import logging
import unittest

import requests
from fastapi import HTTPException

from app.services import state_engine
from app.services import turn_engine
from app.services.turn.attribute_context import build_turn_attribute_context
from app.services.turn.flow_errors import build_narrator_turn_error
from app.services.turn.patch_apply_bio import apply_patch_character_bio_updates
from app.services.turn.patch_apply_normalization import apply_patch_character_late_normalization
from app.services.turn.patch_pipeline import apply_patch_with_events, sanitize_patch_with_events, validate_patch_with_events
from app.services.turn.patch_pipeline import call_canon_extractor_with_events
from app.services.turn.prompt_payloads import build_turn_system_prompt, build_turn_user_prompt
from app.services.turn.records import build_turn_record_payload
from app.services.turn.setup_context import prepare_turn_working_state
from app.services.turn.story_length_guard import rewrite_story_length_guard as rewrite_story_length_guard_helper


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
        "SKILL_RANK_THRESHOLDS": (
            ("S", 14),
            ("A", 11),
            ("B", 9),
            ("C", 7),
            ("D", 5),
            ("E", 3),
            ("F", 1),
        ),
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
        "CLASS_ASCENSION_STATUSES": {"none", "available", "active", "completed"},
        "PROGRESSION_SET_DIRECT_KEYS": {
            "level",
            "xp_total",
            "xp_current",
            "xp_to_next",
            "class_level",
            "class_xp",
            "class_xp_to_next",
        },
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

    def test_build_narrator_turn_error_emits_guard_event(self) -> None:
        events = []

        def emit(ctx, **payload):
            events.append((ctx, payload))

        def make_error(**payload):
            return turn_engine.TurnFlowError(
                error_code=payload["error_code"],
                phase=payload["phase"],
                trace_id=(payload["trace_ctx"] or {}).get("trace_id", ""),
                user_message=payload["user_message"],
            )

        err = build_narrator_turn_error(
            "Antwort abgeschnitten",
            trace_ctx={"trace_id": "trace_1"},
            error_code_narrator_response="narrator_response",
            emit_turn_phase_event=emit,
            turn_flow_error=make_error,
        )

        self.assertIsInstance(err, turn_engine.TurnFlowError)
        self.assertEqual(err.error_code, "narrator_response")
        self.assertEqual(err.phase, "narrator_call_finished")
        self.assertEqual(events[0][0], {"trace_id": "trace_1"})
        self.assertEqual(events[0][1]["error_class"], "NarratorGuardError")
        self.assertEqual(events[0][1]["message"], "Antwort abgeschnitten")

    def test_validate_patch_with_events_emits_success_events(self) -> None:
        events = []

        validate_patch_with_events(
            {"state": True},
            {"patch": True},
            stage="narrator",
            trace_ctx={"trace_id": "trace_1"},
            validate_patch=lambda _state, _patch: None,
            emit_turn_phase_event=lambda ctx, **payload: events.append((ctx, payload)),
            turn_flow_error=lambda **_payload: AssertionError("unexpected error"),
            error_code_schema_validation="schema_validation",
        )

        self.assertEqual([event[1]["phase"] for event in events], ["schema_validation", "schema_validation"])
        self.assertEqual(events[0][1]["extra"], {"stage": "narrator"})
        self.assertEqual(events[1][1]["extra"], {"stage": "narrator", "result": "ok"})

    def test_sanitize_patch_with_events_returns_sanitized_patch(self) -> None:
        events = []
        sanitized = {"patch": "clean"}

        result = sanitize_patch_with_events(
            {"state": True},
            {"patch": "raw"},
            stage="narrator",
            trace_ctx={"trace_id": "trace_1"},
            sanitize_patch=lambda _state, _patch: sanitized,
            emit_turn_phase_event=lambda ctx, **payload: events.append((ctx, payload)),
            turn_flow_error=lambda **_payload: AssertionError("unexpected error"),
            error_code_patch_sanitize="patch_sanitize",
        )

        self.assertIs(result, sanitized)
        self.assertEqual([event[1]["phase"] for event in events], ["patch_sanitize", "patch_sanitize"])
        self.assertEqual(events[0][1]["extra"], {"stage": "narrator"})
        self.assertEqual(events[1][1]["extra"], {"stage": "narrator", "result": "ok"})

    def test_sanitize_patch_with_events_emits_extractor_failure_event(self) -> None:
        events = []

        def fail_sanitize(_state, _patch):
            raise ValueError("bad sanitize")

        def make_error(**payload):
            return turn_engine.TurnFlowError(
                error_code=payload["error_code"],
                phase=payload["phase"],
                trace_id=(payload["trace_ctx"] or {}).get("trace_id", ""),
                user_message="sanitize failed",
                cause_class=payload["exc"].__class__.__name__,
                cause_message=str(payload["exc"]),
            )

        with self.assertRaises(turn_engine.TurnFlowError) as ctx:
            sanitize_patch_with_events(
                {"state": True},
                {"patch": "raw"},
                stage="extractor_player",
                trace_ctx={"trace_id": "trace_1"},
                sanitize_patch=fail_sanitize,
                emit_turn_phase_event=lambda event_ctx, **payload: events.append((event_ctx, payload)),
                turn_flow_error=make_error,
                error_code_patch_sanitize="patch_sanitize",
                extractor_apply_stage="player",
            )

        self.assertEqual(ctx.exception.error_code, "patch_sanitize")
        self.assertEqual(
            [event[1]["phase"] for event in events],
            ["patch_sanitize", "patch_sanitize", "extractor_patch_apply"],
        )
        self.assertEqual(events[1][1]["extra"], {"stage": "extractor_player"})
        self.assertEqual(events[2][1]["extra"], {"stage": "player"})

    def test_apply_patch_with_events_returns_next_state(self) -> None:
        events = []
        next_state = {"meta": {"turn": 2}}
        seen = {}

        def fake_apply(state, patch, *, attribute_cap):
            seen["state"] = state
            seen["patch"] = patch
            seen["attribute_cap"] = attribute_cap
            return next_state

        result = apply_patch_with_events(
            {"meta": {"turn": 1}},
            {"events_add": ["x"]},
            stage="narrator",
            trace_ctx={"trace_id": "trace_1"},
            attribute_cap=12,
            apply_patch=fake_apply,
            emit_turn_phase_event=lambda ctx, **payload: events.append((ctx, payload)),
            turn_flow_error=lambda **_payload: AssertionError("unexpected error"),
            error_code_patch_apply="patch_apply",
        )

        self.assertIs(result, next_state)
        self.assertEqual(seen["attribute_cap"], 12)
        self.assertEqual([event[1]["phase"] for event in events], ["patch_apply", "patch_apply"])
        self.assertEqual(events[1][1]["extra"], {"stage": "narrator", "result": "ok"})

    def test_apply_patch_with_events_emits_extractor_failure_event(self) -> None:
        events = []

        def fail_apply(_state, _patch, *, attribute_cap):
            self.assertEqual(attribute_cap, 10)
            raise ValueError("bad apply")

        def make_error(**payload):
            return turn_engine.TurnFlowError(
                error_code=payload["error_code"],
                phase=payload["phase"],
                trace_id=(payload["trace_ctx"] or {}).get("trace_id", ""),
                user_message="apply failed",
                cause_class=payload["exc"].__class__.__name__,
                cause_message=str(payload["exc"]),
            )

        with self.assertRaises(turn_engine.TurnFlowError) as ctx:
            apply_patch_with_events(
                {"state": True},
                {"patch": True},
                stage="extractor_player",
                trace_ctx={"trace_id": "trace_1"},
                attribute_cap=10,
                apply_patch=fail_apply,
                emit_turn_phase_event=lambda event_ctx, **payload: events.append((event_ctx, payload)),
                turn_flow_error=make_error,
                error_code_patch_apply="patch_apply",
                extractor_apply_stage="player",
            )

        self.assertEqual(ctx.exception.error_code, "patch_apply")
        self.assertEqual(
            [event[1]["phase"] for event in events],
            ["patch_apply", "patch_apply", "extractor_patch_apply"],
        )
        self.assertEqual(events[1][1]["extra"], {"stage": "extractor_player"})
        self.assertEqual(events[2][1]["extra"], {"stage": "player"})

    def test_call_canon_extractor_with_events_returns_patch(self) -> None:
        events = []
        patch = {"events_add": ["x"]}
        seen = {}

        def fake_extractor(campaign, state, actor, action_type, source_text, *, source):
            seen.update(
                {
                    "campaign": campaign,
                    "state": state,
                    "actor": actor,
                    "action_type": action_type,
                    "source_text": source_text,
                    "source": source,
                }
            )
            return patch

        result = call_canon_extractor_with_events(
            {"id": "campaign_1"},
            {"state": True},
            "slot_1",
            "play",
            "Text",
            source="player",
            stage="player",
            trace_ctx={"trace_id": "trace_1"},
            call_canon_extractor=fake_extractor,
            emit_turn_phase_event=lambda ctx, **payload: events.append((ctx, payload)),
            turn_flow_error=lambda **_payload: AssertionError("unexpected error"),
            error_code_extractor="extractor",
        )

        self.assertIs(result, patch)
        self.assertEqual(seen["source"], "player")
        self.assertEqual([event[1]["phase"] for event in events], ["extractor_patch_generation", "extractor_patch_generation"])
        self.assertEqual(events[1][1]["extra"], {"stage": "player", "result": "ok"})

    def test_call_canon_extractor_with_events_wraps_failure(self) -> None:
        events = []

        def fail_extractor(*_args, **_kwargs):
            raise ValueError("extract failed")

        def make_error(**payload):
            return turn_engine.TurnFlowError(
                error_code=payload["error_code"],
                phase=payload["phase"],
                trace_id=(payload["trace_ctx"] or {}).get("trace_id", ""),
                user_message="extract failed",
                cause_class=payload["exc"].__class__.__name__,
                cause_message=str(payload["exc"]),
            )

        with self.assertRaises(turn_engine.TurnFlowError) as ctx:
            call_canon_extractor_with_events(
                {"id": "campaign_1"},
                {"state": True},
                "slot_1",
                "play",
                "Text",
                source="player",
                stage="player",
                trace_ctx={"trace_id": "trace_1"},
                call_canon_extractor=fail_extractor,
                emit_turn_phase_event=lambda event_ctx, **payload: events.append((event_ctx, payload)),
                turn_flow_error=make_error,
                error_code_extractor="extractor",
            )

        self.assertEqual(ctx.exception.error_code, "extractor")
        self.assertEqual([event[1]["phase"] for event in events], ["extractor_patch_generation", "extractor_patch_generation"])
        self.assertEqual(events[1][1]["error_class"], "ValueError")
        self.assertEqual(events[1][1]["extra"], {"stage": "player"})

    def test_validate_patch_with_events_emits_extractor_failure_event(self) -> None:
        events = []

        def fail_validation(_state, _patch):
            raise ValueError("bad patch")

        def make_error(**payload):
            return turn_engine.TurnFlowError(
                error_code=payload["error_code"],
                phase=payload["phase"],
                trace_id=(payload["trace_ctx"] or {}).get("trace_id", ""),
                user_message="schema failed",
                cause_class=payload["exc"].__class__.__name__,
                cause_message=str(payload["exc"]),
            )

        with self.assertRaises(turn_engine.TurnFlowError) as ctx:
            validate_patch_with_events(
                {"state": True},
                {"patch": True},
                stage="extractor_player",
                trace_ctx={"trace_id": "trace_1"},
                validate_patch=fail_validation,
                emit_turn_phase_event=lambda event_ctx, **payload: events.append((event_ctx, payload)),
                turn_flow_error=make_error,
                error_code_schema_validation="schema_validation",
                extractor_apply_stage="player",
        )

        self.assertEqual(ctx.exception.error_code, "schema_validation")
        self.assertEqual(
            [event[1]["phase"] for event in events],
            ["schema_validation", "schema_validation", "extractor_patch_apply"],
        )
        self.assertEqual(events[0][1]["extra"], {"stage": "extractor_player"})
        self.assertEqual(events[1][1]["extra"], {"stage": "extractor_player"})
        self.assertEqual(events[2][1]["extra"], {"stage": "player"})

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

    def test_apply_patch_bio_helper_updates_scene_and_removes_party_role(self) -> None:
        character = {
            "scene_id": "scene_old",
            "bio": {"name": "Mati", "party_role": "Leader", "origin": "Alt"},
        }
        upd = {
            "scene_id": "scene_new",
            "bio_set": {"name": "Mat", "party_role": "Tank", "title": "Wanderer"},
        }

        apply_patch_character_bio_updates(character, upd)

        self.assertEqual(character["scene_id"], "scene_new")
        self.assertEqual(
            character["bio"],
            {"name": "Mat", "origin": "Alt", "title": "Wanderer"},
        )

    def test_apply_patch_late_normalization_helper_preserves_order_and_events(self) -> None:
        calls = []
        character = {
            "bio": {"name": "Mati"},
            "skills": {"skill_a": {"name": "A"}},
        }
        state = {
            "meta": {"turn": 4},
            "world": {"settings": {"resource_name": "Mana"}},
            "items": {"item_a": {}},
            "events": [],
        }

        def record(name):
            def _callback(*_args, **_kwargs):
                calls.append(name)
                if name == "normalize_skill_store":
                    return {"skill_a": {"name": "A", "normalized": True}}
                if name == "resolve_injury_healing":
                    return [{"title": "eine Narbe"}]
                return None

            return _callback

        apply_patch_character_late_normalization(
            character,
            state,
            "slot_1",
            resource_name="Mana",
            effective_world_time={"absolute_day": 1},
            ENABLE_LEGACY_SHADOW_WRITEBACK=True,
            ensure_progression_shape=record("ensure_progression_shape"),
            ensure_character_progression_core=record("ensure_character_progression_core"),
            normalize_skill_store=record("normalize_skill_store"),
            resolve_injury_healing=record("resolve_injury_healing"),
            rebuild_character_derived=record("rebuild_character_derived"),
            reconcile_canonical_resources=record("reconcile_canonical_resources"),
            strip_legacy_shadow_fields=record("strip_legacy_shadow_fields"),
            write_legacy_shadow_fields=record("write_legacy_shadow_fields"),
            sync_scars_into_appearance=record("sync_scars_into_appearance"),
        )

        self.assertEqual(
            calls,
            [
                "ensure_progression_shape",
                "ensure_character_progression_core",
                "normalize_skill_store",
                "resolve_injury_healing",
                "rebuild_character_derived",
                "reconcile_canonical_resources",
                "strip_legacy_shadow_fields",
                "write_legacy_shadow_fields",
                "sync_scars_into_appearance",
            ],
        )
        self.assertEqual(character["skills"], {"skill_a": {"name": "A", "normalized": True}})
        self.assertEqual(state["events"], ["Mati trägt nun eine Narbe."])

    def test_apply_patch_mixed_character_patch_preserves_apply_order(self) -> None:
        state = self._base_apply_state()
        character = state["characters"]["slot_1"]
        character["conditions"] = ["focused"]
        character["injuries"] = [
            {
                "id": "injury_cut",
                "title": "Tiefe Schnitt",
                "severity": "leicht",
                "effects": [],
                "healing_stage": "frisch",
                "will_scar": True,
                "created_turn": 1,
                "notes": "vom alten Kampf",
            }
        ]
        patch = {
            "characters": {
                "slot_1": {
                    "scene_id": "scene_bridge",
                    "bio_set": {"name": "Mat", "party_role": "Leader"},
                    "conditions_add": ["hidden"],
                    "skills_set": {
                        "skill_shadow_step": {
                            "name": "Schatten Schritt",
                            "rank": "F",
                            "level": 1,
                            "description": "Leise Bewegung.",
                        }
                    },
                    "injuries_heal": ["injury_cut"],
                }
            }
        }

        applied = turn_engine.apply_patch(state, patch)
        character = applied["characters"]["slot_1"]

        self.assertEqual(character["scene_id"], "scene_bridge")
        self.assertEqual(character["bio"]["name"], "Mat")
        self.assertNotIn("party_role", character["bio"])
        self.assertIn("hidden", character["conditions"])
        self.assertEqual(character["injuries"], [])
        self.assertEqual(character["scars"][0]["title"], "Tiefe Narbe")
        self.assertEqual(character["appearance"]["scars"][0]["label"], "Tiefe Narbe")
        self.assertIn("Mat trägt nun Tiefe Narbe.", applied["events"])
        self.assertTrue(
            any(skill.get("name") == "Schatten Schritt" for skill in character["skills"].values())
        )

    def test_build_turn_user_prompt_includes_actor_resolution_hint(self) -> None:
        user_prompt, actor_display, actor_resolution_hint = build_turn_user_prompt(
            campaign={"slots": {"slot_1": {"character_name": "Mati"}}},
            actor="slot_1",
            action_type="play",
            content="Ich öffne die Tür.",
            context='{"state": "ok"}',
            turn_mode_guide={"play": "Spielzug"},
            turn_response_json_contract='{"story": "string"}',
            display_name_for_slot=lambda _campaign, _actor: "Mati",
            is_slot_id=lambda value: value.startswith("slot_"),
            is_first_person_action=lambda text: "Ich" in text,
        )

        self.assertEqual(actor_display, "Mati")
        self.assertIn("Aktiver Actor-Slot: slot_1.", actor_resolution_hint)
        self.assertIn(
            "Erste-Person-Pronomen im Spieltext wie 'ich', 'mich', 'mir' oder 'mein' meinen in diesem Turn immer Mati und niemals eine andere Figur.",
            actor_resolution_hint,
        )
        self.assertIn("CONTEXT_PACKET(JSON):\n{\"state\": \"ok\"}", user_prompt)
        self.assertIn('"actor_display": "Mati"', user_prompt)
        self.assertIn("ACTOR_AUFLÖSUNG:", user_prompt)

    def test_build_turn_system_prompt_keeps_core_guard_fragments(self) -> None:
        system_prompt = build_turn_system_prompt(
            system_prompt_base="BASE",
            turn_mode_guide={"play": "Spielzug", "canon": "Kanon"},
            pacing_text="PACING",
            attribute_prompt_hints="ATTRIBUTES",
            combat_scaling_context={
                "actor_score": 12,
                "threat_score": 8,
                "pressure": "normal",
                "ratio": 1.5,
                "weighted_ratio": 1.2,
                "element_factor": 1.0,
            },
            min_story_chars=900,
        )

        self.assertTrue(system_prompt.startswith("BASE\n\nACTION_TYPE-HINWEIS:"))
        self.assertIn("- play: Spielzug", system_prompt)
        self.assertIn("PACING\n\nATTRIBUTES", system_prompt)
        self.assertIn("INTENT-FIRST ist bindend", system_prompt)
        self.assertIn("ELEMENTSYSTEM ist bindend", system_prompt)
        self.assertIn("actor_score=12 threat_score=8 pressure=normal", system_prompt)
        self.assertIn("Die story muss mindestens 900 Zeichen enthalten.", system_prompt)

    def test_build_turn_attribute_context_uses_actor_and_world_settings(self) -> None:
        seen = {}

        def derive(state, actor, action_type, content, combat_context):
            seen["derive"] = (state, actor, action_type, content, combat_context)
            return {"primary_attributes": ["str"], "influence_tier": "minor"}

        def compute(profile, actor_character, world_settings):
            seen["compute"] = (profile, actor_character, world_settings)
            return {"damage_taken_mult": 0.9}

        profile, bias, hints = build_turn_attribute_context(
            {
                "characters": {"slot_1": {"bio": {"name": "Mati"}}},
                "world": {"settings": {"difficulty": "hard"}},
            },
            actor="slot_1",
            action_type="play",
            content="Angriff",
            combat_context={"active": True},
            derive_attribute_relevance=derive,
            compute_attribute_bias=compute,
            compose_attribute_prompt_hints=lambda profile, bias: f"{profile['influence_tier']}:{bias['damage_taken_mult']}",
        )

        self.assertEqual(profile, {"primary_attributes": ["str"], "influence_tier": "minor"})
        self.assertEqual(bias, {"damage_taken_mult": 0.9})
        self.assertEqual(hints, "minor:0.9")
        self.assertEqual(seen["compute"][1], {"bio": {"name": "Mati"}})
        self.assertEqual(seen["compute"][2], {"difficulty": "hard"})

    def test_build_turn_attribute_context_canon_overrides_bias(self) -> None:
        profile, bias, hints = build_turn_attribute_context(
            {"characters": {"slot_1": {}}, "world": {"settings": {}}},
            actor="slot_1",
            action_type="canon",
            content="Kanon",
            combat_context={"active": True},
            derive_attribute_relevance=lambda *_args: {"primary_attributes": ["str"], "influence_tier": "major"},
            compute_attribute_bias=lambda *_args: {"damage_taken_mult": 0.5},
            compose_attribute_prompt_hints=lambda profile, bias: f"{profile['influence_tier']}:{bias['damage_taken_mult']}",
        )

        self.assertEqual(
            profile,
            {
                "primary_attributes": [],
                "influence_tier": "none",
                "narrative_bias": [],
                "combat_active": True,
            },
        )
        self.assertEqual(
            bias,
            {
                "damage_taken_mult": 1.0,
                "cost_mult": 1.0,
                "complication_mult": 1.0,
                "outgoing_effect_mult": 1.0,
            },
        )
        self.assertEqual(hints, "none:1.0")

    def test_prepare_turn_working_state_increments_turn_and_pacing_defaults(self) -> None:
        budget_calls = []
        campaign = {
            "state": {
                "meta": {"turn": 3},
                "world": {"settings": {"raw": True}},
            }
        }

        state_before, working_state, pacing_block, pacing_profile, milestone_info, min_chars, max_chars = prepare_turn_working_state(
            campaign,
            deep_copy=copy.deepcopy,
            normalize_world_settings=lambda settings: {"normalized": settings.get("raw")},
            compute_turn_budget_estimates=lambda state: budget_calls.append(state["meta"]["turn"]),
            build_pacing_instruction_block=lambda _state: {
                "text": "PACING",
                "profile": {"campaign_length": "short"},
                "milestone": {"is_milestone": False},
            },
        )

        self.assertEqual(state_before["meta"]["turn"], 3)
        self.assertEqual(working_state["meta"]["turn"], 4)
        self.assertEqual(working_state["world"]["settings"], {"normalized": True})
        self.assertEqual(budget_calls, [4])
        self.assertEqual(pacing_block["text"], "PACING")
        self.assertEqual(pacing_profile, {"campaign_length": "short"})
        self.assertEqual(milestone_info, {"is_milestone": False})
        self.assertEqual(min_chars, 800)
        self.assertEqual(max_chars, 2200)
        working_state["meta"]["turn"] = 99
        self.assertEqual(campaign["state"]["meta"]["turn"], 3)

    def test_enforce_non_milestone_patch_limits_strips_rank_and_high_new_skills(self) -> None:
        state = self._base_apply_state()
        state["characters"]["slot_1"]["class_current"] = {
            "id": "wanderer",
            "name": "Wanderer",
            "rank": "F",
        }
        state["characters"]["slot_1"]["skills"] = {
            "skill_existing": {"name": "Bestehend", "rank": "F"}
        }
        patch = {
            "plotpoints_add": [
                {"id": "quest_class", "type": "class_ascension"},
                {"id": "quest_keep", "type": "rumor"},
            ],
            "characters": {
                "slot_1": {
                    "class_set": {"id": "mage", "name": "Magier", "rank": "A"},
                    "class_update": {"rank": "B", "title": "Adept"},
                    "skills_set": {
                        "skill_existing": {"name": "Bestehend", "rank": "S"},
                        "skill_new_a": {"name": "Neue Macht", "rank": "A"},
                        "skill_new_f": {"name": "Kleine List", "rank": "F"},
                    },
                }
            },
        }

        limited = turn_engine.enforce_non_milestone_patch_limits(
            state,
            patch,
            is_milestone=False,
            action_type="play",
        )

        self.assertEqual(patch["characters"]["slot_1"]["class_set"]["rank"], "A")
        self.assertEqual(limited["plotpoints_add"], [{"id": "quest_keep", "type": "rumor"}])
        self.assertEqual(limited["characters"]["slot_1"]["class_set"]["rank"], "F")
        self.assertEqual(limited["characters"]["slot_1"]["class_update"], {"title": "Adept"})
        self.assertIn("skill_existing", limited["characters"]["slot_1"]["skills_set"])
        self.assertNotIn("skill_new_a", limited["characters"]["slot_1"]["skills_set"])
        self.assertIn("skill_new_f", limited["characters"]["slot_1"]["skills_set"])
        self.assertIn("Klassenaufstiegs-Quest auf Milestone verschoben.", limited["events_add"])
        self.assertIn("Neuer A-Skill für slot_1 auf Milestone verschoben.", limited["events_add"])

    def test_enforce_progression_set_mode_limits_strips_direct_sets_outside_canon(self) -> None:
        patch = {
            "characters": {
                "slot_1": {
                    "progression_set": {
                        "level": 4,
                        "xp_total": 300,
                        "progression_events": [{"kind": "training"}],
                    }
                }
            }
        }

        limited = turn_engine.enforce_progression_set_mode_limits(patch, action_type="play")

        self.assertEqual(patch["characters"]["slot_1"]["progression_set"]["level"], 4)
        self.assertEqual(
            limited["characters"]["slot_1"]["progression_set"],
            {"progression_events": [{"kind": "training"}]},
        )
        self.assertEqual(
            limited["events_add"],
            ["System: Direkte XP/Level-Setzung ist nur im Modus CANON bindend."],
        )

    def test_progression_limit_wrappers_keep_canon_payloads_unchanged(self) -> None:
        patch = {
            "characters": {
                "slot_1": {
                    "progression_set": {"level": 4},
                    "class_update": {"rank": "A"},
                }
            }
        }

        self.assertIs(
            turn_engine.enforce_progression_set_mode_limits(patch, action_type="canon"),
            patch,
        )
        self.assertIs(
            turn_engine.enforce_non_milestone_patch_limits(
                self._base_apply_state(),
                patch,
                is_milestone=False,
                action_type="canon",
            ),
            patch,
        )

    def test_story_length_guard_rewrites_short_story_with_fake_schema_call(self) -> None:
        calls = []

        def fake_call(_system, user, _schema, **kwargs):
            calls.append((user, kwargs))
            return {"story": "Lang genug."}

        story = rewrite_story_length_guard_helper(
            system_prompt="system",
            user_prompt="user",
            story_text="kurz",
            patch={"events_add": ["x"]},
            requests_payload=[{"type": "none"}],
            min_story_chars=10,
            max_story_chars=80,
            min_story_rewrite_attempts=1,
            max_story_compress_attempts=1,
            story_rewrite_schema={"type": "object"},
            ollama_temperature=0.7,
            call_ollama_schema=fake_call,
            http_exception_type=HTTPException,
        )

        self.assertEqual(story, "Lang genug.")
        self.assertEqual(calls[0][1]["timeout"], 120)
        self.assertIn("REWRITE-AUFTRAG:", calls[0][0])
        self.assertIn("PATCH (unverändert lassen):", calls[0][0])

    def test_story_length_guard_compresses_long_story_with_fake_schema_call(self) -> None:
        calls = []

        def fake_call(_system, user, _schema, **kwargs):
            calls.append((user, kwargs))
            return {"story": "kurz"}

        story = rewrite_story_length_guard_helper(
            system_prompt="system",
            user_prompt="user",
            story_text="x" * 20,
            patch={},
            requests_payload=[],
            min_story_chars=5,
            max_story_chars=10,
            min_story_rewrite_attempts=1,
            max_story_compress_attempts=1,
            story_rewrite_schema={"type": "object"},
            ollama_temperature=0.7,
            call_ollama_schema=fake_call,
            http_exception_type=HTTPException,
        )

        self.assertEqual(story, "kurz")
        self.assertEqual(calls[0][1]["timeout"], 90)
        self.assertIn("KOMPRIMIERUNGSAUFTRAG:", calls[0][0])

    def test_story_length_guard_forwards_configured_ollama_timeout(self) -> None:
        calls = []

        def fake_call(_system, user, _schema, **kwargs):
            calls.append((user, kwargs))
            if "KOMPRIMIERUNGSAUFTRAG:" in user:
                return {"story": "Kompakt und vollständig."}
            return {"story": "Eine ausreichend lange neu geschriebene Szene mit klarer Plotbewegung."}

        story = rewrite_story_length_guard_helper(
            system_prompt="system",
            user_prompt="user",
            story_text="kurz",
            patch={},
            requests_payload=[],
            min_story_chars=10,
            max_story_chars=30,
            min_story_rewrite_attempts=1,
            max_story_compress_attempts=1,
            story_rewrite_schema={"type": "object"},
            ollama_temperature=0.7,
            call_ollama_schema=fake_call,
            http_exception_type=HTTPException,
            ollama_timeout_sec=300,
        )

        self.assertEqual(story, "Kompakt und vollständig.")
        rewrite_call = next(call for call in calls if "REWRITE-AUFTRAG:" in call[0])
        compress_call = next(call for call in calls if "KOMPRIMIERUNGSAUFTRAG:" in call[0])
        self.assertEqual(rewrite_call[1]["timeout"], 300)
        self.assertEqual(compress_call[1]["timeout"], 300)

    def test_story_length_guard_raises_when_rewrite_stays_short(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            rewrite_story_length_guard_helper(
                system_prompt="system",
                user_prompt="user",
                story_text="kurz",
                patch={},
                requests_payload=[],
                min_story_chars=10,
                max_story_chars=80,
                min_story_rewrite_attempts=1,
                max_story_compress_attempts=1,
                story_rewrite_schema={"type": "object"},
                ollama_temperature=0.7,
                call_ollama_schema=lambda *_args, **_kwargs: {"story": "kurz"},
                http_exception_type=HTTPException,
            )

        self.assertEqual(ctx.exception.status_code, 500)

    def test_build_turn_record_payload_preserves_record_contract(self) -> None:
        state_before = {"meta": {"turn": 1}}
        state_after = {"meta": {"turn": 2}, "events": []}
        attribute_profile = {"primary_attributes": ["str"]}
        combat_resolution = {"damage_taken": 2}
        resource_deltas = {"skill_cost": {"mana": -1}}
        npc_updates = [{"id": "npc_1"}]
        codex_updates = [{"id": "codex_1"}]
        updated_combat = {"active": True}

        turn_record = build_turn_record_payload(
            campaign={"turns": [{"turn_id": "turn_old"}]},
            actor="slot_1",
            player_id="player_1",
            action_type="play",
            content="Weiter",
            gm_text_display="GM text",
            requests_payload=[{"type": "none"}],
            skill_requests=[{"type": "choice"}],
            patch={"events_add": ["event"]},
            narrator_patch={"characters": {}},
            extractor_patch={"items_new": {}},
            canon_applied=False,
            attribute_profile=attribute_profile,
            combat_resolution=combat_resolution,
            resource_deltas_applied=resource_deltas,
            progression_result={"events": [{"kind": "xp"}]},
            canon_gate_meta={"ok": True},
            npc_updates=npc_updates,
            codex_updates=codex_updates,
            updated_combat=updated_combat,
            state_before=state_before,
            state_after=state_after,
            retry_of_turn_id="turn_retry",
            prompt_payload={"system": "s"},
            make_id=lambda prefix: f"{prefix}_new",
            utc_now=lambda: "2026-03-10T00:00:00+00:00",
            deep_copy=copy.deepcopy,
            normalize_requests_payload=lambda payload, **_kwargs: payload,
            is_continue_story_content=lambda value: value == "Weiter",
        )

        self.assertEqual(turn_record["turn_id"], "turn_new")
        self.assertEqual(turn_record["turn_number"], 2)
        self.assertEqual(turn_record["input_text_raw"], "Weiter")
        self.assertEqual(turn_record["input_text_display"], "")
        self.assertEqual(turn_record["requests"], [{"type": "none"}, {"type": "choice"}])
        self.assertEqual(turn_record["created_at"], "2026-03-10T00:00:00+00:00")
        self.assertEqual(turn_record["updated_at"], "2026-03-10T00:00:00+00:00")
        self.assertEqual(turn_record["retry_of_turn_id"], "turn_retry")
        # state_before is now defensively deep-copied like state_after (snapshot,
        # not an alias of the live working state).
        self.assertIsNot(turn_record["state_before"], state_before)
        self.assertEqual(turn_record["state_before"], state_before)
        self.assertIsNot(turn_record["state_after"], state_after)
        attribute_profile["primary_attributes"].append("dex")
        self.assertEqual(turn_record["attribute_profile"], {"primary_attributes": ["str"]})

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
