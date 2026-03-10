from typing import Any, Callable, Dict, Optional, Type

from fastapi import APIRouter, Header

from app.services import setup_service


def build_setup_router(
    *,
    setup_answer_model: Type[Any],
    setup_random_model: Type[Any],
    setup_random_apply_model: Type[Any],
    setup_service_dependencies: Callable[[], setup_service.SetupServiceDependencies],
    build_campaign_view: Callable[[Dict[str, Any], Optional[str]], Dict[str, Any]],
) -> APIRouter:
    router = APIRouter()

    @router.post("/api/campaigns/{campaign_id}/setup/world/next")
    def next_world_setup_question(
        campaign_id: str,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        result = setup_service.next_world_setup_question(
            campaign_id=campaign_id,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=setup_service_dependencies(),
        )
        return {
            "completed": result["completed"],
            "question": result["question"],
            "progress": result["progress"],
            "campaign": build_campaign_view(result["campaign"], x_player_id),
        }

    @router.post("/api/campaigns/{campaign_id}/setup/world/answer")
    def answer_world_setup_question(
        campaign_id: str,
        inp: setup_answer_model,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        result = setup_service.answer_world_setup_question(
            campaign_id=campaign_id,
            question_id=inp.question_id,
            answer_payload=inp.model_dump(),
            player_id=x_player_id,
            player_token=x_player_token,
            deps=setup_service_dependencies(),
        )
        return {
            "completed": result["completed"],
            "question": result["question"],
            "progress": result["progress"],
            "campaign": build_campaign_view(result["campaign"], x_player_id),
        }

    @router.post("/api/campaigns/{campaign_id}/setup/world/random")
    def randomize_world_setup_question(
        campaign_id: str,
        inp: setup_random_model,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        result = setup_service.randomize_world_setup_question(
            campaign_id=campaign_id,
            mode=inp.mode,
            question_id=inp.question_id,
            preview_answers=inp.preview_answers,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=setup_service_dependencies(),
        )
        return {
            "mode": result["mode"],
            "question_id": result["question_id"],
            "preview_answers": result["preview_answers"],
            "randomized_count": result["randomized_count"],
        }

    @router.post("/api/campaigns/{campaign_id}/setup/world/random/apply")
    def apply_world_setup_random_preview(
        campaign_id: str,
        inp: setup_random_apply_model,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        result = setup_service.apply_world_setup_random_preview(
            campaign_id=campaign_id,
            preview_answers=inp.preview_answers,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=setup_service_dependencies(),
        )
        return {
            "completed": result["completed"],
            "question": result["question"],
            "progress": result["progress"],
            "campaign": build_campaign_view(result["campaign"], x_player_id),
            "randomized_count": result["randomized_count"],
        }

    @router.post("/api/campaigns/{campaign_id}/setup/finalize")
    def finalize_setup(
        campaign_id: str,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        campaign = setup_service.finalize_setup(
            campaign_id=campaign_id,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=setup_service_dependencies(),
        )
        return {"campaign": build_campaign_view(campaign, x_player_id)}

    @router.post("/api/campaigns/{campaign_id}/slots/{slot_name}/setup/next")
    def next_character_setup_question(
        campaign_id: str,
        slot_name: str,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        result = setup_service.next_character_setup_question(
            campaign_id=campaign_id,
            slot_name=slot_name,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=setup_service_dependencies(),
        )
        return {
            "completed": result["completed"],
            "question": result["question"],
            "progress": result["progress"],
            "campaign": build_campaign_view(result["campaign"], x_player_id),
        }

    @router.post("/api/campaigns/{campaign_id}/slots/{slot_name}/setup/answer")
    def answer_character_setup_question(
        campaign_id: str,
        slot_name: str,
        inp: setup_answer_model,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        result = setup_service.answer_character_setup_question(
            campaign_id=campaign_id,
            slot_name=slot_name,
            question_id=inp.question_id,
            answer_payload=inp.model_dump(),
            player_id=x_player_id,
            player_token=x_player_token,
            deps=setup_service_dependencies(),
        )
        return {
            "completed": result["completed"],
            "question": result["question"],
            "progress": result["progress"],
            "started_adventure": result["started_adventure"],
            "turn_id": result["turn_id"],
            "campaign": build_campaign_view(result["campaign"], x_player_id),
        }

    @router.post("/api/campaigns/{campaign_id}/slots/{slot_name}/setup/random")
    def randomize_character_setup_question(
        campaign_id: str,
        slot_name: str,
        inp: setup_random_model,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        result = setup_service.randomize_character_setup_question(
            campaign_id=campaign_id,
            slot_name=slot_name,
            mode=inp.mode,
            question_id=inp.question_id,
            preview_answers=inp.preview_answers,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=setup_service_dependencies(),
        )
        return {
            "mode": result["mode"],
            "question_id": result["question_id"],
            "preview_answers": result["preview_answers"],
            "randomized_count": result["randomized_count"],
        }

    @router.post("/api/campaigns/{campaign_id}/slots/{slot_name}/setup/random/apply")
    def apply_character_setup_random_preview(
        campaign_id: str,
        slot_name: str,
        inp: setup_random_apply_model,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        result = setup_service.apply_character_setup_random_preview(
            campaign_id=campaign_id,
            slot_name=slot_name,
            preview_answers=inp.preview_answers,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=setup_service_dependencies(),
        )
        return {
            "completed": result["completed"],
            "question": result["question"],
            "progress": result["progress"],
            "started_adventure": result["started_adventure"],
            "turn_id": result["turn_id"],
            "campaign": build_campaign_view(result["campaign"], x_player_id),
            "randomized_count": result["randomized_count"],
        }

    return router

