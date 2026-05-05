from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.services.world.math_utils import clamp
from app.services.world.text_normalization import normalized_eval_text

_CONFIGURED = False


def configure(main_globals: Dict[str, Any]) -> None:
    global _CONFIGURED
    globals().update(main_globals)
    _CONFIGURED = True


def next_character_xp_for_level(level: int) -> int:
    normalized = max(1, int(level or 1))
    return int(120 + ((normalized - 1) * 60) + (max(0, normalized - 1) ** 1.4) * 14)

def normalize_resource_name(value: Any, default: str = "Aether") -> str:
    text = str(value or "").strip()
    if not text:
        return default
    text = re.sub(r"\s+", " ", text)
    if len(text) > 24:
        text = text[:24].strip()
    return text or default

def normalize_class_current(value: Any) -> Optional[Dict[str, Any]]:
    if value in (None, "", False):
        return None
    payload = deep_copy(value) if isinstance(value, dict) else {}
    if not payload:
        return None
    klass = default_class_current()
    klass.update(payload)
    klass["id"] = str(klass.get("id") or klass.get("class_id") or "").strip()
    klass["name"] = str(klass.get("name") or klass.get("class_name") or klass.get("id") or "").strip()
    if not klass["id"] and klass["name"]:
        klass["id"] = re.sub(r"[^a-z0-9]+", "_", normalized_eval_text(klass["name"])).strip("_")
        if klass["id"] and not klass["id"].startswith("class_"):
            klass["id"] = f"class_{klass['id']}"
    if not klass["name"]:
        return None
    raw_rank = klass.get("rank", klass.get("class_rank", "F"))
    klass["rank"] = normalize_skill_rank(raw_rank)
    klass["path_id"] = str(klass.get("path_id") or "").strip()
    klass["path_rank"] = normalize_skill_rank(klass.get("path_rank") or klass.get("rank") or "F")
    klass["element_id"] = str(klass.get("element_id") or "").strip()
    raw_element_tags = klass.get("element_tags") or []
    klass["element_tags"] = list(dict.fromkeys([str(entry).strip() for entry in raw_element_tags if str(entry).strip()]))
    klass["level"] = max(1, int(klass.get("level", klass.get("class_level", 1)) or 1))
    klass["level_max"] = max(klass["level"], int(klass.get("level_max", klass.get("class_level_max", 10)) or 10))
    default_xp_next = next_class_xp_for_level(klass["level"])
    klass["xp_next"] = max(1, int(klass.get("xp_next", klass.get("class_xp_to_next", default_xp_next)) or default_xp_next))
    klass["xp"] = clamp(int(klass.get("xp", klass.get("class_xp", 0)) or 0), 0, klass["xp_next"])
    normalized_affinity_tags: List[str] = []
    for raw_tag in (klass.get("affinity_tags") or []):
        if isinstance(raw_tag, str):
            parts = re.split(r"[\n,;/|]+", raw_tag)
        else:
            parts = [str(raw_tag)]
        for part in parts:
            clean_part = str(part).strip()
            if clean_part:
                normalized_affinity_tags.append(clean_part)
    klass["affinity_tags"] = list(dict.fromkeys(normalized_affinity_tags))
    klass["description"] = str(klass.get("description", "") or "").strip()
    class_traits = [str(entry).strip() for entry in (klass.get("class_traits") or []) if str(entry).strip()]
    klass["class_traits"] = list(dict.fromkeys(class_traits))
    klass["class_mastery"] = clamp(int(klass.get("class_mastery", int((klass["xp"] / max(klass["xp_next"], 1)) * 100)) or 0), 0, 100)
    ascension = deep_copy(klass.get("ascension") or {})
    merged_ascension = deep_copy(default_class_current()["ascension"])
    merged_ascension.update(ascension)
    merged_ascension["status"] = str(merged_ascension.get("status") or "none").strip().lower()
    if merged_ascension["status"] not in CLASS_ASCENSION_STATUSES:
        merged_ascension["status"] = "none"
    merged_ascension["quest_id"] = str(merged_ascension.get("quest_id") or "").strip() or None
    merged_ascension["requirements"] = [str(entry).strip() for entry in (merged_ascension.get("requirements") or []) if str(entry).strip()]
    merged_ascension["result_hint"] = str(merged_ascension.get("result_hint") or "").strip() or None
    klass["ascension"] = merged_ascension
    klass["class_id"] = klass["id"]
    klass["class_name"] = klass["name"]
    klass["class_rank"] = klass["rank"]
    klass["class_level"] = klass["level"]
    klass["class_level_max"] = klass["level_max"]
    klass["class_xp"] = klass["xp"]
    klass["class_xp_to_next"] = klass["xp_next"]
    return klass

