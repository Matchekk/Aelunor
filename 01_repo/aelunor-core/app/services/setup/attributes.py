"""Character attribute-range and weight allocation for setup.

Pure setup-domain logic extracted from the state runtime core. The single
LLM-backed entry point (:func:`generate_character_attribute_weights`) receives
its ``call_ollama_schema`` port explicitly so this module stays free of runtime
adapter state.
"""
import json
import math
import re
from typing import Any, Callable, Dict, List

from app.config.progression import ATTRIBUTE_KEYS
from app.prompts.system_prompts import CHARACTER_ATTRIBUTE_SYSTEM_PROMPT
from app.schemas.llm import CHARACTER_ATTRIBUTE_SCHEMA
from app.services.setup.answers import extract_text_answer
from app.services.world.math_utils import clamp
from app.services.world.text_normalization import normalized_eval_text


def parse_attribute_range(raw_value: Any) -> Dict[str, Any]:
    text = extract_text_answer(raw_value)
    match = re.search(r"1\s*-\s*(100|20|10)", text)
    maximum = int(match.group(1)) if match else 10
    return {
        "label": f"1-{maximum}",
        "min": 1,
        "max": maximum,
    }


def world_attribute_scale(campaign: Dict[str, Any]) -> Dict[str, Any]:
    world_setup = (((campaign.get("setup") or {}).get("world")) or {})
    answers = (world_setup.get("answers") or {})
    summary = (world_setup.get("summary") or {})
    if answers.get("attribute_range"):
        return parse_attribute_range(answers.get("attribute_range"))
    if summary.get("attribute_range_max"):
        return {
            "label": str(summary.get("attribute_range_label") or f"1-{int(summary.get('attribute_range_max') or 10)}"),
            "min": int(summary.get("attribute_range_min", 1) or 1),
            "max": int(summary.get("attribute_range_max", 10) or 10),
        }
    return parse_attribute_range(None)


def attribute_cap_for_campaign(campaign: Dict[str, Any]) -> int:
    return max(1, int(world_attribute_scale(campaign)["max"] or 10))


def level_one_attribute_budget(campaign: Dict[str, Any]) -> int:
    world_max = int(world_attribute_scale(campaign)["max"] or 10)
    return max(len(ATTRIBUTE_KEYS), min(120, int(round(world_max * 3.5))))


def level_one_attribute_cap(campaign: Dict[str, Any]) -> int:
    world_max = int(world_attribute_scale(campaign)["max"] or 10)
    if world_max <= 10:
        return 10
    if world_max <= 20:
        return 18
    return min(world_max, 32)


def normalize_attribute_weight_pool(raw_weights: Dict[str, Any], total: int = 120) -> Dict[str, int]:
    cleaned = {
        key: max(1, int(raw_weights.get(key, 0) or 0))
        for key in ATTRIBUTE_KEYS
    }
    raw_total = sum(cleaned.values()) or len(ATTRIBUTE_KEYS)
    scaled = {
        key: (cleaned[key] / raw_total) * total
        for key in ATTRIBUTE_KEYS
    }
    normalized = {key: max(1, int(math.floor(value))) for key, value in scaled.items()}
    delta = total - sum(normalized.values())
    if delta > 0:
        order = sorted(
            ATTRIBUTE_KEYS,
            key=lambda key: (scaled[key] - normalized[key], cleaned[key]),
            reverse=True,
        )
        index = 0
        while delta > 0 and order:
            key = order[index % len(order)]
            normalized[key] += 1
            delta -= 1
            index += 1
    elif delta < 0:
        order = sorted(
            ATTRIBUTE_KEYS,
            key=lambda key: (scaled[key] - normalized[key], normalized[key]),
        )
        index = 0
        while delta < 0 and order:
            key = order[index % len(order)]
            if normalized[key] > 1:
                normalized[key] -= 1
                delta += 1
            index += 1
            if index > 200:
                break
    return normalized


def allocate_weighted_attributes(
    weights: Dict[str, int],
    *,
    total_budget: int,
    max_value: int,
    min_value: int = 1,
) -> Dict[str, int]:
    values = {key: int(min_value) for key in ATTRIBUTE_KEYS}
    remaining = max(0, int(total_budget) - (min_value * len(ATTRIBUTE_KEYS)))
    total_weight = sum(max(0, int(weights.get(key, 0) or 0)) for key in ATTRIBUTE_KEYS) or len(ATTRIBUTE_KEYS)
    scaled_additions = {
        key: (remaining * max(0, int(weights.get(key, 0) or 0))) / total_weight
        for key in ATTRIBUTE_KEYS
    }
    remainders: List[tuple[float, str]] = []
    for key in ATTRIBUTE_KEYS:
        cap_room = max(0, int(max_value) - values[key])
        addition = min(cap_room, int(math.floor(scaled_additions[key])))
        values[key] += addition
        remainders.append((scaled_additions[key] - addition, key))
    delta = int(total_budget) - sum(values.values())
    order = [key for _, key in sorted(remainders, reverse=True)]
    if not order:
        order = list(ATTRIBUTE_KEYS)
    guard = 0
    while delta > 0 and guard < 500:
        changed = False
        for key in order:
            if values[key] < int(max_value):
                values[key] += 1
                delta -= 1
                changed = True
                if delta <= 0:
                    break
        if not changed:
            break
        guard += 1
    return {key: clamp(int(values[key]), int(min_value), int(max_value)) for key in ATTRIBUTE_KEYS}


