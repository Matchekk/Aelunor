from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.config.progression import CLASS_ASCENSION_STATUSES, DEFAULT_DYNAMIC_SKILL_LEVEL_MAX, LEGACY_ROLE_CLASS_MAP, SKILL_RANK_ORDER
from app.core.ids import deep_copy, make_id
from app.services.characters.resources import resource_name_for_character
from app.services.progression import skills
from app.services.world import progression as _world_progression
from app.services.world.codex import normalize_codex_alias_text
from app.services.world.element_class_paths import (
    resolve_class_element_id as _resolve_class_element_id,
    resolve_class_path_rank_node as _resolve_class_path_rank_node,
)
from app.services.world.element_ids import normalize_element_id_list as _normalize_element_id_list
from app.services.world.element_profiles import element_id_from_name as _element_id_from_name
from app.services.world.math_utils import clamp
from app.services.world.progression import default_class_current, normalize_class_current
from app.services.world.text_normalization import normalized_eval_text


def next_class_xp_for_level(level: int) -> int:
    normalized = max(1, int(level or 1))
    return int(100 + ((normalized - 1) * 50) + (max(0, normalized - 1) ** 1.35) * 10)

_world_progression.configure(
    {
        "CLASS_ASCENSION_STATUSES": CLASS_ASCENSION_STATUSES,
        "deep_copy": deep_copy,
        "next_class_xp_for_level": next_class_xp_for_level,
        "normalize_skill_rank": skills.normalize_skill_rank,
    }
)

def role_key(role_text: str) -> str:
    normalized = normalized_eval_text(role_text)
    if "frontline" in normalized:
        return "frontline"
    if "scout" in normalized or "späher" in normalized or "spaeher" in normalized:
        return "scout"
    if "face" in normalized:
        return "face"
    if "support" in normalized:
        return "support"
    if "occult" in normalized or "flüche" in normalized or "flueche" in normalized:
        return "occult"
    if "tüftler" in normalized or "tueftler" in normalized:
        return "tueftler"
    return ""

def class_rank_sort_value(rank: str) -> int:
    return SKILL_RANK_ORDER.get(str(rank or "F").upper(), -1)

def migrate_legacy_role_to_class(role_text: str) -> Optional[Dict[str, Any]]:
    template = LEGACY_ROLE_CLASS_MAP.get(role_key(role_text))
    if not template:
        return None
    payload = default_class_current()
    payload.update(deep_copy(template))
    return normalize_class_current(payload)

def apply_class_xp(character: Dict[str, Any], amount: int, *, event_reason: str = "") -> List[str]:
    out: List[str] = []
    if amount <= 0:
        return out
    current_class = normalize_class_current(character.get("class_current"))
    if not current_class:
        return out
    current_class["xp"] = int(current_class.get("xp", 0) or 0) + int(amount or 0)
    leveled = False
    while (
        current_class["level"] < current_class["level_max"]
        and current_class["xp"] >= int(current_class.get("xp_next", next_class_xp_for_level(current_class["level"])) or next_class_xp_for_level(current_class["level"]))
    ):
        required = int(current_class.get("xp_next", next_class_xp_for_level(current_class["level"])) or next_class_xp_for_level(current_class["level"]))
        current_class["xp"] = max(0, int(current_class.get("xp", 0) or 0) - required)
        current_class["level"] += 1
        current_class["xp_next"] = next_class_xp_for_level(current_class["level"])
        leveled = True
    current_class["xp_next"] = max(1, int(current_class.get("xp_next", next_class_xp_for_level(current_class["level"])) or next_class_xp_for_level(current_class["level"])))
    current_class["xp"] = clamp(int(current_class.get("xp", 0) or 0), 0, current_class["xp_next"])
    current_class["class_mastery"] = clamp(int((current_class["xp"] / max(current_class["xp_next"], 1)) * 100), 0, 100)
    if current_class["level"] >= current_class["level_max"] and current_class.get("ascension", {}).get("status") == "none":
        current_class.setdefault("ascension", {}).update({"status": "available"})
        out.append(f"Klassenaufstieg bereit: {current_class.get('name', 'Klasse')}.")
    if leveled:
        out.append(
            f"Klassenfortschritt: {current_class.get('name', 'Klasse')} erreicht Lv {current_class.get('level')}/{current_class.get('level_max')}."
            + (f" ({event_reason})" if event_reason else "")
        )
    character["class_current"] = normalize_class_current(current_class)
    return out

