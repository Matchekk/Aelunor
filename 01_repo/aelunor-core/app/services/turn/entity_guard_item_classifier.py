from __future__ import annotations

import re
from typing import Any


def looks_like_item_payload(item: dict) -> bool:
    if not isinstance(item, dict):
        return False
    if looks_like_moment_or_plotpoint(item, _text(item.get("name") or item.get("title"))):
        return False
    item_context_keys = {
        "slot",
        "rarity",
        "weight",
        "tags",
        "effects",
        "modifiers",
        "weapon_profile",
        "durability",
        "description",
        "item_type",
        "kind",
        "stack",
        "quantity",
        "value",
    }
    if any(key in item and item.get(key) not in (None, "", [], {}) for key in item_context_keys):
        return True
    item_id = _text(item.get("id"))
    if item_id.lower().startswith("item_"):
        return True
    name = _text(item.get("name"))
    if not name or looks_like_moment_title(name):
        return False
    return looks_equipment_name(name)


def looks_like_moment_or_plotpoint(item: dict, name: str) -> bool:
    text = _norm(" ".join(str(item.get(key) or "") for key in ("type", "kind", "category", "source", "notes", "description")) + " " + name)
    return any(token in text for token in ("event", "moment", "plot", "plotpoint", "scene", "beat", "attention", "rettung", "gerettet", "zurueck", "zuruck", "spat", "spaet"))


def looks_like_moment_title(name: str) -> bool:
    text = _norm(name)
    return any(token in text for token in ("augenbraue", "hand zurueck", "hand zuruck", "aufmerksamkeit", "rettung", "gerettet", "zu spaet", "zu spat"))


def looks_equipment_name(name: str) -> bool:
    text = _norm(name)
    return any(
        token in text
        for token in (
            "gear",
            "bracer",
            "stabilizer",
            "klinge",
            "siegel",
            "glas",
            "stahl",
            "amulet",
            "ring",
            "mask",
            "blade",
            "sword",
            "armor",
            "robe",
            "potion",
            "trank",
            "relic",
            "tool",
            "support",
        )
    )


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm(value: Any) -> str:
    text = _text(value).lower()
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()
