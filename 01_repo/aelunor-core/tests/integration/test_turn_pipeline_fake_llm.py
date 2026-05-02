from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import patch


SLOT_ID = "slot_1"
FAKE_LLM_PIPELINE_MARKER = "FAKE_LLM_PIPELINE_MARKER"


def _long_fake_story() -> str:
    sentence = (
        "Aria untersucht die Runen am Tor und erkennt, dass ihr kaltes Licht auf ihre letzte Handlung reagiert. "
        f"{FAKE_LLM_PIPELINE_MARKER} bleibt als Prüfzeichen sichtbar, während die Gruppe die Lage ruhig bewertet. "
        "Die Steine öffnen sich nicht sofort, aber ein neuer sicherer Ansatz entsteht: Aria kann die Zeichenfolge "
        "weiterlesen, ohne den bisherigen Kanon zu brechen. "
    )
    return sentence * 5


class TurnPipelineFakeLlmTests(unittest.TestCase):
    def test_real_turn_pipeline_uses_fake_llm_and_applies_patch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aelunor-turn-pipeline-") as temp_dir:
            from app import main
            from app.services import state_engine, turn_engine

            turn_engine.configure(main.__dict__)
            campaigns_dir = str(Path(temp_dir) / "campaigns")
            Path(campaigns_dir).mkdir(parents=True, exist_ok=True)
            trace_events: list[Dict[str, Any]] = []
            fake_llm_calls: list[Dict[str, Any]] = []

            def fake_ensure_question_ai_copy(*_args: Any, **_kwargs: Any) -> str:
                return "Turn pipeline setup copy"

            def fail_real_network_post(*_args: Any, **_kwargs: Any) -> None:
                raise AssertionError("Turn pipeline test must not call real Ollama over the network")

            def fail_unexpected_schema_llm(*_args: Any, **_kwargs: Any) -> Dict[str, Any]:
                raise AssertionError("Fake story should not require story rewrite/compression LLM calls")

            def fake_call_ollama_json(
                system: str,
                user: str,
                *,
                temperature: Optional[float] = None,
                repeat_penalty: Optional[float] = None,
                trace_ctx: Optional[Dict[str, Any]] = None,
            ) -> Dict[str, Any]:
                fake_llm_calls.append(
                    {
                        "system_len": len(system),
                        "user_len": len(user),
                        "temperature": temperature,
                        "repeat_penalty": repeat_penalty,
                        "trace_id": (trace_ctx or {}).get("trace_id"),
                    }
                )
                patch_payload = main.blank_patch()
                patch_payload["events_add"] = [f"{FAKE_LLM_PIPELINE_MARKER}: Aria markiert die gelesenen Runen."]
                return {
                    "story": _long_fake_story(),
                    "patch": patch_payload,
                    "requests": [{"type": "none", "actor": SLOT_ID}],
                }

            def fake_call_canon_extractor(*_args: Any, **_kwargs: Any) -> Dict[str, Any]:
                return main.blank_patch()

            def fake_call_npc_extractor(*_args: Any, **_kwargs: Any) -> list[Dict[str, Any]]:
                return []

            def fail_progression_extractor(*_args: Any, **_kwargs: Any) -> Dict[str, Any]:
                raise AssertionError("Fake story should not trigger progression extractor LLM calls")

            def capture_turn_phase_event(_trace_ctx: Optional[Dict[str, Any]], **kwargs: Any) -> None:
                trace_events.append(dict(kwargs))

            patches = [
                patch.object(main, "DATA_DIR", temp_dir),
                patch.object(main, "CAMPAIGNS_DIR", campaigns_dir),
                patch.object(state_engine, "DATA_DIR", temp_dir),
                patch.object(state_engine, "CAMPAIGNS_DIR", campaigns_dir),
                patch.object(main, "ensure_question_ai_copy", fake_ensure_question_ai_copy),
                patch.object(main.requests, "post", fail_real_network_post),
                patch.object(turn_engine, "requests", main.requests),
                patch.object(turn_engine, "call_ollama_json", fake_call_ollama_json),
                patch.object(turn_engine, "call_ollama_schema", fail_unexpected_schema_llm),
                patch.object(turn_engine, "call_canon_extractor", fake_call_canon_extractor),
                patch.object(turn_engine, "call_npc_extractor", fake_call_npc_extractor),
                patch.object(turn_engine, "call_progression_canon_extractor", fail_progression_extractor),
                patch.object(turn_engine, "emit_turn_phase_event", capture_turn_phase_event),
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
                patches[10],
                patches[11],
                patches[12],
            ):
                main.ensure_campaign_storage()
                created = main.create_campaign_record("Pipeline Campaign", "Host")
                campaign = created["campaign"]
                campaign_id = campaign["campaign_meta"]["campaign_id"]
                player_id = created["player_id"]

                campaign.setdefault("claims", {})[SLOT_ID] = player_id
                campaign["setup"]["world"]["completed"] = True
                campaign["setup"].setdefault("characters", {})[SLOT_ID] = {
                    "completed": True,
                    "question_queue": [],
                    "answers": {},
                    "summary": {},
                    "raw_transcript": [],
                    "question_runtime": {},
                }
                character = main.blank_character_state(SLOT_ID)
                character["bio"]["name"] = "Aria"
                character["class_current"] = main.default_class_current()
                campaign["state"].setdefault("characters", {})[SLOT_ID] = character
                campaign["state"]["meta"]["phase"] = "active"
                campaign["state"]["meta"]["turn"] = 0
                campaign["state"]["meta"]["intro_state"] = {
                    "status": "generated",
                    "generated_turn_id": "turn_intro_fake",
                    "last_error": "",
                }

                turn = turn_engine.create_turn_record(
                    campaign=campaign,
                    actor=SLOT_ID,
                    player_id=player_id,
                    action_type="do",
                    content="Ich prüfe die Runen am Tor.",
                    request_received_ts=123.0,
                    trace_ctx={"trace_id": "trace_fake_llm_pipeline"},
                )

                self.assertEqual(len(fake_llm_calls), 1)
                self.assertTrue(turn["turn_id"].startswith("turn_"))
                self.assertEqual(turn["actor"], SLOT_ID)
                self.assertEqual(turn["player_id"], player_id)
                self.assertIn(FAKE_LLM_PIPELINE_MARKER, turn["gm_text_display"])
                self.assertIn(FAKE_LLM_PIPELINE_MARKER, turn["patch"]["events_add"][0])
                self.assertIn(FAKE_LLM_PIPELINE_MARKER, campaign["state"]["events"][-1])
                self.assertEqual(turn["state_before"]["meta"]["turn"], 0)
                self.assertEqual(turn["state_after"]["meta"]["turn"], 1)
                self.assertEqual(campaign["state"]["meta"]["turn"], 1)
                self.assertEqual(campaign["turns"][-1]["turn_id"], turn["turn_id"])
                self.assertEqual(turn["narrator_patch"]["events_add"], [f"{FAKE_LLM_PIPELINE_MARKER}: Aria markiert die gelesenen Runen."])
                self.assertEqual(turn["extractor_patch"], main.blank_patch())
                self.assertFalse([event for event in trace_events if event.get("success") is False])
                self.assertIn("patch_apply", {str(event.get("phase")) for event in trace_events})
                json.dumps(turn, ensure_ascii=False)
                json.dumps(campaign, ensure_ascii=False)
                self.assertTrue((Path(campaigns_dir) / f"{campaign_id}.json").is_file())
                self.assertTrue(str(Path(campaigns_dir)).startswith(temp_dir))


if __name__ == "__main__":
    unittest.main()
