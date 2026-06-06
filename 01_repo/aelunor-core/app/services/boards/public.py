from typing import Any, Callable, Dict, Optional

from app.core.ids import deep_copy
from app.services.boards.diary import filter_private_diary_content


CampaignState = Dict[str, Any]


def build_public_boards(
    campaign: CampaignState,
    viewer_id: Optional[str],
    *,
    copy_value: Callable[[Any], Any] = deep_copy,
) -> CampaignState:
    boards = copy_value(campaign.get("boards") or {})
    diaries = boards.get("player_diaries") or {}
    for diary_player_id, entry in diaries.items():
        if not isinstance(entry, dict):
            continue
        entry["content"] = filter_private_diary_content(
            entry.get("content", ""),
            viewer_is_owner=diary_player_id == viewer_id,
        )
    return boards
