import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services import campaign_service, claim_service, setup_service, turn_service


HOST_ID = "host_1"
HOST_TOKEN = "host_token"
PLAYER_ID = "player_1"
PLAYER_TOKEN = "player_token"
SLOT_ID = "slot_aria"


class TempCampaignStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.campaigns_dir = root / "campaigns"
        self.campaigns_dir.mkdir(parents=True)

    def path(self, campaign_id: str) -> Path:
        return self.campaigns_dir / f"{campaign_id}.json"

    def save(self, campaign: Dict[str, Any], **_kwargs: Any) -> None:
        with self.path(campaign["campaign_meta"]["campaign_id"]).open("w", encoding="utf-8") as handle:
            json.dump(campaign, handle, ensure_ascii=False, indent=2)

    def load(self, campaign_id: str) -> Dict[str, Any]:
        with self.path(campaign_id).open("r", encoding="utf-8") as handle:
            return json.load(handle)


def make_campaign() -> Dict[str, Any]:
    return {
        "campaign_meta": {
            "campaign_id": "camp_smoke",
            "title": "Smoke Campaign",
            "status": "active",
            "host_player_id": HOST_ID,
            "created_at": "2026-04-27T00:00:00Z",
            "updated_at": "2026-04-27T00:00:00Z",
        },
        "players": {
            HOST_ID: {"display_name": "Host", "player_token_hash": f"hash:{HOST_TOKEN}"},
            PLAYER_ID: {"display_name": "Aria Player", "player_token_hash": f"hash:{PLAYER_TOKEN}"},
        },
        "claims": {SLOT_ID: None},
        "setup": {
            "world": {"completed": False, "question_order": ["world_seed"], "answers": {}},
            "characters": {
                SLOT_ID: {"completed": False, "question_order": ["char_seed"], "answers": {}},
            },
        },
        "state": {
            "meta": {
                "phase": "lobby",
                "turn": 0,
                "intro_state": {"status": "idle", "generated_turn_id": None, "last_error": ""},
            },
            "world": {"settings": {}},
            "characters": {
                SLOT_ID: {
                    "bio": {"name": "Aria"},
                    "class_current": {"id": "class_wanderer", "name": "Wanderer", "rank": "F"},
                    "skills": [],
                    "inventory": [],
                    "equipment": {},
                }
            },
            "items": {},
            "events": [],
            "recent_story": [],
        },
        "turns": [],
    }


def authenticate(campaign: Dict[str, Any], player_id: Optional[str], token: Optional[str], *, required: bool = True) -> None:
    if required and (not player_id or not token):
        raise AssertionError("player credentials required")
    player = campaign.get("players", {}).get(player_id or "")
    if not player or player.get("player_token_hash") != f"hash:{token}":
        raise AssertionError("invalid player credentials")


def current_question_id(setup_node: Dict[str, Any]) -> Optional[str]:
    for question_id in setup_node.get("question_order") or []:
        if question_id not in (setup_node.get("answers") or {}):
            return question_id
    return None


