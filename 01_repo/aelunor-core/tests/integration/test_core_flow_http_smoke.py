from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from unittest.mock import patch

from fastapi.testclient import TestClient


SLOT_ID = "slot_1"
FAKE_NARRATOR_TEXT = "FAKE_NARRATOR_HTTP_SMOKE_OK"


def _answer_to_dict(entry: Any) -> Dict[str, Any]:
    if hasattr(entry, "model_dump"):
        return entry.model_dump()
    if isinstance(entry, dict):
        return dict(entry)
    return {"value": str(entry)}


def _question_ids(setup_node: Dict[str, Any]) -> Iterable[str]:
    return setup_node.get("question_queue") or setup_node.get("question_order") or []


class CoreFlowHttpSmokeTests(unittest.TestCase):
    def test_http_campaign_setup_claim_turn_and_reload_with_fake_narrator(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aelunor-http-smoke-") as temp_dir:
            os.environ["DATA_DIR"] = temp_dir

            from app import main
            from app.services import presence_service
            from app.services import live_state_service, state_engine

            campaigns_dir = str(Path(temp_dir) / "campaigns")
            Path(campaigns_dir).mkdir(parents=True, exist_ok=True)
            live_state_service.LIVE_STATE_REGISTRY.clear()
            presence_service.clear_stream_tickets()

            def fake_ensure_question_ai_copy(*_args: Any, **_kwargs: Any) -> str:
                return "HTTP smoke setup copy"

            def fake_apply_random_setup_preview(
                _campaign: Dict[str, Any],
                setup_node: Dict[str, Any],
                _question_map: Dict[str, Dict[str, Any]],
                preview_answers: Any,
                *,
                player_id: Optional[str],
            ) -> int:
                _ = player_id
                supplied = {_answer_to_dict(entry).get("question_id"): _answer_to_dict(entry) for entry in preview_answers or []}
                applied = 0
                for question_id in _question_ids(setup_node):
                    if question_id in (setup_node.get("answers") or {}):
                        continue
                    setup_node.setdefault("answers", {})[question_id] = supplied.get(question_id) or {
                        "question_id": question_id,
                        "value": f"http-smoke-{question_id}",
                    }
                    applied += 1
                return applied

            def fake_finalize_world_setup(campaign: Dict[str, Any], _player_id: Optional[str]) -> None:
                campaign["setup"]["world"]["completed"] = True
                campaign["state"]["meta"]["phase"] = "character_setup_open"
                campaign.setdefault("claims", {})[SLOT_ID] = None
                campaign["setup"].setdefault("characters", {})[SLOT_ID] = {
                    "completed": False,
                    "question_queue": ["char_seed"],
                    "answers": {},
                    "summary": {},
                    "raw_transcript": [],
                    "question_runtime": {},
                }
                character = main.blank_character_state(SLOT_ID)
                character["bio"]["name"] = "Aria"
                character["class_current"] = main.default_class_current()
                character["class_current"]["id"] = "class_http_smoke"
                character["class_current"]["name"] = "HTTP Smoke"
                campaign["state"].setdefault("characters", {})[SLOT_ID] = character

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
                campaign["state"]["meta"]["turn"] = int(campaign["state"]["meta"].get("turn", 0) or 0) + 1
                campaign["state"]["meta"]["phase"] = "active"
                campaign["state"].setdefault("events", []).append(f"{FAKE_NARRATOR_TEXT}: {content}")
                turn = {
                    "turn_id": f"turn_http_{len(campaign.get('turns', [])) + 1}",
                    "turn_number": campaign["state"]["meta"]["turn"],
                    "status": "active",
                    "actor": actor,
                    "player_id": player_id,
                    "action_type": action_type,
                    "input_text_raw": content,
                    "input_text_display": content,
                    "gm_text_raw": FAKE_NARRATOR_TEXT,
                    "gm_text_display": FAKE_NARRATOR_TEXT,
                    "requests": [],
                    "patch": main.blank_patch(),
                    "narrator_patch": main.blank_patch(),
                    "extractor_patch": main.blank_patch(),
                    "state_before": state_before,
                    "state_after": copy.deepcopy(campaign["state"]),
                    "retry_of_turn_id": None,
                    "edited_at": None,
                    "created_at": "2026-04-27T00:00:00Z",
                    "updated_at": "2026-04-27T00:00:00Z",
                    "edit_history": [],
                    "prompt_payload": {"fake_narrator": "http_smoke"},
                }
                campaign.setdefault("turns", []).append(turn)
                main.remember_recent_story(campaign)
                return turn

            def fail_real_ollama_post(*_args: Any, **_kwargs: Any) -> None:
                raise AssertionError("MVP smoke test must not call real Ollama over the network")

            def fake_finalize_character_setup(campaign: Dict[str, Any], slot_name: str) -> Dict[str, Any]:
                campaign["setup"]["characters"][slot_name]["completed"] = True
                intro_turn = fake_turn_record(
                    campaign=campaign,
                    actor=slot_name,
                    player_id=campaign["claims"].get(slot_name),
                    action_type="story",
                    content="HTTP smoke intro",
                )
                campaign["state"]["meta"]["intro_state"] = {
                    "status": "generated",
                    "generated_turn_id": intro_turn["turn_id"],
                    "last_error": "",
                }
                return intro_turn

            patches = [
                patch.object(main, "DATA_DIR", temp_dir),
                patch.object(main, "CAMPAIGNS_DIR", campaigns_dir),
                patch.object(state_engine, "DATA_DIR", temp_dir),
                patch.object(state_engine, "CAMPAIGNS_DIR", campaigns_dir),
                patch.object(main, "ensure_question_ai_copy", fake_ensure_question_ai_copy),
                patch.object(main, "apply_random_setup_preview", fake_apply_random_setup_preview),
                patch.object(main, "finalize_world_setup", fake_finalize_world_setup),
                patch.object(main, "finalize_character_setup", fake_finalize_character_setup),
                patch.object(main, "create_turn_record", fake_turn_record),
                patch.object(main.requests, "post", fail_real_ollama_post),
            ]

            with (
                patches[0],
                patches[1],
                patches[2],
                patches[3],
                patches[4],
                patches[5],
                patches[6],
                patches[7],
                patches[8],
                patches[9],
            ):
                main.ensure_campaign_storage()
                with TestClient(main.app) as client:
                    create_response = client.post(
                        "/api/campaigns",
                        json={"title": "HTTP Smoke Campaign", "display_name": "Host"},
                    )
                    self.assertEqual(create_response.status_code, 200, create_response.text)
                    created = create_response.json()
                    campaign_id = created["campaign_id"]
                    player_id = created["player_id"]
                    player_token = created["player_token"]
                    self.assertTrue(campaign_id)
                    self.assertTrue(created["join_code"])
                    headers = {"X-Player-Id": player_id, "X-Player-Token": player_token}
                    saved_path = Path(campaigns_dir) / f"{campaign_id}.json"
                    self.assertTrue(saved_path.is_file())
                    self.assertTrue(str(saved_path).startswith(temp_dir))

                    load_response = client.get(f"/api/campaigns/{campaign_id}", headers=headers)
                    self.assertEqual(load_response.status_code, 200, load_response.text)
                    self.assertEqual(load_response.json()["campaign_meta"]["campaign_id"], campaign_id)
                    self.assertEqual(load_response.json()["state"]["meta"]["phase"], "lobby")

                    join_response = client.post(
                        "/api/campaigns/join",
                        json={"join_code": created["join_code"], "display_name": "Second Player"},
                    )
                    self.assertEqual(join_response.status_code, 200, join_response.text)
                    second_player_id = join_response.json()["player_id"]
                    second_player_token = join_response.json()["player_token"]
                    self.assertTrue(second_player_id)
                    self.assertTrue(second_player_token)

                    ticket_response = client.post(f"/api/campaigns/{campaign_id}/events/ticket", headers=headers)
                    self.assertEqual(ticket_response.status_code, 200, ticket_response.text)
                    self.assertTrue(ticket_response.json()["stream_token"])
                    self.assertGreater(ticket_response.json()["expires_in_sec"], 0)

                    bad_ticket_response = client.post(
                        f"/api/campaigns/{campaign_id}/events/ticket",
                        headers={"X-Player-Id": player_id, "X-Player-Token": "wrong"},
                    )
                    self.assertEqual(bad_ticket_response.status_code, 401)

                    bad_stream_response = client.get(f"/api/campaigns/{campaign_id}/events?stream_token=not-a-ticket")
                    self.assertEqual(bad_stream_response.status_code, 401)

                    raw_campaign = main.load_campaign(campaign_id)
                    world_question_id = main.current_question_id(raw_campaign["setup"]["world"])
                    self.assertTrue(world_question_id)
                    world_response = client.post(
                        f"/api/campaigns/{campaign_id}/setup/world/random/apply",
                        headers=headers,
                        json={"preview_answers": [{"question_id": world_question_id, "value": "Nebelwald"}]},
                    )
                    self.assertEqual(world_response.status_code, 200, world_response.text)
                    self.assertTrue(world_response.json()["completed"])

                    claim_response = client.post(f"/api/campaigns/{campaign_id}/slots/{SLOT_ID}/claim", headers=headers)
                    self.assertEqual(claim_response.status_code, 200, claim_response.text)
                    self.assertEqual(claim_response.json()["campaign"]["claims"][SLOT_ID], player_id)

                    bad_presence_response = client.post(
                        f"/api/campaigns/{campaign_id}/presence/activity",
                        headers={"X-Player-Id": second_player_id, "X-Player-Token": second_player_token},
                        json={"kind": "building_character", "slot_id": SLOT_ID},
                    )
                    self.assertEqual(bad_presence_response.status_code, 403)

                    character_response = client.post(
                        f"/api/campaigns/{campaign_id}/slots/{SLOT_ID}/setup/random/apply",
                        headers=headers,
                        json={"preview_answers": [{"question_id": "char_seed", "value": "Aria"}]},
                    )
                    self.assertEqual(character_response.status_code, 200, character_response.text)
                    character_payload = character_response.json()
                    self.assertTrue(character_payload["started_adventure"])
                    self.assertEqual(character_payload["campaign"]["state"]["meta"]["phase"], "active")

                    presence_response = client.post(
                        f"/api/campaigns/{campaign_id}/presence/activity",
                        headers=headers,
                        json={"kind": "typing_turn", "slot_id": SLOT_ID},
                    )
                    self.assertEqual(presence_response.status_code, 200, presence_response.text)
                    self.assertTrue(presence_response.json()["ok"])
                    self.assertEqual(presence_response.json()["activity"]["slot_id"], SLOT_ID)

                    unauthenticated_turn = client.post(
                        f"/api/campaigns/{campaign_id}/turns",
                        headers={"X-Player-Id": player_id},
                        json={"actor": SLOT_ID, "mode": "do", "text": "Ohne Token."},
                    )
                    self.assertEqual(unauthenticated_turn.status_code, 401)

                    turn_response = client.post(
                        f"/api/campaigns/{campaign_id}/turns",
                        headers=headers,
                        json={"actor": SLOT_ID, "mode": "do", "text": "Ich prüfe die Runen am Tor."},
                    )
                    self.assertEqual(turn_response.status_code, 200, turn_response.text)
                    turn_payload = turn_response.json()
                    self.assertTrue(turn_payload["turn_id"])
                    self.assertEqual(turn_payload["campaign"]["state"]["meta"]["phase"], "active")
                    self.assertEqual(turn_payload["campaign"]["state"]["meta"]["turn"], 2)
                    self.assertEqual(turn_payload["campaign"]["claims"][SLOT_ID], player_id)
                    self.assertEqual(turn_payload["campaign"]["active_turns"][-1]["gm_text_display"], FAKE_NARRATOR_TEXT)
                    json.dumps(turn_payload["campaign"], ensure_ascii=False)

                    reload_response = client.get(f"/api/campaigns/{campaign_id}", headers=headers)
                    self.assertEqual(reload_response.status_code, 200, reload_response.text)
                    reloaded = reload_response.json()
                    json.dumps(reloaded, ensure_ascii=False)
                    self.assertEqual(reloaded["state"]["meta"]["phase"], "active")
                    self.assertEqual(reloaded["state"]["meta"]["turn"], 2)
                    self.assertEqual(reloaded["claims"][SLOT_ID], player_id)
                    self.assertEqual(reloaded["active_turns"][-1]["turn_id"], turn_payload["turn_id"])
                    self.assertEqual(reloaded["active_turns"][-1]["gm_text_display"], FAKE_NARRATOR_TEXT)
                    self.assertIn(FAKE_NARRATOR_TEXT, reloaded["state"]["events"][-1])

                    raw_reload = main.load_campaign(campaign_id)
                    self.assertEqual(raw_reload["claims"][SLOT_ID], player_id)
                    self.assertEqual(raw_reload["turns"][-1]["turn_id"], turn_payload["turn_id"])
                    self.assertEqual(raw_reload["turns"][-1]["patch"], main.blank_patch())
                    self.assertEqual(raw_reload["turns"][-1]["state_after"]["meta"]["turn"], 2)
                    self.assertEqual(raw_reload["turns"][-1]["prompt_payload"], {"fake_narrator": "http_smoke"})

                    next_turn_response = client.post(
                        f"/api/campaigns/{campaign_id}/turns",
                        headers=headers,
                        json={"actor": SLOT_ID, "mode": "say", "text": "Ich bleibe wachsam."},
                    )
                    self.assertEqual(next_turn_response.status_code, 200, next_turn_response.text)
                    self.assertEqual(next_turn_response.json()["campaign"]["state"]["meta"]["turn"], 3)


if __name__ == "__main__":
    unittest.main()
