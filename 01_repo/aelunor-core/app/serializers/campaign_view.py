import copy
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


JsonDict = Dict[str, Any]


def deep_copy(value: Any) -> Any:
    return copy.deepcopy(value)


def active_turns(campaign: JsonDict) -> List[JsonDict]:
    return [turn for turn in campaign.get("turns", []) if turn.get("status") == "active"]


def is_host(campaign: JsonDict, player_id: Optional[str]) -> bool:
    return bool(player_id) and player_id == campaign["campaign_meta"]["host_player_id"]


def is_campaign_player(campaign: JsonDict, player_id: Optional[str]) -> bool:
    return bool(player_id) and player_id in (campaign.get("players") or {})


def build_patch_summary(patch: JsonDict) -> JsonDict:
    return {
        "characters_changed": len((patch.get("characters") or {}).keys()),
        "items_added": len(patch.get("items_new") or {}),
        "plot_updates": len(patch.get("plotpoints_add") or []) + len(patch.get("plotpoints_update") or []),
        "map_updates": len(patch.get("map_add_nodes") or []) + len(patch.get("map_add_edges") or []),
        "events_added": len(patch.get("events_add") or []),
    }


def filter_private_diary_content(content: Any, viewer_is_owner: bool) -> str:
    text = str(content or "")
    if viewer_is_owner or not text:
        return text
    visible_lines = [line for line in text.splitlines() if not line.lstrip().startswith("//")]
    return "\n".join(visible_lines).strip()


def build_public_boards(
    campaign: JsonDict,
    viewer_id: Optional[str],
    *,
    deep_copy: Callable[[Any], Any],
    filter_private_diary_content_fn: Callable[[Any, bool], str],
) -> JsonDict:
    boards = deep_copy(campaign.get("boards") or {})
    diaries = boards.get("player_diaries") or {}
    for diary_player_id, entry in diaries.items():
        if not isinstance(entry, dict):
            continue
        entry["content"] = filter_private_diary_content_fn(
            entry.get("content", ""),
            viewer_is_owner=diary_player_id == viewer_id,
        )
    return boards


def public_turn(
    turn: JsonDict,
    campaign: JsonDict,
    viewer_id: Optional[str],
    *,
    display_name_for_slot: Callable[[JsonDict, str], str],
    is_slot_id: Callable[[str], bool],
    normalize_requests_payload: Callable[..., List[JsonDict]],
    blank_patch: Callable[[], JsonDict],
    is_campaign_player_fn: Callable[[JsonDict, Optional[str]], bool],
) -> JsonDict:
    actor = turn["actor"]
    action_type = turn["action_type"]
    mode_label = {"do": "TUN", "say": "SAGEN", "story": "STORY", "canon": "CANON"}.get(action_type, str(action_type or "").upper())
    requests_payload = normalize_requests_payload(turn.get("requests", []), default_actor=actor)
    can_edit = is_campaign_player_fn(campaign, viewer_id)
    return {
        "turn_id": turn["turn_id"],
        "turn_number": turn["turn_number"],
        "status": turn["status"],
        "actor": actor,
        "actor_display": display_name_for_slot(campaign, actor) if is_slot_id(actor) else actor,
        "player_id": turn.get("player_id"),
        "action_type": action_type,
        "mode": mode_label,
        "input_text_display": turn["input_text_display"],
        "gm_text_display": turn["gm_text_display"],
        "requests": requests_payload,
        "retry_of_turn_id": turn.get("retry_of_turn_id"),
        "created_at": turn["created_at"],
        "updated_at": turn["updated_at"],
        "edited_at": turn.get("edited_at"),
        "edit_count": len(turn.get("edit_history", [])),
        "patch_summary": build_patch_summary(turn.get("patch") or blank_patch()),
        "narrator_patch": turn.get("narrator_patch") or blank_patch(),
        "extractor_patch": turn.get("extractor_patch") or blank_patch(),
        "source_mode": turn.get("source_mode", turn.get("action_type")),
        "canon_applied": bool(turn.get("canon_applied")),
        "attribute_profile": deep_copy(turn.get("attribute_profile") or {}),
        "combat_resolution": deep_copy(turn.get("combat_resolution") or {}),
        "resource_deltas_applied": deep_copy(turn.get("resource_deltas_applied") or {}),
        "progression_events": deep_copy(turn.get("progression_events") or []),
        "canon_gate": deep_copy(turn.get("canon_gate") or {}),
        "codex_updates": deep_copy(turn.get("codex_updates") or []),
        "can_edit": can_edit,
        "can_undo": can_edit and turn["status"] == "active",
        "can_retry": can_edit and turn["status"] == "active",
    }


