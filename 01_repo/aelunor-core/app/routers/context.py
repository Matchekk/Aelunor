from typing import Any, Callable, Dict, Optional, Type

from fastapi import APIRouter, Header

from app.services import context_service


def build_context_router(
    *,
    context_query_model: Type[Any],
    context_service_dependencies: Callable[[], context_service.ContextServiceDependencies],
) -> APIRouter:
    router = APIRouter()

    @router.post("/api/campaigns/{campaign_id}/context/query")
    def query_campaign_context(
        campaign_id: str,
        inp: context_query_model,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        return context_service.query_campaign_context(
            campaign_id=campaign_id,
            question=inp.text,
            actor=inp.actor,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=context_service_dependencies(),
        )

    return router

