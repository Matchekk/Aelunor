from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from fastapi import HTTPException


CampaignState = Dict[str, Any]


@dataclass(frozen=True)
class CharacterSheetPorts:
    normalize_character_state: Callable[..., CampaignState]
    reconcile_canonical_resources: Callable[[CampaignState, CampaignState], None]
    build_compat_resources_view: Callable[[CampaignState, CampaignState], CampaignState]
    list_inventory_items: Callable[[CampaignState], List[CampaignState]]
    ensure_item_shape: Callable[[str, CampaignState], CampaignState]
    resource_name_for_character: Callable[[CampaignState, CampaignState], str]
    normalize_class_current: Callable[[Any], Any]
    normalize_dynamic_skill_state: Callable[..., CampaignState]
    class_affinity_match: Callable[[List[str], List[str]], bool]
    effective_skill_progress_multiplier: Callable[[CampaignState, CampaignState, CampaignState], float]
    skill_rank_sort_value: Callable[[Any], int]
    build_skill_fusion_hints: Callable[..., List[CampaignState]]
    calculate_derived_bonus: Callable[[CampaignState, CampaignState, str], int]
    world_attribute_scale: Callable[[CampaignState], CampaignState]
    display_name_for_slot: Callable[[CampaignState, str], str]
    derive_scene_name: Callable[[CampaignState, str], str]
    next_character_xp_for_level: Callable[[int], int]