@dataclass(frozen=True)
class CampaignViewDependencies:
    normalize_campaign: Callable[[JsonDict], JsonDict]
    deep_copy: Callable[[Any], Any]
    build_setup_runtime: Callable[[JsonDict, Optional[str]], JsonDict]
    available_slots: Callable[[JsonDict], List[JsonDict]]
    active_party: Callable[[JsonDict], List[str]]
    display_name_for_slot: Callable[[JsonDict, str], str]
    normalize_world_time: Callable[[JsonDict], JsonDict]
    build_public_boards: Callable[[JsonDict, Optional[str]], JsonDict]
    active_turns: Callable[[JsonDict], List[JsonDict]]
    public_turn: Callable[[JsonDict, JsonDict, Optional[str]], JsonDict]
    build_party_overview: Callable[[JsonDict], List[JsonDict]]
    campaign_slots: Callable[[JsonDict], List[str]]
    public_player: Callable[[str, JsonDict], JsonDict]
    build_viewer_context: Callable[[JsonDict, Optional[str]], JsonDict]
    live_snapshot: Callable[[str], JsonDict]


def build_campaign_view(campaign: JsonDict, viewer_id: Optional[str], *, deps: CampaignViewDependencies) -> JsonDict:
    # View assembly must stay passive and never mutate the live campaign object.
    normalized_campaign = deps.normalize_campaign(deps.deep_copy(campaign))
    active_party_slots = deps.active_party(normalized_campaign)

    return {
        "campaign_meta": {
            "campaign_id": normalized_campaign["campaign_meta"]["campaign_id"],
            "title": normalized_campaign["campaign_meta"]["title"],
            "created_at": normalized_campaign["campaign_meta"]["created_at"],
            "updated_at": normalized_campaign["campaign_meta"]["updated_at"],
            "status": normalized_campaign["campaign_meta"]["status"],
            "host_player_id": normalized_campaign["campaign_meta"]["host_player_id"],
        },
        "state": normalized_campaign["state"],
        "setup": normalized_campaign["setup"],
        "setup_runtime": deps.build_setup_runtime(normalized_campaign, viewer_id),
        "available_slots": deps.available_slots(normalized_campaign),
        "claims": normalized_campaign["claims"],
        "active_party": active_party_slots,
        "display_party": [
            {"slot_id": slot_name, "display_name": deps.display_name_for_slot(normalized_campaign, slot_name)}
            for slot_name in active_party_slots
        ],
        "world_time": deps.normalize_world_time(normalized_campaign["state"]["meta"]),
        "boards": deps.build_public_boards(normalized_campaign, viewer_id),
        "active_turns": [deps.public_turn(turn, normalized_campaign, viewer_id) for turn in deps.active_turns(normalized_campaign)],
        "party_overview": deps.build_party_overview(normalized_campaign),
        "character_sheet_slots": deps.campaign_slots(normalized_campaign),
        "ui_panels": {
            "sidebar": ["party", "chars", "diary", "map", "events"],
            "settings": ["session", "plot", "note", "cards", "world", "memory"],
        },
        "players": [deps.public_player(player_id, player) for player_id, player in normalized_campaign.get("players", {}).items()],
        "viewer_context": deps.build_viewer_context(normalized_campaign, viewer_id),
        "live": deps.live_snapshot(normalized_campaign["campaign_meta"]["campaign_id"]),
    }
