from typing import Any, Dict, List, Optional

from app.config.runtime import MAX_PLAYERS
from app.core.ids import utc_now
from app.services.state_basics import is_slot_id, ordered_slots, slot_id, slot_index


CampaignState = Dict[str, Any]
SLOT_PREFIX = "slot_"


def campaign_slots(campaign: CampaignState) -> List[str]:
    keys = list((campaign.get("state", {}).get("characters") or {}).keys())
    if not keys:
        keys = list((campaign.get("claims") or {}).keys())
    if not keys:
        keys = list((campaign.get("setup", {}).get("characters") or {}).keys())
    return ordered_slots([key for key in keys if is_slot_id(key)], slot_prefix=SLOT_PREFIX)


def player_claim(campaign: CampaignState, player_id: Optional[str]) -> Optional[str]:
    if not player_id:
        return None
    for slot_name, claimed_player_id in (campaign.get("claims") or {}).items():
        if claimed_player_id == player_id:
            return slot_name
    return None


def display_name_for_slot(campaign: CampaignState, slot_name: str) -> str:
    bio = (campaign.get("state", {}).get("characters", {}).get(slot_name) or {}).get("bio", {})
    return bio.get("name") or f"Slot {slot_index(slot_name, slot_prefix=SLOT_PREFIX)}"


def active_party(campaign: CampaignState) -> List[str]:
    slots = []
    setup_chars = campaign.get("setup", {}).get("characters", {})
    for slot_name in campaign_slots(campaign):
        if campaign.get("claims", {}).get(slot_name) and setup_chars.get(slot_name, {}).get("completed"):
            slots.append(slot_name)
    return slots


def expected_setup_slots(campaign: CampaignState) -> List[str]:
    summary = ((campaign.get("setup") or {}).get("world") or {}).get("summary") or {}
    count = int(summary.get("player_count") or 1)
    count = max(1, min(MAX_PLAYERS, count))
    slots = campaign_slots(campaign)
    if len(slots) >= count:
        return slots[:count]
    return [slot_id(index, slot_prefix=SLOT_PREFIX) for index in range(1, count + 1)]


def setup_slot_statuses(campaign: CampaignState) -> List[CampaignState]:
    setup_chars = ((campaign.get("setup") or {}).get("characters") or {})
    statuses: List[CampaignState] = []
    for slot_name in expected_setup_slots(campaign):
        owner = (campaign.get("claims") or {}).get(slot_name)
        node = setup_chars.get(slot_name) or {}
        if not owner:
            status = "unclaimed"
        elif node.get("completed"):
            status = "ready"
        else:
            status = "in_progress"
        statuses.append(
            {
                "slot_id": slot_name,
                "display_name": display_name_for_slot(campaign, slot_name),
                "claimed_by": owner,
                "status": status,
                "completed": bool(node.get("completed")),
            }
        )
    return statuses


def public_player(player_id: str, player: CampaignState) -> CampaignState:
    return {
        "player_id": player_id,
        "display_name": player.get("display_name", ""),
        "joined_at": player.get("joined_at"),
        "last_seen_at": player.get("last_seen_at"),
    }


def default_player_diary_entry(player_id: str, display_name: str) -> CampaignState:
    now = utc_now()
    return {
        "player_id": player_id,
        "display_name": display_name,
        "content": "",
        "updated_at": now,
        "updated_by": player_id,
    }


def compact_conditions(character: CampaignState) -> List[str]:
    names = []
    for effect in character.get("effects", []) or []:
        if effect.get("visible", True) and effect.get("name"):
            names.append(effect["name"])
    if not names:
        names = [entry for entry in character.get("conditions", []) or [] if entry]
    return names[:3]


