from typing import Any, Callable, Dict


def default_attribute_influence_meta() -> Dict[str, Any]:
    return {
        "last_turn": 0,
        "last_actor": "",
        "last_profile": {
            "primary_attributes": [],
            "influence_tier": "none",
            "narrative_bias": [],
            "mechanical_bias": {
                "damage_taken_mult": 1.0,
                "cost_mult": 1.0,
                "complication_mult": 1.0,
                "outgoing_effect_mult": 1.0,
            },
        },
    }


def normalize_attribute_influence_meta(
    meta: Dict[str, Any],
    *,
    default_attribute_influence_meta: Callable[[], Dict[str, Any]],
    deep_copy: Callable[[Any], Any],
    attribute_keys: tuple[str, ...],
    clamp_float: Callable[[float, float, float], float],
) -> Dict[str, Any]:
    influence = deep_copy(meta.get("attribute_influence") or default_attribute_influence_meta())
    defaults = default_attribute_influence_meta()
    influence["last_turn"] = max(0, int(influence.get("last_turn", defaults["last_turn"]) or defaults["last_turn"]))
    influence["last_actor"] = str(influence.get("last_actor") or defaults["last_actor"]).strip()
    profile = deep_copy(influence.get("last_profile") or defaults["last_profile"])
    tier = str(profile.get("influence_tier") or "none").strip().lower()
    if tier not in {"none", "low", "medium", "high"}:
        tier = "none"
    profile["influence_tier"] = tier
    profile["primary_attributes"] = [
        str(entry).strip().lower()
        for entry in (profile.get("primary_attributes") or [])
        if str(entry).strip().lower() in attribute_keys
    ]
    profile["narrative_bias"] = [str(entry).strip() for entry in (profile.get("narrative_bias") or []) if str(entry).strip()]
    raw_mechanical = profile.get("mechanical_bias") if isinstance(profile.get("mechanical_bias"), dict) else {}
    profile["mechanical_bias"] = {
        "damage_taken_mult": clamp_float(float(raw_mechanical.get("damage_taken_mult", 1.0) or 1.0), 0.65, 1.35),
        "cost_mult": clamp_float(float(raw_mechanical.get("cost_mult", 1.0) or 1.0), 0.65, 1.35),
        "complication_mult": clamp_float(float(raw_mechanical.get("complication_mult", 1.0) or 1.0), 0.65, 1.35),
        "outgoing_effect_mult": clamp_float(float(raw_mechanical.get("outgoing_effect_mult", 1.0) or 1.0), 0.65, 1.35),
    }
    influence["last_profile"] = profile
    meta["attribute_influence"] = influence
    return influence
