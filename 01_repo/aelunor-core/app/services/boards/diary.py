from typing import Any, Dict

from app.core.ids import utc_now


CampaignState = Dict[str, Any]


def default_player_diary_entry(player_id: str, display_name: str) -> CampaignState:
    now = utc_now()
    return {
        "player_id": player_id,
        "display_name": display_name,
        "content": "",
        "updated_at": now,
        "updated_by": player_id,
    }


def filter_private_diary_content(content: Any, viewer_is_owner: bool) -> str:
    text = str(content or "")
    if viewer_is_owner or not text:
        return text
    visible_lines = [line for line in text.splitlines() if not line.lstrip().startswith("//")]
    return "\n".join(visible_lines).strip()
