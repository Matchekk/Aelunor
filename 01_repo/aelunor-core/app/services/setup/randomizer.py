from typing import Any, Dict, List, Optional

from app.helpers import setup_helpers


def validate_answer_payload(question: Dict[str, Any], answer: Dict[str, Any]) -> Any:
    return setup_helpers.validate_answer_payload(question, answer)


def fallback_random_text(
    question_id: str,
    *,
    setup_type: str,
    campaign: Dict[str, Any],
    deps: setup_helpers.SetupHelperDependencies,
    slot_name: Optional[str] = None,
) -> str:
    return setup_helpers.fallback_random_text(
        question_id,
        setup_type=setup_type,
        campaign=campaign,
        slot_name=slot_name,
        deps=deps,
    )


def fallback_random_answer_payload(
    campaign: Dict[str, Any],
    question: Dict[str, Any],
    *,
    setup_type: str,
    deps: setup_helpers.SetupHelperDependencies,
    slot_name: Optional[str] = None,
) -> Dict[str, Any]:
    return setup_helpers.fallback_random_answer_payload(
        campaign,
        question,
        setup_type=setup_type,
        slot_name=slot_name,
        deps=deps,
    )


def generate_random_setup_answer(
    campaign: Dict[str, Any],
    question: Dict[str, Any],
    *,
    setup_type: str,
    deps: setup_helpers.SetupHelperDependencies,
    slot_name: Optional[str] = None,
    setup_node: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return setup_helpers.generate_random_setup_answer(
        campaign,
        question,
        setup_type=setup_type,
        slot_name=slot_name,
        setup_node=setup_node,
        deps=deps,
    )


def store_setup_answer(
    setup_node: Dict[str, Any],
    question: Dict[str, Any],
    stored: Any,
    *,
    player_id: Optional[str],
    deps: setup_helpers.SetupHelperDependencies,
    source: str = "manual",
) -> None:
    return setup_helpers.store_setup_answer(
        setup_node,
        question,
        stored,
        player_id=player_id,
        source=source,
        deps=deps,
    )


def setup_answer_to_input_payload(question: Dict[str, Any], stored: Any) -> Dict[str, Any]:
    return setup_helpers.setup_answer_to_input_payload(question, stored)


def setup_answer_preview_text(question: Dict[str, Any], stored: Any) -> str:
    return setup_helpers.setup_answer_preview_text(question, stored)


def build_random_setup_preview(
    campaign: Dict[str, Any],
    setup_node: Dict[str, Any],
    question_map: Dict[str, Dict[str, Any]],
    *,
    setup_type: str,
    player_id: Optional[str],
    mode: str,
    deps: setup_helpers.SetupHelperDependencies,
    slot_name: Optional[str] = None,
    question_id: Optional[str] = None,
    preview_answers: Optional[List[Any]] = None,
) -> List[Dict[str, Any]]:
    return setup_helpers.build_random_setup_preview(
        campaign,
        setup_node,
        question_map,
        setup_type=setup_type,
        player_id=player_id,
        slot_name=slot_name,
        mode=mode,
        question_id=question_id,
        preview_answers=preview_answers,
        deps=deps,
    )


def apply_random_setup_preview(
    campaign: Dict[str, Any],
    setup_node: Dict[str, Any],
    question_map: Dict[str, Dict[str, Any]],
    preview_answers: List[Any],
    *,
    player_id: Optional[str],
    deps: setup_helpers.SetupHelperDependencies,
) -> int:
    return setup_helpers.apply_random_setup_preview(
        campaign,
        setup_node,
        question_map,
        preview_answers,
        player_id=player_id,
        deps=deps,
    )
