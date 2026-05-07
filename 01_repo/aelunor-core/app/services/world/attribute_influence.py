from typing import Any, Callable, Dict, Optional


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


def derive_attribute_relevance(
    state: Dict[str, Any],
    actor: str,
    action_type: str,
    text: str,
    combat_context: Optional[Dict[str, Any]] = None,
    *,
    normalized_eval_text: Callable[[Any], str],
    hash_unit_interval: Callable[[str], float],
    attribute_keys: tuple[str, ...],
    attribute_influence_distribution: tuple[tuple[str, float], ...],
) -> Dict[str, Any]:
    character = ((state.get("characters") or {}).get(actor) or {})
    attrs = character.get("attributes", {}) or {}
    normalized_text = normalized_eval_text(text)
    combat_active = bool((combat_context or {}).get("active") or (combat_context or {}).get("hinted"))

    keyword_map = {
        "str": ("schlag", "drücken", "kraft", "klinge", "hieb", "werfen", "reißen"),
        "dex": ("ausweichen", "springen", "schnell", "präzise", "treffer", "klettern", "balanc"),
        "con": ("aushalten", "einstecken", "standhaft", "zäh", "widerstand", "durchhalten"),
        "int": ("analys", "plan", "taktik", "berechnen", "runen", "technik", "formel"),
        "wis": ("spüren", "ahnung", "instinkt", "warnung", "wahrnehmen", "ruhe"),
        "cha": ("überzeugen", "drohen", "verhandeln", "reden", "bluff", "anführen"),
        "luck": ("zufall", "glück", "fund", "zufällig", "knapp", "unerwartet", "gerade noch"),
    }

    scored: list[tuple[float, str]] = []
    for key in attribute_keys:
        base = float(int(attrs.get(key, 0) or 0))
        score = base
        if combat_active and key in {"str", "dex", "con", "luck"}:
            score += 2.0
        if action_type == "say" and key in {"cha", "wis", "luck"}:
            score += 2.5
        if action_type == "story" and key in {"int", "wis", "luck"}:
            score += 1.5
        for keyword in keyword_map.get(key, ()):
            if keyword in normalized_text:
                score += 2.2
        scored.append((score, key))

    scored.sort(key=lambda entry: (entry[0], int(attrs.get(entry[1], 0) or 0)), reverse=True)
    primary_attributes = [entry[1] for entry in scored[:2] if entry[0] > 0]
    if not primary_attributes:
        primary_attributes = ["luck"]

    roll = hash_unit_interval(f"{int((state.get('meta') or {}).get('turn', 0) or 0)}|{actor}|{action_type}|{normalized_text[:180]}")
    cursor = 0.0
    tier = "none"
    for label, probability in attribute_influence_distribution:
        cursor += probability
        if roll <= cursor:
            tier = label
            break

    narrative_bias: list[str] = []
    if "luck" in primary_attributes:
        narrative_bias.append("fortunate_timing" if int(attrs.get("luck", 0) or 0) >= 5 else "ill_timing")
    if "dex" in primary_attributes:
        narrative_bias.append("tempo_shift")
    if "con" in primary_attributes:
        narrative_bias.append("pain_tolerance")
    if "cha" in primary_attributes:
        narrative_bias.append("social_pressure")
    if "int" in primary_attributes:
        narrative_bias.append("tactical_read")
    if "wis" in primary_attributes:
        narrative_bias.append("hazard_sense")
    if "str" in primary_attributes:
        narrative_bias.append("force_spike")

    return {
        "primary_attributes": primary_attributes,
        "influence_tier": tier,
        "narrative_bias": narrative_bias[:3],
        "combat_active": combat_active,
    }


