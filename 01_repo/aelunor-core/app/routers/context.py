from typing import Any, Callable, Dict, Optional, Type

from fastapi import APIRouter, Header

from app.services import context_service
from app.services.rag import context_preview


def build_context_router(
    *,
    context_query_model: Type[Any],
    context_service_dependencies: Callable[[], context_service.ContextServiceDependencies],
    rag_context_preview_model: Type[Any],
    rag_context_preview_dependencies: Callable[
        [], context_preview.RagContextPreviewDependencies
    ],
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

    @router.post("/api/campaigns/{campaign_id}/context/rag-preview")
    def preview_campaign_rag_context(
        campaign_id: str,
        inp: rag_context_preview_model,
        x_player_id: Optional[str] = Header(default=None),
        x_player_token: Optional[str] = Header(default=None),
    ) -> Dict[str, Any]:
        return context_preview.preview_campaign_rag_context(
            campaign_id=campaign_id,
            text=inp.text,
            player_id=x_player_id,
            player_token=x_player_token,
            deps=rag_context_preview_dependencies(),
            entities=inp.entities,
            source_types=inp.source_types,
            max_results=inp.max_results,
            max_items=inp.max_items,
            max_chars=inp.max_chars,
        )

    return router
