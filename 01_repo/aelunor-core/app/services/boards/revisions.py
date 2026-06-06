from typing import Any, Callable, Dict, Optional


CampaignState = Dict[str, Any]


def log_board_revision(
    campaign: CampaignState,
    *,
    board: str,
    op: str,
    updated_by: Optional[str],
    previous: Any,
    current: Any,
    make_id: Callable[[str], str],
    utc_now: Callable[[], str],
    item_id: Optional[str] = None,
) -> None:
    campaign.setdefault("board_revisions", []).append(
        {
            "revision_id": make_id("boardrev"),
            "board": board,
            "op": op,
            "item_id": item_id,
            "updated_by": updated_by,
            "updated_at": utc_now(),
            "previous": previous,
            "current": current,
        }
    )