def active_turns(campaign: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [turn for turn in campaign.get("turns", []) if turn.get("status") == "active"]


def fake_turn_record(
    *,
    campaign: Dict[str, Any],
    actor: str,
    player_id: Optional[str],
    action_type: str,
    content: str,
    **_kwargs: Any,
) -> Dict[str, Any]:
    state_before = copy.deepcopy(campaign["state"])
    campaign["state"]["meta"]["turn"] = int(campaign["state"]["meta"].get("turn", 0)) + 1
    campaign["state"]["meta"]["phase"] = "active"
    campaign["state"].setdefault("events", []).append(f"Fake narrator resolved: {content}")
    campaign["state"].setdefault("recent_story", []).append("Fake narrator keeps the smoke flow deterministic.")
    turn = {
        "turn_id": f"turn_{len(campaign.get('turns', [])) + 1}",
        "turn_number": campaign["state"]["meta"]["turn"],
        "status": "active",
        "actor": actor,
        "player_id": player_id,
        "action_type": action_type,
        "input_text_raw": content,
        "input_text_display": content,
        "gm_text_raw": "Fake narrator keeps the smoke flow deterministic.",
        "gm_text_display": "Fake narrator keeps the smoke flow deterministic.",
        "requests": [],
        "patch": {},
        "state_before": state_before,
        "state_after": copy.deepcopy(campaign["state"]),
        "retry_of_turn_id": None,
        "created_at": "2026-04-27T00:00:00Z",
        "updated_at": "2026-04-27T00:00:00Z",
        "edit_history": [],
        "prompt_payload": {"fake_narrator": True},
    }
    campaign.setdefault("turns", []).append(turn)
    return turn


class CoreFlowSmokeTests(unittest.TestCase):
    def test_campaign_setup_claim_turn_and_reload_with_fake_narrator(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aelunor-smoke-") as temp_dir:
            store = TempCampaignStore(Path(temp_dir))

            created = campaign_service.create_campaign(
                title="Smoke Campaign",
                display_name="Host",
                deps=campaign_service.CampaignServiceDependencies(
                    ensure_campaign_storage=lambda: None,
                    create_campaign_record=lambda _title, _display_name: self._create_campaign_record(store),
                    find_campaign_by_join_code=lambda _code: None,
                    new_player=lambda _display_name: {"player_id": PLAYER_ID, "player_token": PLAYER_TOKEN, "display_name": "Aria Player"},
                    utc_now=lambda: "2026-04-27T00:00:00Z",
                    hash_secret=lambda value: f"hash:{value}",
                    save_campaign=store.save,
                    load_campaign=store.load,
                    authenticate_player=authenticate,
                    require_host=lambda campaign, player_id: self.assertEqual(player_id, campaign["campaign_meta"]["host_player_id"]),
                    deep_copy=copy.deepcopy,
                    intro_state=lambda campaign: campaign["state"]["meta"]["intro_state"],
                    active_turns=active_turns,
                    can_start_adventure=lambda campaign: campaign["setup"]["world"]["completed"]
                    and campaign["setup"]["characters"][SLOT_ID]["completed"]
                    and campaign["claims"][SLOT_ID] == PLAYER_ID,
                    clear_live_activity=lambda *_args, **_kwargs: None,
                    start_blocking_action=lambda *_args, **_kwargs: None,
                    clear_blocking_action=lambda *_args, **_kwargs: None,
                    try_generate_adventure_intro=lambda campaign: fake_turn_record(
                        campaign=campaign,
                        actor=SLOT_ID,
                        player_id=PLAYER_ID,
                        action_type="story",
                        content="Intro",
                    ),
                    apply_world_time_advance=lambda *_args, **_kwargs: None,
                    rebuild_all_character_derived=lambda *_args, **_kwargs: None,
                    append_character_change_events=lambda *_args, **_kwargs: None,
                    normalize_class_current=lambda payload: payload,
                    rebuild_character_derived=lambda *_args, **_kwargs: None,
                    normalize_world_time=lambda _meta: {},
                    campaign_path=lambda campaign_id: str(store.path(campaign_id)),
                    clear_live_campaign_state=lambda _campaign_id: None,
                ),
            )

            campaign_id = created["campaign_id"]
            self.assertEqual(store.load(campaign_id)["state"]["meta"]["phase"], "lobby")

            setup_deps = self._setup_deps(store)
            setup_service.apply_world_setup_random_preview(
                campaign_id=campaign_id,
                preview_answers=[{"question_id": "world_seed", "answer": {"value": "Nebelwald"}}],
                player_id=HOST_ID,
                player_token=HOST_TOKEN,
                deps=setup_deps,
            )
            self.assertTrue(store.load(campaign_id)["setup"]["world"]["completed"])

            claim_service.claim_slot(
                campaign_id=campaign_id,
                slot_name=SLOT_ID,
                player_id=PLAYER_ID,
                player_token=PLAYER_TOKEN,
                deps=claim_service.ClaimServiceDependencies(
                    load_campaign=store.load,
                    authenticate_player=authenticate,
                    player_claim=lambda campaign, player_id: next((slot for slot, owner in campaign["claims"].items() if owner == player_id), None),
                    current_question_id=current_question_id,
                    ensure_question_ai_copy=lambda *_args, **_kwargs: None,
                    save_campaign=store.save,
                    is_host=lambda campaign, player_id: campaign["campaign_meta"]["host_player_id"] == player_id,
                ),
            )
            self.assertEqual(store.load(campaign_id)["claims"][SLOT_ID], PLAYER_ID)

            character_result = setup_service.apply_character_setup_random_preview(
                campaign_id=campaign_id,
                slot_name=SLOT_ID,
                preview_answers=[{"question_id": "char_seed", "answer": {"value": "Aria"}}],
                player_id=PLAYER_ID,
                player_token=PLAYER_TOKEN,
                deps=setup_deps,
            )
            self.assertTrue(character_result["started_adventure"])

            campaign = store.load(campaign_id)
            self.assertEqual(campaign["state"]["meta"]["phase"], "active")
            self.assertEqual(len(active_turns(campaign)), 1)

            turn_result = turn_service.create_turn(
                campaign_id=campaign_id,
                actor=SLOT_ID,
                action_type="do",
                content="Ich prüfe die Runen am Tor.",
                player_id=PLAYER_ID,
                player_token=PLAYER_TOKEN,
                deps=turn_service.TurnServiceDependencies(
                    load_campaign=store.load,
                    authenticate_player=authenticate,
                    active_turns=active_turns,
                    intro_state=lambda campaign: campaign["state"]["meta"]["intro_state"],
                    require_claim=lambda campaign, player_id, actor: self.assertEqual(campaign["claims"][actor], player_id),
                    new_turn_trace_context=lambda _campaign_id, _slot_id, _player_id: {"trace_id": "trace_smoke"},
                    emit_turn_phase_event=lambda *_args, **_kwargs: None,
                    clear_live_activity=lambda *_args, **_kwargs: None,
                    start_blocking_action=lambda *_args, **_kwargs: None,
                    clear_blocking_action=lambda *_args, **_kwargs: None,
                    create_turn_record=fake_turn_record,
                    save_campaign=store.save,
                    classify_turn_exception=lambda *_args, **_kwargs: None,
                    turn_flow_error_cls=RuntimeError,
                    remember_recent_story=lambda _campaign: None,
                    rebuild_memory_summary=lambda _campaign: None,
                    find_turn=lambda campaign, turn_id: next(turn for turn in campaign["turns"] if turn["turn_id"] == turn_id),
                    reset_turn_branch=lambda *_args, **_kwargs: None,
                    utc_now=lambda: "2026-04-27T00:00:00Z",
                ),
            )

            reloaded = store.load(campaign_id)
            self.assertEqual(turn_result["trace_id"], "trace_smoke")
            self.assertEqual(reloaded["state"]["meta"]["phase"], "active")
            self.assertEqual(reloaded["state"]["meta"]["turn"], 2)
            self.assertEqual(len(active_turns(reloaded)), 2)
            self.assertEqual(reloaded["turns"][-1]["prompt_payload"], {"fake_narrator": True})
            self.assertIn("Fake narrator resolved", reloaded["state"]["events"][-1])
            self.assertEqual(reloaded["claims"][SLOT_ID], PLAYER_ID)

    def _create_campaign_record(self, store: TempCampaignStore) -> Dict[str, Any]:
        campaign = make_campaign()
        store.save(campaign)
        return {
            "campaign": campaign,
            "campaign_id": campaign["campaign_meta"]["campaign_id"],
            "join_code": "SMOKE1",
            "player_id": HOST_ID,
            "player_token": HOST_TOKEN,
        }

    def _setup_deps(self, store: TempCampaignStore) -> setup_service.SetupServiceDependencies:
        def apply_preview(
            _campaign: Dict[str, Any],
            setup_node: Dict[str, Any],
            _question_map: Dict[str, Dict[str, Any]],
            preview_answers: List[Any],
            *,
            player_id: Optional[str],
        ) -> int:
            _ = player_id
            for entry in preview_answers:
                setup_node.setdefault("answers", {})[entry["question_id"]] = entry.get("answer", {"value": "smoke"})
            return len(preview_answers)

        def finalize_character(campaign: Dict[str, Any], slot_name: str) -> Dict[str, Any]:
            campaign["setup"]["characters"][slot_name]["completed"] = True
            campaign["state"]["meta"]["phase"] = "active"
            intro_turn = fake_turn_record(
                campaign=campaign,
                actor=slot_name,
                player_id=campaign["claims"][slot_name],
                action_type="story",
                content="Intro",
            )
            campaign["state"]["meta"]["intro_state"] = {
                "status": "generated",
                "generated_turn_id": intro_turn["turn_id"],
                "last_error": "",
            }
            return intro_turn

        return setup_service.SetupServiceDependencies(
            load_campaign=store.load,
            authenticate_player=authenticate,
            require_host=lambda campaign, player_id: self.assertEqual(player_id, campaign["campaign_meta"]["host_player_id"]),
            is_host=lambda campaign, player_id: campaign["campaign_meta"]["host_player_id"] == player_id,
            current_question_id=current_question_id,
            clear_live_activity=lambda *_args, **_kwargs: None,
            start_blocking_action=lambda *_args, **_kwargs: None,
            clear_blocking_action=lambda *_args, **_kwargs: None,
            ensure_question_ai_copy=lambda *_args, **_kwargs: None,
            save_campaign=store.save,
            build_world_question_state=lambda campaign, _viewer_id: None
            if not current_question_id(campaign["setup"]["world"])
            else {"question": {"question_id": current_question_id(campaign["setup"]["world"])}, "progress": {}},
            build_character_question_state=lambda campaign, slot_name: None
            if not current_question_id(campaign["setup"]["characters"][slot_name])
            else {"question": {"question_id": current_question_id(campaign["setup"]["characters"][slot_name])}, "progress": {}},
            progress_payload=lambda setup_node: {"answered": len(setup_node.get("answers") or {})},
            validate_answer_payload=lambda _question, answer: answer,
            store_setup_answer=lambda setup_node, question, stored, **_kwargs: setup_node.setdefault("answers", {}).update({question["id"]: stored}),
            build_random_setup_preview=lambda *_args, **_kwargs: [],
            apply_random_setup_preview=apply_preview,
            finalize_world_setup=lambda campaign, _player_id: (
                campaign["setup"]["world"].__setitem__("completed", True),
                campaign["state"]["meta"].__setitem__("phase", "character_setup_open"),
            ),
            finalize_character_setup=finalize_character,
            deep_copy=copy.deepcopy,
            build_world_summary=lambda _campaign: {},
            build_character_summary=lambda _campaign, _slot_name: {},
            normalize_world_settings=lambda settings: dict(settings or {}),
            apply_world_summary_to_boards=lambda *_args, **_kwargs: None,
            apply_character_summary_to_state=lambda *_args, **_kwargs: None,
            campaign_slots=lambda campaign: list(campaign["setup"]["characters"].keys()),
            target_turns_defaults={},
            pacing_profile_defaults={},
            world_question_map={"world_seed": {"id": "world_seed", "type": "text"}},
            character_question_map={"char_seed": {"id": "char_seed", "type": "text"}},
        )


if __name__ == "__main__":
    unittest.main()