def fallback_character_attribute_weights(summary: Dict[str, Any]) -> Dict[str, int]:
    weights = {key: 16 for key in ATTRIBUTE_KEYS}
    class_tags = {normalized_eval_text(entry) for entry in (summary.get("class_custom_tags") or []) if normalized_eval_text(entry)}
    if any(tag in class_tags for tag in ("körper", "kampf", "schutz")):
        for key, delta in {"str": 8, "con": 8, "dex": 2}.items():
            weights[key] = max(1, weights[key] + delta)
    if any(tag in class_tags for tag in ("bewegung", "heimlichkeit", "sinn")):
        for key, delta in {"dex": 10, "wis": 7, "luck": 3}.items():
            weights[key] = max(1, weights[key] + delta)
    if any(tag in class_tags for tag in ("sozial", "sprache", "einfluss")):
        for key, delta in {"cha": 10, "wis": 4, "int": 3}.items():
            weights[key] = max(1, weights[key] + delta)
    if any(tag in class_tags for tag in ("technik", "improvisation", "werkzeug", "okkult", "ritual", "schatten")):
        for key, delta in {"int": 8, "wis": 5, "luck": 3}.items():
            weights[key] = max(1, weights[key] + delta)

    strength_text = normalized_eval_text(summary.get("strength", ""))
    weakness_text = normalized_eval_text(summary.get("weakness", ""))
    focus_text = normalized_eval_text(summary.get("current_focus", ""))

    if any(token in strength_text for token in ("kraft", "athlet", "nahkampf")):
        weights["str"] += 6
        weights["con"] += 3
    if any(token in strength_text for token in ("sinne", "spur", "schleich", "unauff")):
        weights["dex"] += 6
        weights["wis"] += 4
    if any(token in strength_text for token in ("okkult", "wissen", "technik", "tueft", "plan")):
        weights["int"] += 6
        weights["wis"] += 2
    if any(token in strength_text for token in ("sozial", "uberzeug", "ueberzeug", "dominanz", "einschuch", "einschuech")):
        weights["cha"] += 6

    if any(token in weakness_text for token in ("angst", "flucht", "konfliktscheu")):
        weights["con"] -= 3
        weights["cha"] -= 1
    if any(token in weakness_text for token in ("naiv", "vertrauen")):
        weights["wis"] -= 3
    if any(token in weakness_text for token in ("wut", "jähzorn", "jaehzorn", "uber", "uebermut", "ungeduld")):
        weights["wis"] -= 2
        weights["cha"] -= 1
    if any(token in weakness_text for token in ("ausdauer", "erschopf", "erschoepf")):
        weights["con"] -= 4
    if any(token in weakness_text for token in ("orientierung", "paranoia")):
        weights["wis"] -= 2

    if "uberleben" in focus_text or "ueberleben" in focus_text or "flucht" in focus_text:
        weights["con"] += 3
        weights["wis"] += 3
    if "macht" in focus_text or "skills" in focus_text:
        weights["str"] += 2
        weights["int"] += 2
    if "wahrheit" in focus_text or "geheim" in focus_text:
        weights["int"] += 3
        weights["wis"] += 3
    if "rache" in focus_text:
        weights["str"] += 3
        weights["dex"] += 2
    if "reichen" in focus_text or "loot" in focus_text:
        weights["luck"] += 3
        weights["dex"] += 2

    return normalize_attribute_weight_pool(weights, total=120)


def generate_character_attribute_weights(
    campaign: Dict[str, Any],
    slot_name: str,
    summary: Dict[str, Any],
    *,
    call_ollama_schema: Callable[..., Dict[str, Any]],
) -> Dict[str, Any]:
    world_summary = (((campaign.get("setup") or {}).get("world") or {}).get("summary") or {})
    payload = {
        "slot_id": slot_name,
        "display_name": summary.get("display_name", ""),
        "gender": summary.get("gender", ""),
        "age_bucket": summary.get("age_bucket", ""),
        "class_start_mode": summary.get("class_start_mode", ""),
        "class_seed": summary.get("class_seed", ""),
        "class_custom_tags": summary.get("class_custom_tags", []),
        "strength": summary.get("strength", ""),
        "weakness": summary.get("weakness", ""),
        "current_focus": summary.get("current_focus", ""),
        "isekai_price": summary.get("isekai_price", ""),
        "personality_tags": summary.get("personality_tags", []),
        "background_tags": summary.get("background_tags", []),
        "earth_life": summary.get("earth_life", ""),
        "world": {
            "theme": world_summary.get("theme", ""),
            "tone": world_summary.get("tone", ""),
            "difficulty": world_summary.get("difficulty", ""),
            "attribute_range": world_attribute_scale(campaign)["label"],
        },
        "pool_total": 120,
        "note": "Verteile nur Gewichte. Die finalen Level-1-Startwerte werden serverseitig aus diesem Pool abgeleitet.",
    }
    try:
        raw = call_ollama_schema(
            CHARACTER_ATTRIBUTE_SYSTEM_PROMPT,
            json.dumps(payload, ensure_ascii=False),
            CHARACTER_ATTRIBUTE_SCHEMA,
            timeout=90,
            temperature=0.35,
        )
        weights = normalize_attribute_weight_pool(raw if isinstance(raw, dict) else {}, total=120)
        return {"weights": weights, "source": "ai"}
    except Exception:
        return {"weights": fallback_character_attribute_weights(summary), "source": "fallback"}


def level_one_attributes_from_weights(campaign: Dict[str, Any], weights: Dict[str, int]) -> Dict[str, int]:
    return allocate_weighted_attributes(
        weights,
        total_budget=level_one_attribute_budget(campaign),
        max_value=level_one_attribute_cap(campaign),
        min_value=1,
    )