def available_slots(campaign: CampaignState, *, ports: Any) -> List[CampaignState]:
    players = campaign.get("players", {})
    out = []
    for slot_name in campaign_slots(campaign):
        owner = campaign.get("claims", {}).get(slot_name)
        owner_name = players.get(owner, {}).get("display_name") if owner else None
        setup_node = campaign.get("setup", {}).get("characters", {}).get(slot_name, {})
        character = (campaign.get("state", {}).get("characters", {}) or {}).get(slot_name) or ports.blank_character_state(slot_name)
        character = ports.normalize_character_state(character, slot_name, campaign.get("state", {}).get("items", {}) or {})
        current_class = ports.normalize_class_current(character.get("class_current"))
        out.append(
            {
                "slot_id": slot_name,
                "claimed_by": owner,
                "claimed_by_name": owner_name,
                "completed": bool(setup_node.get("completed")),
                "display_name": display_name_for_slot(campaign, slot_name),
                "summary": setup_node.get("summary", {}),
                "class_name": (current_class or {}).get("name", ""),
                "class_rank": (current_class or {}).get("rank", ""),
                "class_level": (current_class or {}).get("level", 0),
                "class_level_max": (current_class or {}).get("level_max", 10),
            }
        )
    return out


def build_party_overview(campaign: CampaignState, *, ports: Any) -> List[CampaignState]:
    overview = []
    world_settings = (((campaign.get("state") or {}).get("world") or {}).get("settings") or {})
    for slot_name in campaign_slots(campaign):
        character = (campaign.get("state", {}).get("characters", {}) or {}).get(slot_name) or ports.blank_character_state(slot_name)
        character = ports.normalize_character_state(character, slot_name, campaign.get("state", {}).get("items", {}) or {})
        current_class = ports.normalize_class_current(character.get("class_current"))
        level = int(character.get("level", 1) or 1)
        xp_to_next = int(character.get("xp_to_next", ports.next_character_xp_for_level(level)) or ports.next_character_xp_for_level(level))
        overview.append(
            {
                "slot_id": slot_name,
                "display_name": display_name_for_slot(campaign, slot_name),
                "claimed_by": campaign.get("claims", {}).get(slot_name),
                "claimed_by_name": campaign.get("players", {}).get(campaign.get("claims", {}).get(slot_name), {}).get("display_name"),
                "scene_id": character.get("scene_id", ""),
                "scene_name": ports.derive_scene_name(campaign, slot_name),
                "class_name": (current_class or {}).get("name", ""),
                "class_rank": (current_class or {}).get("rank", ""),
                "class_level": (current_class or {}).get("level"),
                "class_level_max": (current_class or {}).get("level_max"),
                "level": level,
                "xp_current": int(character.get("xp_current", 0) or 0),
                "xp_to_next": xp_to_next,
                "hp_current": int(character.get("hp_current", 0) or 0),
                "hp_max": int(character.get("hp_max", 0) or 0),
                "sta_current": int(character.get("sta_current", 0) or 0),
                "sta_max": int(character.get("sta_max", 0) or 0),
                "res_current": int(character.get("res_current", 0) or 0),
                "res_max": int(character.get("res_max", 0) or 0),
                "resource_name": ports.resource_name_for_character(character, world_settings),
                "carry_current": int(character.get("carry_current", 0) or 0),
                "carry_max": int(character.get("carry_max", 0) or 0),
                "hp_pct": ports.clamp(int(round((int(character.get("hp_current", 0) or 0) / max(1, int(character.get("hp_max", 1) or 1))) * 100)), 0, 100),
                "sta_pct": ports.clamp(int(round((int(character.get("sta_current", 0) or 0) / max(1, int(character.get("sta_max", 1) or 1))) * 100)), 0, 100),
                "res_pct": ports.clamp(int(round((int(character.get("res_current", 0) or 0) / max(1, int(character.get("res_max", 1) or 1))) * 100)), 0, 100),
                "injury_count": len(character.get("injuries", []) or []),
                "scar_count": len(character.get("scars", []) or []),
                "conditions": compact_conditions(character),
                "in_combat": bool(((character.get("derived") or {}).get("combat_flags") or {}).get("in_combat", False)),
                "appearance_short": ((character.get("appearance") or {}).get("summary_short") or ""),
                "age": int(((character.get("bio") or {}).get("age_years", 0) or 0)),
                "age_stage": str(((character.get("bio") or {}).get("age_stage", "")) or ""),
            }
        )
    return overview
