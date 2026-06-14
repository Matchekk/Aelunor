"""Developer router for the Campaign Second Brain (read-only overview).

GET /api/campaigns/{campaign_id}/brain — aggregate counts + meta only, no node
content or secrets. Not a player-facing UI. The overview function is injected
so it can be tested and bound to a campaigns dir.
"""

from typing import Any, Callable, Dict

from fastapi import APIRouter


def build_brain_router(*, brain_overview: Callable[[str], Dict[str, Any]]) -> APIRouter:
    router = APIRouter()

    @router.get("/api/campaigns/{campaign_id}/brain")
    def get_campaign_brain(campaign_id: str) -> Dict[str, Any]:
        return brain_overview(campaign_id)

    return router
