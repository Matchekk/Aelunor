import unittest
from typing import Any, Dict, Optional

from fastapi import HTTPException

from app.services import turn_service


class DummyTurnFlowError(Exception):
    def __init__(self) -> None:
        self.phase = "turn_internal"
        self.error_code = "ERR"
        self.cause_class = "Dummy"
        self.cause_message = "dummy"
        self.trace_id = "trace_1"

    def to_client_detail(self) -> str:
        return "dummy"


def make_campaign() -> Dict[str, Any]:
    return {
        "state": {
            "meta": {"phase": "active"},
            "characters": {"slot_aria": {}},
        },
        "turns": [{"turn_id": "turn_1", "turn_number": 1, "status": "active", "actor": "slot_aria"}],
    }


class TurnServiceTests(unittest.TestCase):
    def build_deps(self, campaign: Dict[str, Any]) -> tuple[turn_service.TurnServiceDependencies, Dict[str, Any]]:
        calls: Dict[str, Any] = {"saved": [], "events": []}

        def load_campaign(_campaign_id: str) -> Dict[str, Any]:
            return campaign

        def authenticate_player(_campaign: Dict[str, Any], player_id: Optional[str], _player_token: Optional[str], *, required: bool = False) -> None:
            if required and not player_id:
                raise AssertionError("player required")

        def active_turns(_campaign: Dict[str, Any]) -> Any:
            return _campaign.get("turns", [])

        def intro_state(_campaign: Dict[str, Any]) -> Dict[str, Any]:
            return {"status": "ok"}

        def require_claim(_campaign: Dict[str, Any], _player_id: str, actor: str) -> None:
            if actor != "slot_aria":
                raise AssertionError("unexpected actor")

        def new_turn_trace_context(_campaign_id: str, _slot_id: str, _player_id: Optional[str]) -> Dict[str, Any]:
            return {"trace_id": "trace_123", "last_phase": "turn_internal"}

        def emit_turn_phase_event(_trace_ctx: Dict[str, Any], **kwargs: Any) -> None:
            calls["events"].append(kwargs)

        def clear_live_activity(_campaign_id: str, _player_id: Optional[str]) -> None:
            return None

        def start_blocking_action(_campaign: Dict[str, Any], **kwargs: Any) -> None:
            calls["blocking"] = kwargs

        def clear_blocking_action(_campaign_id: str) -> None:
            calls["cleared"] = True

        def create_turn_record(**kwargs: Any) -> Dict[str, Any]:
            _ = kwargs
            return {"turn_id": "turn_new", "input_text_display": "x"}

        def save_campaign(_campaign: Dict[str, Any], **kwargs: Any) -> None:
            calls["saved"].append(kwargs.get("reason"))

        def classify_turn_exception(exc: Exception, **kwargs: Any) -> Any:
            _ = kwargs
            raise AssertionError(f"unexpected classify call {exc}")

        def remember_recent_story(_campaign: Dict[str, Any]) -> None:
            return None

        def rebuild_memory_summary(_campaign: Dict[str, Any]) -> None:
            return None

        def find_turn(_campaign: Dict[str, Any], _turn_id: str) -> Dict[str, Any]:
            return {
                "turn_id": "turn_1",
                "turn_number": 1,
                "status": "active",
                "actor": "slot_aria",
                "action_type": "do",
                "input_text_raw": "test",
                "input_text_display": "test",
                "gm_text_display": "gm",
            }

        def reset_turn_branch(_campaign: Dict[str, Any], _turn: Dict[str, Any], _new_status: str) -> None:
            return None

        deps = turn_service.TurnServiceDependencies(
            load_campaign=load_campaign,
            authenticate_player=authenticate_player,
            active_turns=active_turns,
            intro_state=intro_state,
            require_claim=require_claim,
            new_turn_trace_context=new_turn_trace_context,
            emit_turn_phase_event=emit_turn_phase_event,
            clear_live_activity=clear_live_activity,
            start_blocking_action=start_blocking_action,
            clear_blocking_action=clear_blocking_action,
            create_turn_record=create_turn_record,
            save_campaign=save_campaign,
            classify_turn_exception=classify_turn_exception,
            turn_flow_error_cls=DummyTurnFlowError,
            remember_recent_story=remember_recent_story,
            rebuild_memory_summary=rebuild_memory_summary,
            find_turn=find_turn,
            reset_turn_branch=reset_turn_branch,
            utc_now=lambda: "2026-01-01T00:00:00Z",
        )
        return deps, calls

    def test_create_turn_happy_path(self) -> None:
        campaign = make_campaign()
        deps, calls = self.build_deps(campaign)
        result = turn_service.create_turn(
            campaign_id="cmp_1",
            actor="slot_aria",
            action_type="do",
            content="Aktion",
            player_id="player_1",
            player_token="token",
            deps=deps,
        )
        self.assertEqual(result["turn_id"], "turn_new")
        self.assertEqual(result["trace_id"], "trace_123")
        self.assertIn("turn_created", calls["saved"])

    def test_create_turn_invalid_phase(self) -> None:
        campaign = make_campaign()
        campaign["state"]["meta"]["phase"] = "world_setup"
        deps, _calls = self.build_deps(campaign)
        with self.assertRaises(HTTPException) as ctx:
            turn_service.create_turn(
                campaign_id="cmp_1",
                actor="slot_aria",
                action_type="do",
                content="Aktion",
                player_id="player_1",
                player_token="token",
                deps=deps,
            )
        self.assertEqual(ctx.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()

