import re
from typing import Any, Dict, Optional

from app.config.feature_flags import ENABLE_LEGACY_SHADOW_WRITEBACK
from app.core.ids import deep_copy
from app.services.world.math_utils import clamp
from app.services.world.progression import normalize_resource_name
from app.services.world.text_normalization import normalized_eval_text


def configure(main_globals: Dict[str, Any]) -> None:
    globals().update(main_globals)


def resource_name_for_character(character: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> str:
    progression = character.get("progression", {}) or {}
    resource_name = normalize_resource_name(progression.get("resource_name", ""))
    if resource_name:
        return resource_name
    world_settings = world_settings or {}
    return normalize_resource_name(world_settings.get("resource_name", ""), "Aether")


def canonical_resource_field_name(raw_name: Any) -> str:
    normalized = normalized_eval_text(raw_name)
    if normalized in {"hp", "health", "leben", "lebenspunkte"}:
        return "hp"
    if normalized in {"sta", "stamina", "ausdauer"}:
        return "stamina"
    if normalized in {"res", "resource", "mana", "aether", "äther", "qi", "ki", "energie"}:
        return "aether"
    if normalized in {"stress"}:
        return "stress"
    if normalized in {"corruption", "verderbnis"}:
        return "corruption"
    if normalized in {"wounds", "wound", "wunde", "wunden"}:
        return "wounds"
    return ""


def ingest_legacy_resources_into_canonical(
    character: Dict[str, Any],
    world_settings: Optional[Dict[str, Any]] = None,
    *,
    source_character: Optional[Dict[str, Any]] = None,
) -> None:
    source = source_character if isinstance(source_character, dict) else character
    resources = source.get("resources", {}) if isinstance(source.get("resources"), dict) else {}
    progression = character.setdefault("progression", {})
    resource_label = normalize_resource_name(
        ((world_settings or {}).get("resource_name")) or progression.get("resource_name") or "Aether",
        "Aether",
    )
    hp_res = resources.get("hp") or {}
    sta_res = resources.get("stamina") or {}
    legacy_res = resources.get("aether") or {}
    if not legacy_res:
        dynamic_key = re.sub(r"[^a-z0-9]+", "_", normalized_eval_text(resource_label)).strip("_")
        if dynamic_key:
            legacy_res = resources.get(dynamic_key) or {}

    if "hp_max" not in source:
        character["hp_max"] = max(1, int(hp_res.get("max", 10) or 10))
    if "hp_current" not in source:
        default_hp_current = hp_res.get("current", character.get("hp_max", 10))
        character["hp_current"] = max(0, int(default_hp_current or 0))
    if "sta_max" not in source:
        character["sta_max"] = max(0, int(sta_res.get("max", 10) or 10))
    if "sta_current" not in source:
        default_sta_current = sta_res.get("current", character.get("sta_max", 10))
        character["sta_current"] = max(0, int(default_sta_current or 0))
    if "res_max" not in source:
        default_res_max = legacy_res.get("max", progression.get("resource_max", 5))
        character["res_max"] = max(0, int(default_res_max or 5))
    if "res_current" not in source:
        default_res_current = legacy_res.get("current", progression.get("resource_current", character.get("res_max", 5)))
        character["res_current"] = max(0, int(default_res_current or 0))
    if "carry_max" not in source:
        carry_limit = int(((character.get("derived") or {}).get("carry_limit", 10)) or 10)
        character["carry_max"] = max(0, carry_limit)
    if "carry_current" not in source:
        carry_weight = int(((character.get("derived") or {}).get("carry_weight", 0)) or 0)
        character["carry_current"] = max(0, carry_weight)
    if "hp" in source and "hp_current" not in source and not isinstance(resources.get("hp"), dict):
        character["hp_current"] = max(0, int(character.get("hp", 0) or 0))
    if "stamina" in source and "sta_current" not in source and not isinstance(resources.get("stamina"), dict):
        character["sta_current"] = max(0, int(character.get("stamina", 0) or 0))
    progression["resource_name"] = resource_label


def reconcile_canonical_resources(character: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> None:
    progression = character.setdefault("progression", {})
    resource_label = normalize_resource_name(
        ((world_settings or {}).get("resource_name")) or progression.get("resource_name") or "Aether",
        "Aether",
    )
    character["hp_max"] = max(1, int(character.get("hp_max", 10) or 10))
    character["hp_current"] = clamp(int(character.get("hp_current", character["hp_max"]) or character["hp_max"]), 0, character["hp_max"])
    character["sta_max"] = max(0, int(character.get("sta_max", 10) or 10))
    character["sta_current"] = clamp(int(character.get("sta_current", character["sta_max"]) or character["sta_max"]), 0, character["sta_max"])
    character["res_max"] = max(0, int(character.get("res_max", 5) or 5))
    character["res_current"] = clamp(int(character.get("res_current", character["res_max"]) or character["res_max"]), 0, character["res_max"])
    character["carry_max"] = max(0, int(character.get("carry_max", 10) or 10))
    character["carry_current"] = clamp(int(character.get("carry_current", 0) or 0), 0, character["carry_max"])
    progression["resource_name"] = resource_label
    progression["resource_current"] = int(character.get("res_current", 0) or 0)
    progression["resource_max"] = int(character.get("res_max", 0) or 0)
    character.setdefault("derived", {})["carry_limit"] = int(character["carry_max"])
    character.setdefault("derived", {})["carry_weight"] = int(character["carry_current"])


def build_compat_resources_view(character: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, int]]:
    resource_label = resource_name_for_character(character, world_settings)
    resource_key = re.sub(r"[^a-z0-9]+", "_", normalized_eval_text(resource_label)).strip("_") or "resource"
    hp_max = max(1, int(character.get("hp_max", 10) or 10))
    sta_max = max(0, int(character.get("sta_max", 10) or 10))
    res_max = max(0, int(character.get("res_max", 5) or 5))
    hp_payload = {"current": clamp(int(character.get("hp_current", hp_max) or hp_max), 0, hp_max), "base_max": hp_max, "bonus_max": 0, "max": hp_max}
    sta_payload = {"current": clamp(int(character.get("sta_current", sta_max) or sta_max), 0, sta_max), "base_max": sta_max, "bonus_max": 0, "max": sta_max}
    res_payload = {"current": clamp(int(character.get("res_current", res_max) or res_max), 0, res_max), "base_max": res_max, "bonus_max": 0, "max": res_max}
    view = {
        "hp": dict(hp_payload),
        "stamina": dict(sta_payload),
        "aether": dict(res_payload),
    }
    view[resource_key] = dict(res_payload)
    for key in ("stress", "corruption", "wounds"):
        raw = ((character.get("resources") or {}).get(key) or {}) if isinstance(character.get("resources"), dict) else {}
        fallback_max = 10 if key != "wounds" else 3
        entry_max = max(0, int(raw.get("max", fallback_max) or fallback_max))
        view[key] = {
            "current": clamp(int(raw.get("current", 0) or 0), 0, entry_max),
            "base_max": max(0, int(raw.get("base_max", entry_max) or entry_max)),
            "bonus_max": int(raw.get("bonus_max", 0) or 0),
            "max": entry_max,
        }
    return view


def strip_legacy_resource_shadows(character: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> None:
    if ENABLE_LEGACY_SHADOW_WRITEBACK:
        return
    resources = character.get("resources")
    if not isinstance(resources, dict):
        return
    resource_label = resource_name_for_character(character, world_settings)
    dynamic_key = re.sub(r"[^a-z0-9]+", "_", normalized_eval_text(resource_label)).strip("_")
    for key in ("hp", "stamina", "aether", dynamic_key):
        if key and key in resources and key not in {"stress", "corruption", "wounds"}:
            resources.pop(key, None)


def strip_legacy_shadow_fields(character: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> None:
    if ENABLE_LEGACY_SHADOW_WRITEBACK:
        return
    strip_legacy_resource_shadows(character, world_settings)
    for field_name in ("hp", "stamina", "equip", "abilities", "potential", "class_state"):
        character.pop(field_name, None)


def legacy_misc_resources_set_from_payload(resources_set_payload: Any) -> Dict[str, Dict[str, int]]:
    out: Dict[str, Dict[str, int]] = {}
    if not isinstance(resources_set_payload, dict):
        return out
    for raw_key, raw_value in resources_set_payload.items():
        mapped = canonical_resource_field_name(raw_key)
        if mapped not in {"stress", "corruption", "wounds"}:
            continue
        if not isinstance(raw_value, dict):
            continue
        entry = {
            "current": max(0, int(raw_value.get("current", 0) or 0)),
            "max": max(0, int(raw_value.get("max", 0) or 0)),
        }
        if entry["max"] > 0:
            entry["current"] = clamp(entry["current"], 0, entry["max"])
        out[mapped] = entry
    return out


def legacy_misc_resource_deltas_from_update(upd: Dict[str, Any]) -> Dict[str, int]:
    out = {"stress": 0, "corruption": 0, "wounds": 0}
    raw_deltas = upd.get("resources_delta") if isinstance(upd.get("resources_delta"), dict) else {}
    for raw_key, raw_value in raw_deltas.items():
        mapped = canonical_resource_field_name(raw_key)
        if mapped in out:
            out[mapped] += int(raw_value or 0)
    return out


def write_legacy_shadow_fields(character: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> None:
    resources_view = build_compat_resources_view(character, world_settings)
    character["resources"] = deep_copy(resources_view)
    character["hp"] = int(character.get("hp_current", 0) or 0)
    character["stamina"] = int(character.get("sta_current", 0) or 0)
    character["equip"] = {
        "weapon": ((character.get("equipment") or {}).get("weapon", "") if isinstance(character.get("equipment"), dict) else ""),
        "armor": ((character.get("equipment") or {}).get("chest", "") if isinstance(character.get("equipment"), dict) else ""),
        "trinket": ((character.get("equipment") or {}).get("trinket", "") if isinstance(character.get("equipment"), dict) else ""),
    }
    character["potential"] = [
        card.get("name", card.get("id", ""))
        for card in (character.get("progression", {}).get("potential_cards") or [])
        if isinstance(card, dict)
    ]


def sync_canonical_resources(character: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> None:
    # Backward-compatible wrapper: canonical-first by default, optional legacy shadow writeback.
    ingest_legacy_resources_into_canonical(character, world_settings)
    reconcile_canonical_resources(character, world_settings)
    if ENABLE_LEGACY_SHADOW_WRITEBACK:
        write_legacy_shadow_fields(character, world_settings)
    else:
        strip_legacy_shadow_fields(character, world_settings)
