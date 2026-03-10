import copy
import logging
import unittest

import requests
from fastapi import HTTPException

from app.services import turn_engine


def configure_engine_for_tests() -> None:
    turn_engine.configure(
        {
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
        }
    )


class TurnEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        configure_engine_for_tests()

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


if __name__ == "__main__":
    unittest.main()