def compute_attribute_bias(
    profile: Dict[str, Any],
    character: Dict[str, Any],
    world_settings: Optional[Dict[str, Any]] = None,
    *,
    attribute_keys: tuple[str, ...],
    attribute_influence_strength: Dict[str, float],
    clamp: Callable[[int, int, int], int],
    clamp_float: Callable[[float, float, float], float],
) -> Dict[str, float]:
    attrs = (character or {}).get("attributes", {}) or {}
    tier = str((profile or {}).get("influence_tier") or "none").lower()
    strength = attribute_influence_strength.get(tier, 0.0)
    attr_cap = max(10, max((int(attrs.get(key, 0) or 0) for key in attribute_keys), default=10))
    primary = [key for key in ((profile or {}).get("primary_attributes") or []) if key in attribute_keys]

    bias = {
        "damage_taken_mult": 1.0,
        "cost_mult": 1.0,
        "complication_mult": 1.0,
        "outgoing_effect_mult": 1.0,
    }
    if strength <= 0 or not primary:
        return bias

    for key in primary:
        value = clamp(int(attrs.get(key, 0) or 0), 0, attr_cap)
        normalized = value / float(attr_cap)
        if key == "luck":
            bias["damage_taken_mult"] -= (0.18 * strength * normalized)
            bias["cost_mult"] -= (0.14 * strength * normalized)
            bias["complication_mult"] -= (0.30 * strength * normalized)
            bias["outgoing_effect_mult"] += (0.10 * strength * normalized)
            if value <= max(1, int(attr_cap * 0.25)) and tier in {"medium", "high"}:
                bias["complication_mult"] += (0.22 * strength)
        elif key == "con":
            bias["damage_taken_mult"] -= (0.26 * strength * normalized)
            bias["cost_mult"] -= (0.08 * strength * normalized)
        elif key == "dex":
            bias["damage_taken_mult"] -= (0.14 * strength * normalized)
            bias["complication_mult"] -= (0.16 * strength * normalized)
            bias["outgoing_effect_mult"] += (0.08 * strength * normalized)
        elif key == "str":
            bias["outgoing_effect_mult"] += (0.20 * strength * normalized)
            bias["cost_mult"] += (0.04 * strength * (1.0 - normalized))
        elif key == "int":
            bias["outgoing_effect_mult"] += (0.18 * strength * normalized)
            bias["cost_mult"] -= (0.10 * strength * normalized)
        elif key == "wis":
            bias["complication_mult"] -= (0.14 * strength * normalized)
            bias["cost_mult"] -= (0.08 * strength * normalized)
            bias["outgoing_effect_mult"] += (0.06 * strength * normalized)
        elif key == "cha":
            bias["complication_mult"] -= (0.08 * strength * normalized)
            bias["outgoing_effect_mult"] += (0.10 * strength * normalized)

    for key in tuple(bias.keys()):
        bias[key] = clamp_float(float(bias[key]), 0.65, 1.35)
    return bias


def compose_attribute_prompt_hints(profile: Dict[str, Any], bias: Dict[str, float]) -> str:
    attrs = ", ".join(str(entry).upper() for entry in (profile.get("primary_attributes") or [])) or "LUCK"
    narrative = ", ".join(profile.get("narrative_bias") or []) or "keine"
    tier = str(profile.get("influence_tier") or "none")
    return (
        "ATTRIBUTE INFLUENCE:\n"
        f"- primary_attributes={attrs}\n"
        f"- influence_tier={tier}\n"
        f"- narrative_bias={narrative}\n"
        f"- mechanical_bias.damage_taken_mult={bias.get('damage_taken_mult', 1.0):.2f}\n"
        f"- mechanical_bias.cost_mult={bias.get('cost_mult', 1.0):.2f}\n"
        f"- mechanical_bias.complication_mult={bias.get('complication_mult', 1.0):.2f}\n"
        f"- mechanical_bias.outgoing_effect_mult={bias.get('outgoing_effect_mult', 1.0):.2f}\n"
        "- Attributwirkung muss im story-Text konkret sichtbar sein (kein abstraktes Meta-Gerede)."
    )


def apply_attribute_bias_to_resolution(
    resolution: Dict[str, Any],
    numeric_bias: Dict[str, float],
    *,
    deep_copy: Callable[[Any], Any],
) -> Dict[str, Any]:
    adjusted = deep_copy(resolution or {})
    if "damage_taken" in adjusted:
        adjusted["damage_taken"] = int(round(float(adjusted.get("damage_taken", 0) or 0) * float(numeric_bias.get("damage_taken_mult", 1.0))))
    if "cost" in adjusted:
        adjusted["cost"] = int(round(float(adjusted.get("cost", 0) or 0) * float(numeric_bias.get("cost_mult", 1.0))))
    if "complication" in adjusted:
        adjusted["complication"] = int(round(float(adjusted.get("complication", 0) or 0) * float(numeric_bias.get("complication_mult", 1.0))))
    if "outgoing_effect" in adjusted:
        adjusted["outgoing_effect"] = int(round(float(adjusted.get("outgoing_effect", 0) or 0) * float(numeric_bias.get("outgoing_effect_mult", 1.0))))
    return adjusted


def scale_negative_delta(value: int, multiplier: float) -> int:
    number = int(value or 0)
    if number >= 0:
        return number
    scaled = int(round(number * float(multiplier)))
    if scaled == 0:
        return -1
    return scaled