def build_elemental_core_skill_payload(
    *,
    skill_name: str,
    element_id: str,
    class_name: str,
    resource_name: str,
    unlocked_from: str,
) -> Dict[str, Any]:
    pretty_name = skills.clean_extracted_skill_name(skill_name) or str(skill_name or "").strip() or "Elementtechnik"
    return skills.normalize_dynamic_skill_state(
        {
            "id": skills.skill_id_from_name(pretty_name),
            "name": pretty_name,
            "rank": "F",
            "level": 1,
            "level_max": DEFAULT_DYNAMIC_SKILL_LEVEL_MAX,
            "tags": ["technik", "elementar", normalize_codex_alias_text(class_name)],
            "description": f"{pretty_name} ist Teil des Klassenkerns von {class_name}.",
            "effect_summary": f"{pretty_name} kanalisiert elementare Energie.",
            "power_rating": 8,
            "growth_potential": "mittel",
            "elements": [element_id] if element_id else [],
            "element_primary": element_id or None,
            "cost": {"resource": resource_name, "amount": 1},
            "unlocked_from": unlocked_from,
            "manifestation_source": "class_core",
            "category": "elemental_core",
            "class_affinity": [normalize_codex_alias_text(class_name)] if class_name else None,
            "xp": 0,
            "next_xp": skills.next_skill_xp_for_level(1),
            "mastery": 0,
        },
        resource_name=resource_name,
    )


def resolve_class_element_id(current_class: Optional[Dict[str, Any]], world: Dict[str, Any]) -> Optional[str]:
    return _resolve_class_element_id(
        current_class,
        world,
        normalize_class_current=normalize_class_current,
        normalize_element_id_list=normalize_element_id_list,
    )


def resolve_class_path_rank_node(world: Dict[str, Any], current_class: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return _resolve_class_path_rank_node(
        world,
        current_class,
        normalize_class_current=normalize_class_current,
        resolve_class_element_id=resolve_class_element_id,
        normalize_skill_rank=skills.normalize_skill_rank,
        deep_copy=deep_copy,
    )


def element_id_from_name(name: str) -> str:
    return _element_id_from_name(
        name,
        normalize_codex_alias_text=normalize_codex_alias_text,
        make_id=make_id,
    )


def normalize_element_id_list(values: Any, world: Optional[Dict[str, Any]] = None) -> List[str]:
    return _normalize_element_id_list(
        values,
        world,
        normalize_codex_alias_text=normalize_codex_alias_text,
        element_id_from_name=element_id_from_name,
    )


def ensure_class_rank_core_skills(
    character: Dict[str, Any],
    world: Dict[str, Any],
    world_settings: Optional[Dict[str, Any]] = None,
    *,
    unlock_extra: bool = False,
) -> List[str]:
    messages: List[str] = []
    current_class = normalize_class_current(character.get("class_current"))
    if not current_class:
        return messages
    node_info = resolve_class_path_rank_node(world, current_class)
    if not node_info:
        return messages
    node = node_info["node"]
    current_class["path_id"] = str(node_info.get("path_id") or current_class.get("path_id") or "")
    current_class["path_rank"] = skills.normalize_skill_rank(node_info.get("rank") or current_class.get("rank") or "F")
    current_class["element_id"] = str(node_info.get("element_id") or current_class.get("element_id") or "")
    current_class["element_tags"] = list(
        dict.fromkeys(
            [
                *(current_class.get("element_tags") or []),
                str(current_class.get("element_id") or "").strip(),
            ]
        )
    )
    character["class_current"] = normalize_class_current(current_class)
    skill_store = character.setdefault("skills", {})
    resource_name = resource_name_for_character(character, world_settings or {})
    class_name = str(current_class.get("name") or "")
    required = [str(name).strip() for name in (node.get("core_skills_required") or []) if str(name).strip()]
    unlockable = [str(name).strip() for name in (node.get("core_skills_unlockable") or []) if str(name).strip()]
    signature = [str(name).strip() for name in (node.get("signature_skills") or []) if str(name).strip()]
    guaranteed: List[str] = required[:1] if required else []
    if unlock_extra:
        guaranteed.extend(unlockable[:1])
        if current_class.get("rank") in {"A", "S"}:
            guaranteed.extend(signature[:1])
    for skill_name in guaranteed:
        skill_id = skills.skill_id_from_name(skill_name)
        if skill_id in skill_store:
            existing = skills.normalize_dynamic_skill_state(skill_store[skill_id], resource_name=resource_name)
            if current_class.get("element_id") and current_class["element_id"] not in (existing.get("elements") or []):
                existing["elements"] = [current_class["element_id"], *(existing.get("elements") or [])]
                existing["element_primary"] = existing.get("element_primary") or current_class["element_id"]
                skill_store[skill_id] = skills.normalize_dynamic_skill_state(existing, resource_name=resource_name)
            continue
        new_skill = build_elemental_core_skill_payload(
            skill_name=skill_name,
            element_id=str(current_class.get("element_id") or ""),
            class_name=class_name,
            resource_name=resource_name,
            unlocked_from=f"ClassCore:{current_class.get('rank','F')}",
        )
        skill_store[new_skill["id"]] = new_skill
        char_name = str(((character.get("bio") or {}).get("name") or character.get("slot_id") or "").strip() or "Die Figur")
        messages.append(f"{char_name} schaltet den Klassenkern-Skill {new_skill['name']} frei.")
    return messages
