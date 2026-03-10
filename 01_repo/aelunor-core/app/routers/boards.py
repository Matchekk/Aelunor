from typing import Any, Callable, Dict, Optional, Type

from fastapi import APIRouter, Header

from app.services import boards_service


def build_boards_router(
    *,
    plot_essentials_patch_model: Type[Any],
    authors_note_patch_model: Type[Any],
    player_diary_patch_model: Type[Any],
    story_card_create_model: Type[Any],
    story_card_patch_model: Type[Any],
    world_info_create_model: Type[Any],
    world_info_patch_model: Type[Any],
    boards_service_dependencies: Callable[[], boards_service.BoardsServiceDependencies],
    build_campaign_view: Callable[[Dict[str, Any], Optional[str]], Dict[str, Any]],
) -> APIRouter:
    router = APIRouter()

    @router.patch("/api/campaigns/{campaign_id}/boards/plot-essentials")
    def patch_plot_essentials(
        campaign_id: str,
        inp: plot_essentials_patch_model,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        campaign = boards_service.patch_plot_essentials(
            campaign_id=campaign_id,
            payload=inp.model_dump(exclude_none=True),
            player_id=x_player_id,
            player_token=x_player_token,
            deps=boards_service_dependencies(),
        )
        return {"campaign": build_campaign_view(campaign, x_player_id)}

    @router.patch("/api/campaigns/{campaign_id}/boards/authors-note")
    def patch_authors_note(
        campaign_id: str,
        inp: authors_note_patch_model,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        campaign = boards_service.patch_authors_note(
            campaign_id=campaign_id,
            content=inp.content,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=boards_service_dependencies(),
        )
        return {"campaign": build_campaign_view(campaign, x_player_id)}

    @router.patch("/api/campaigns/{campaign_id}/boards/diary/{player_id}")
    def patch_player_diary(
        campaign_id: str,
        player_id: str,
        inp: player_diary_patch_model,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        campaign = boards_service.patch_player_diary(
            campaign_id=campaign_id,
            diary_player_id=player_id,
            content=inp.content,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=boards_service_dependencies(),
        )
        return {"campaign": build_campaign_view(campaign, x_player_id)}

    @router.post("/api/campaigns/{campaign_id}/boards/story-cards")
    def create_story_card(
        campaign_id: str,
        inp: story_card_create_model,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        campaign = boards_service.create_story_card(
            campaign_id=campaign_id,
            title=inp.title,
            kind=inp.kind,
            content=inp.content,
            tags=inp.tags,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=boards_service_dependencies(),
        )
        return {"campaign": build_campaign_view(campaign, x_player_id)}

    @router.patch("/api/campaigns/{campaign_id}/boards/story-cards/{card_id}")
    def patch_story_card(
        campaign_id: str,
        card_id: str,
        inp: story_card_patch_model,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        campaign = boards_service.patch_story_card(
            campaign_id=campaign_id,
            card_id=card_id,
            payload=inp.model_dump(exclude_none=True),
            player_id=x_player_id,
            player_token=x_player_token,
            deps=boards_service_dependencies(),
        )
        return {"campaign": build_campaign_view(campaign, x_player_id)}

    @router.post("/api/campaigns/{campaign_id}/boards/world-info")
    def create_world_info(
        campaign_id: str,
        inp: world_info_create_model,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        campaign = boards_service.create_world_info(
            campaign_id=campaign_id,
            title=inp.title,
            category=inp.category,
            content=inp.content,
            tags=inp.tags,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=boards_service_dependencies(),
        )
        return {"campaign": build_campaign_view(campaign, x_player_id)}

    @router.patch("/api/campaigns/{campaign_id}/boards/world-info/{entry_id}")
    def patch_world_info(
        campaign_id: str,
        entry_id: str,
        inp: world_info_patch_model,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        campaign = boards_service.patch_world_info(
            campaign_id=campaign_id,
            entry_id=entry_id,
            payload=inp.model_dump(exclude_none=True),
            player_id=x_player_id,
            player_token=x_player_token,
            deps=boards_service_dependencies(),
        )
        return {"campaign": build_campaign_view(campaign, x_player_id)}

    return router