def build_character_sheet_view(
    campaign: CampaignState,
    slot_name: str,
    *,
    ports: CharacterSheetPorts,
) -> CampaignState:
    character = (campaign.get("state", {}).get("characters", {}) or {}).get(slot_name)
    if not character:
        raise HTTPException(status_code=404, detail="Charakter nicht gefunden.")
    character = ports.normalize_character_state(character, slot_name, campaign.get("state", {}).get("items", {}) or {})
    world_settings = (((campaign.get("state") or {}).get("world") or {}).get("settings") or {})
    ports.reconcile_canonical_resources(character, world_settings)
    bio = character.get("bio", {})
    resources = ports.build_compat_resources_view(character, world_settings)
    derived = character.get("derived", {})
    skills = character.get("skills", {})
    equipment = character.get("equipment", {})
    inventory_items = ports.list_inventory_items(character)
    items_db = campaign.get("state", {}).get("items", {}) or {}
    item_views = []
    for entry in inventory_items:
        item = ports.ensure_item_shape(entry["item_id"], items_db.get(entry["item_id"], {}))
        item_views.append(
            {
                "item_id": entry["item_id"],
                "name": item.get("name", entry["item_id"]),
                "stack": entry["stack"],
                "rarity": item.get("rarity", "common"),
                "weight": item.get("weight", 0),
                "slot": item.get("slot", ""),
                "cursed": item.get("cursed", False),
            }
        )
    equipment_view = {}
    for equip_slot, item_id in equipment.items():
        item = ports.ensure_item_shape(item_id, items_db.get(item_id, {})) if item_id else {}
        equipment_view[equip_slot] = {
            "item_id": item_id,
            "name": item.get("name", "Leer") if item_id else "Leer",
            "rarity": item.get("rarity", "") if item_id else "",
            "weight": item.get("weight", 0) if item_id else 0,
        }
    resource_name = ports.resource_name_for_character(character, world_settings)
    current_class = ports.normalize_class_current(character.get("class_current"))
    ascension_plotpoint = None
    current_quest_id = (((current_class or {}).get("ascension") or {}).get("quest_id"))
    if current_quest_id:
        ascension_plotpoint = next(
            (entry for entry in (campaign.get("state", {}).get("plotpoints") or []) if entry.get("id") == current_quest_id),
            None,
        )
    skill_views = []
    for skill_id, skill_value in (skills or {}).items():
        skill_state = ports.normalize_dynamic_skill_state(
            skill_value,
            skill_id=skill_id,
            skill_name=(skill_value or {}).get("name", skill_id) if isinstance(skill_value, dict) else skill_id,
            resource_name=resource_name,
            unlocked_from=(skill_value or {}).get("unlocked_from", "Story") if isinstance(skill_value, dict) else "Story",
        )
        skill_views.append(
            {
                "id": skill_state.get("id"),
                "name": skill_state.get("name"),
                "level": skill_state.get("level", 1),
                "level_max": skill_state.get("level_max", 10),
                "xp": skill_state.get("xp", 0),
                "next_xp": skill_state.get("next_xp", 100),
                "rank": skill_state.get("rank", "F"),
                "mastery": skill_state.get("mastery", 0),
                "tags": skill_state.get("tags", []),
                "description": skill_state.get("description", ""),
                "cost": skill_state.get("cost"),
                "price": skill_state.get("price"),
                "cooldown_turns": skill_state.get("cooldown_turns"),
                "unlocked_from": skill_state.get("unlocked_from"),
                "synergy_notes": skill_state.get("synergy_notes"),
                "class_match": ports.class_affinity_match(
                    skill_state.get("tags") or [],
                    (current_class or {}).get("affinity_tags") or [],
                ),
                "effective_progress_multiplier": ports.effective_skill_progress_multiplier(
                    character,
                    skill_state,
                    world_settings,
                ),
            }
        )
    skill_views.sort(
        key=lambda entry: (ports.skill_rank_sort_value(entry.get("rank")), entry.get("level", 1), entry.get("name", "")),
        reverse=True,
    )
    fusion_hints = ports.build_skill_fusion_hints(skills, resource_name=resource_name)
    modifier_summary = {
        "defense": ports.calculate_derived_bonus(character, items_db, "defense"),
        "initiative": ports.calculate_derived_bonus(character, items_db, "initiative"),
        "attack_rating_mainhand": ports.calculate_derived_bonus(character, items_db, "attack_rating_mainhand"),
        "attack_rating_offhand": ports.calculate_derived_bonus(character, items_db, "attack_rating_offhand"),
    }
    attribute_scale = ports.world_attribute_scale(campaign)
    level = int(character.get("level", 1) or 1)
    return {
        "slot_id": slot_name,
        "display_name": ports.display_name_for_slot(campaign, slot_name),
        "scene_id": character.get("scene_id", ""),
        "scene_name": ports.derive_scene_name(campaign, slot_name),
        "claimed_by_name": campaign.get("players", {}).get(campaign.get("claims", {}).get(slot_name), {}).get("display_name"),
        "sheet": {
            "overview": {
                "bio": bio,
                "resources": resources,
                "resource_label": resource_name,
                "class_current": current_class,
                "character_progression": {
                    "level": level,
                    "xp_current": int(character.get("xp_current", 0) or 0),
                    "xp_to_next": int(character.get("xp_to_next", ports.next_character_xp_for_level(level)) or ports.next_character_xp_for_level(level)),
                    "xp_total": int(character.get("xp_total", 0) or 0),
                },
                "injury_count": len(character.get("injuries", []) or []),
                "scar_count": len(character.get("scars", []) or []),
                "location": {"scene_id": character.get("scene_id", ""), "scene_name": ports.derive_scene_name(campaign, slot_name)},
                "claim_status": "geclaimt" if campaign.get("claims", {}).get(slot_name) else "frei",
                "appearance": character.get("appearance", {}),
                "ageing": character.get("aging", {}),
            },
            "stats": {
                "attributes": character.get("attributes", {}),
                "attribute_scale": {
                    "label": attribute_scale["label"],
                    "min": attribute_scale["min"],
                    "max": attribute_scale["max"],
                },
                "derived": derived,
                "resistances": derived.get("resistances", {}),
                "age_modifiers": derived.get("age_modifiers", {}),
                "modifier_summary": modifier_summary,
            },
            "skills": skill_views,
            "class": {
                "current": current_class,
                "ascension_plotpoint": ascension_plotpoint,
            },
            "injuries_scars": {
                "injuries": character.get("injuries", []),
                "scars": character.get("scars", []),
            },
            "gear_inventory": {
                "equipment": equipment_view,
                "quick_slots": character.get("inventory", {}).get("quick_slots", {}),
                "inventory_items": item_views,
                "carry_weight": character.get("carry_current", derived.get("carry_weight", 0)),
                "carry_limit": character.get("carry_max", derived.get("carry_limit", 0)),
                "encumbrance_state": derived.get("encumbrance_state", "normal"),
            },
            "effects": character.get("effects", []),
            "journal": {
                **(character.get("journal", {}) or {}),
                "appearance_history": character.get("appearance_history", []),
            },
            "progression": character.get("progression", {}),
            "skill_meta": {
                "fusion_possible": bool(fusion_hints),
                "fusion_hints": fusion_hints,
                "resource_name": resource_name,
            },
            "meta": {
                "faction_memberships": character.get("faction_memberships", []),
            },
        },
        "derived_explainer": {
            "defense": "10 + DEX + Armor + Effekte",
            "carry_limit": "10 + STR * 2",
            "initiative": "DEX + passive Boni + Effekte",
        },
        "timeline_refs": [],
    }
