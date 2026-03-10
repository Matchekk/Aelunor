import unittest
from typing import Any, Dict, Optional

from app.services import context_service


def make_campaign() -> Dict[str, Any]:
    return {
        "state": {"characters": {"slot_aria": {}}, "meta": {}},
    }


class ContextServiceTests(unittest.TestCase):
    def build_deps(self, campaign: Dict[str, Any]) -> context_service.ContextServiceDependencies:
        def load_campaign(_campaign_id: str) -> Dict[str, Any]:
            return campaign

        def authenticate_player(_campaign: Dict[str, Any], _player_id: Optional[str], _player_token: Optional[str], *, required: bool = False) -> None:
            _ = required

        return context_service.ContextServiceDependencies(
            load_campaign=load_campaign,
            authenticate_player=authenticate_player,
            player_claim=lambda _campaign, _player_id: "slot_aria",
            active_party=lambda _campaign: ["slot_aria"],
            campaign_slots=lambda _campaign: ["slot_aria"],
            context_state_signature=lambda _state: "sig",
            parse_context_intent=lambda _text: {"intent": "lookup", "target": "Aelunor"},
            build_context_knowledge_index=lambda _campaign, _state: {"entries": []},
            resolve_context_target=lambda _index, _target: {"status": "not_found", "suggestions": []},
            deterministic_context_result_from_entry=lambda **kwargs: kwargs,
            build_context_result_payload=lambda **kwargs: kwargs,
            extract_story_target_evidence=lambda _campaign, _target, **kwargs: {"facts": [], "sources": []},
            build_reduced_context_snippets=lambda _index, **kwargs: [],
            build_context_result_via_llm=lambda *_args, **_kwargs: None,
            context_result_to_answer_text=lambda result: f"status={result.get('status')}",
        )

    def test_context_query_happy_path(self) -> None:
        campaign = make_campaign()
        deps = self.build_deps(campaign)
        result = context_service.query_campaign_context(
            campaign_id="cmp_1",
            question="Wer ist Aelunor?",
            actor=None,
            player_id="player_1",
            player_token="token",
            deps=deps,
        )
        self.assertEqual(result["actor"], "slot_aria")
        self.assertEqual(result["result"]["status"], "not_in_canon")
        self.assertIn("status=", result["answer"])


if __name__ == "__main__":
    unittest.main()

