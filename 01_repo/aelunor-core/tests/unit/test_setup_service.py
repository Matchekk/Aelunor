import unittest
from typing import Any, Dict, List, Optional

from app.services import setup_service


def make_campaign() -> Dict[str, Any]:
    return {
        "state": {"meta": {"phase": "character_setup_open"}},
        "setup": {
            "world": {
                "completed": False,
                "question_order": ["wq_1"],
                "answers": {},
            },
            "characters": {
                "slot_aria": {
                    "completed": False,
                    "question_order": ["cq_1"],
                    "answers": {},
                }
            },
        },
        "claims": {"slot_aria": "player_1"},
    }


class SetupServiceTests(unittest.TestCase):
    def build_dependencies(self, campaign: Dict[str, Any]) -> tuple[setup_service.SetupServiceDependencies, Dict[str, Any]]:
        calls: Dict[str, Any] = {
            "authenticated": 0,
            "require_host": 0,
            "saved_reasons": [],
            "ensure_calls": [],
            "blocking_started": [],
            "blocking_cleared": [],
            "finalize_world": 0,
            "finalize_character": 0,
            "load_calls": 0,
        }
        campaigns_by_id = {"cmp_1": campaign}
        world_question_map = {"wq_1": {"id": "wq_1", "label": "Weltfrage", "type": "text"}}
        character_question_map = {"cq_1": {"id": "cq_1", "label": "Charakterfrage", "type": "text"}}

        def load_campaign(campaign_id: str) -> Dict[str, Any]:
            calls["load_calls"] += 1
            return campaigns_by_id[campaign_id]

        def authenticate_player(_campaign: Dict[str, Any], player_id: Optional[str], _player_token: Optional[str], *, required: bool = False) -> None:
            if required and not player_id:
                raise AssertionError("player id required in test")
            calls["authenticated"] += 1

        def require_host(_campaign: Dict[str, Any], player_id: Optional[str]) -> None:
            calls["require_host"] += 1
            if player_id != "host_1":
                raise AssertionError("host required in test")

        def is_host(_campaign: Dict[str, Any], player_id: Optional[str]) -> bool:
            return player_id == "host_1"

        def current_question_id(setup_node: Dict[str, Any]) -> Optional[str]:
            for qid in setup_node.get("question_order") or []:
                if qid not in (setup_node.get("answers") or {}):
                    return qid
            return None

        def clear_live_activity(_campaign_id: str, _player_id: Optional[str]) -> None:
            return None

        def start_blocking_action(_campaign: Dict[str, Any], *, player_id: Optional[str], kind: str, slot_id: Optional[str] = None) -> None:
            calls["blocking_started"].append((player_id, kind, slot_id))

        def clear_blocking_action(campaign_id: str) -> None:
            calls["blocking_cleared"].append(campaign_id)

        def ensure_question_ai_copy(_campaign: Dict[str, Any], **kwargs: Any) -> None:
            calls["ensure_calls"].append(kwargs)

        def save_campaign(_campaign: Dict[str, Any], *args: Any, **kwargs: Any) -> None:
            calls["saved_reasons"].append(kwargs.get("reason"))

        def build_world_question_state(_campaign: Dict[str, Any], _viewer_id: Optional[str]) -> Optional[Dict[str, Any]]:
            qid = current_question_id(_campaign["setup"]["world"])
            if not qid:
                return None
            return {"question": {"question_id": qid}, "progress": {"answered": len(_campaign["setup"]["world"]["answers"])}}

        def build_character_question_state(_campaign: Dict[str, Any], slot_name: str) -> Optional[Dict[str, Any]]:
            qid = current_question_id(_campaign["setup"]["characters"][slot_name])
            if not qid:
                return None
            return {"question": {"question_id": qid}, "progress": {"answered": len(_campaign["setup"]["characters"][slot_name]["answers"])}}

        def progress_payload(setup_node: Dict[str, Any]) -> Dict[str, Any]:
            return {"answered": len(setup_node.get("answers") or {})}

        def validate_answer_payload(_question: Dict[str, Any], answer: Dict[str, Any]) -> Any:
            return answer

        def store_setup_answer(setup_node: Dict[str, Any], question: Dict[str, Any], stored: Any, *, player_id: Optional[str], source: str = "manual") -> None:
            _ = (player_id, source)
            setup_node.setdefault("answers", {})[question["id"]] = stored

        def build_random_setup_preview(
            _campaign: Dict[str, Any],
            _setup_node: Dict[str, Any],
            _question_map: Dict[str, Dict[str, Any]],
            *,
            setup_type: str,
            **kwargs: Any,
        ) -> List[Dict[str, Any]]:
            _ = kwargs
            if setup_type == "world":
                return [{"question_id": "wq_1", "answer": {"value": "preview_world"}}]
            return [{"question_id": "cq_1", "answer": {"value": "preview_char"}}]

        def apply_random_setup_preview(
            _campaign: Dict[str, Any],
            setup_node: Dict[str, Any],
            _question_map: Dict[str, Dict[str, Any]],
            preview_answers: List[Any],
            *,
            player_id: Optional[str],
        ) -> int:
            _ = player_id
            applied = 0
            for _entry in preview_answers:
                qid = current_question_id(setup_node)
                if not qid:
                    break
                setup_node.setdefault("answers", {})[qid] = {"value": "applied"}
                applied += 1
            return applied

        def finalize_world_setup(_campaign: Dict[str, Any], _player_id: Optional[str]) -> None:
            calls["finalize_world"] += 1
            _campaign["setup"]["world"]["completed"] = True
            _campaign["state"]["meta"]["phase"] = "character_setup_open"

        def finalize_character_setup(_campaign: Dict[str, Any], slot_name: str) -> Optional[Dict[str, Any]]:
            calls["finalize_character"] += 1
            _campaign["setup"]["characters"][slot_name]["completed"] = True
            return {"turn_id": "turn_start_1"}

        def build_world_summary(_campaign: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "resource_name": "Aether",
                "consequence_severity": "mittel",
                "progression_speed": "normal",
                "evolution_cost_policy": "leicht",
                "offclass_xp_multiplier": 0.7,
                "onclass_xp_multiplier": 1.0,
                "campaign_length": "medium",
                "target_turns": {"short": 120},
                "pacing_profile": {"short": {"beats_per_turn": 3}},
            }

        def build_character_summary(_campaign: Dict[str, Any], _slot_name: str) -> Dict[str, Any]:
            return {"display_name": "Aria"}

        def normalize_world_settings(settings: Any) -> Dict[str, Any]:
            return dict(settings or {})

        def apply_world_summary_to_boards(_campaign: Dict[str, Any], _updated_by: Optional[str]) -> None:
            return None

        def apply_character_summary_to_state(_campaign: Dict[str, Any], _slot_name: str) -> None:
            return None

        def campaign_slots(_campaign: Dict[str, Any]) -> List[str]:
            return list((_campaign.get("setup", {}).get("characters", {}) or {}).keys())

        deps = setup_service.SetupServiceDependencies(
            load_campaign=load_campaign,
            authenticate_player=authenticate_player,
            require_host=require_host,
            is_host=is_host,
            current_question_id=current_question_id,
            clear_live_activity=clear_live_activity,
            start_blocking_action=start_blocking_action,
            clear_blocking_action=clear_blocking_action,
            ensure_question_ai_copy=ensure_question_ai_copy,
            save_campaign=save_campaign,
            build_world_question_state=build_world_question_state,
            build_character_question_state=build_character_question_state,
            progress_payload=progress_payload,
            validate_answer_payload=validate_answer_payload,
            store_setup_answer=store_setup_answer,
            build_random_setup_preview=build_random_setup_preview,
            apply_random_setup_preview=apply_random_setup_preview,
            finalize_world_setup=finalize_world_setup,
            finalize_character_setup=finalize_character_setup,
            deep_copy=lambda value: value,
            build_world_summary=build_world_summary,
            build_character_summary=build_character_summary,
            normalize_world_settings=normalize_world_settings,
            apply_world_summary_to_boards=apply_world_summary_to_boards,
            apply_character_summary_to_state=apply_character_summary_to_state,
            campaign_slots=campaign_slots,
            target_turns_defaults={"short": 120},
            pacing_profile_defaults={"short": {"beats_per_turn": 3}},
            world_question_map=world_question_map,
            character_question_map=character_question_map,
        )
        return deps, calls

    def test_world_next_happy_path(self) -> None:
        campaign = make_campaign()
        deps, calls = self.build_dependencies(campaign)

        result = setup_service.next_world_setup_question(
            campaign_id="cmp_1",
            player_id="host_1",
            player_token="token",
            deps=deps,
        )

        self.assertEqual(result["completed"], False)
        self.assertEqual(result["question"]["question_id"], "wq_1")
        self.assertEqual(calls["require_host"], 1)
        self.assertEqual(calls["saved_reasons"], ["world_setup_next"])
        self.assertEqual(calls["blocking_started"][0][1], "building_world")

    def test_world_answer_happy_path(self) -> None:
        campaign = make_campaign()
        deps, calls = self.build_dependencies(campaign)

        result = setup_service.answer_world_setup_question(
            campaign_id="cmp_1",
            question_id="wq_1",
            answer_payload={"question_id": "wq_1", "value": "Nebelreich"},
            player_id="host_1",
            player_token="token",
            deps=deps,
        )

        self.assertEqual(result["completed"], True)
        self.assertIsNone(result["question"])
        self.assertEqual(calls["finalize_world"], 1)
        self.assertEqual(calls["saved_reasons"], ["world_setup_answer"])

    def test_world_random_and_apply_happy_paths(self) -> None:
        campaign = make_campaign()
        deps, calls = self.build_dependencies(campaign)

        random_result = setup_service.randomize_world_setup_question(
            campaign_id="cmp_1",
            mode="single",
            question_id="wq_1",
            preview_answers=[],
            player_id="host_1",
            player_token="token",
            deps=deps,
        )
        apply_result = setup_service.apply_world_setup_random_preview(
            campaign_id="cmp_1",
            preview_answers=[{"question_id": "wq_1"}],
            player_id="host_1",
            player_token="token",
            deps=deps,
        )

        self.assertEqual(random_result["randomized_count"], 1)
        self.assertEqual(apply_result["randomized_count"], 1)
        self.assertEqual(apply_result["completed"], True)
        self.assertEqual(calls["finalize_world"], 1)
        self.assertIn("world_setup_random_apply", calls["saved_reasons"])

    def test_slot_next_happy_path(self) -> None:
        campaign = make_campaign()
        deps, calls = self.build_dependencies(campaign)

        result = setup_service.next_character_setup_question(
            campaign_id="cmp_1",
            slot_name="slot_aria",
            player_id="player_1",
            player_token="token",
            deps=deps,
        )

        self.assertEqual(result["completed"], False)
        self.assertEqual(result["question"]["question_id"], "cq_1")
        self.assertEqual(calls["saved_reasons"], ["character_setup_next"])
        self.assertEqual(calls["blocking_started"][0][1], "building_character")

    def test_slot_answer_happy_path(self) -> None:
        campaign = make_campaign()
        deps, calls = self.build_dependencies(campaign)

        result = setup_service.answer_character_setup_question(
            campaign_id="cmp_1",
            slot_name="slot_aria",
            question_id="cq_1",
            answer_payload={"question_id": "cq_1", "value": "Mati"},
            player_id="player_1",
            player_token="token",
            deps=deps,
        )

        self.assertEqual(result["completed"], True)
        self.assertEqual(result["started_adventure"], True)
        self.assertEqual(result["turn_id"], "turn_start_1")
        self.assertEqual(calls["finalize_character"], 1)
        self.assertIn("character_setup_answer", calls["saved_reasons"])

    def test_slot_random_and_apply_happy_paths(self) -> None:
        campaign = make_campaign()
        deps, calls = self.build_dependencies(campaign)

        random_result = setup_service.randomize_character_setup_question(
            campaign_id="cmp_1",
            slot_name="slot_aria",
            mode="single",
            question_id="cq_1",
            preview_answers=[],
            player_id="player_1",
            player_token="token",
            deps=deps,
        )
        apply_result = setup_service.apply_character_setup_random_preview(
            campaign_id="cmp_1",
            slot_name="slot_aria",
            preview_answers=[{"question_id": "cq_1"}],
            player_id="player_1",
            player_token="token",
            deps=deps,
        )

        self.assertEqual(random_result["randomized_count"], 1)
        self.assertEqual(apply_result["randomized_count"], 1)
        self.assertEqual(apply_result["completed"], True)
        self.assertEqual(apply_result["started_adventure"], True)
        self.assertEqual(calls["finalize_character"], 1)
        self.assertIn("character_setup_random_apply", calls["saved_reasons"])


if __name__ == "__main__":
    unittest.main()
