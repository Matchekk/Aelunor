from __future__ import annotations

from typing import Any, Dict


LARGE_WORLD_CONTEXT_KEYS = {
    "beast_alias_index",
    "beast_types",
    "bible",
    "element_class_paths",
    "element_relations",
    "element_alias_index",
    "elements",
    "race_alias_index",
    "races",
}

LARGE_CHARACTER_CONTEXT_KEYS = {
    "living_profile",
}


def _truncate_text(value: Any, *, max_chars: int = 1600) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _compact_value(value: Any, *, max_items: int = 16, max_chars: int = 1600) -> Any:
    if isinstance(value, str):
        return _truncate_text(value, max_chars=max_chars)
    if isinstance(value, list):
        return [_compact_value(entry, max_items=max_items, max_chars=max_chars) for entry in value[:max_items]]
    if isinstance(value, dict):
        compact: Dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= max_items:
                compact["_omitted_count"] = len(value) - max_items
                break
            compact[str(key)] = _compact_value(item, max_items=max_items, max_chars=max_chars)
        return compact
    return value


def compact_setup_for_turn_context(setup: Any) -> Dict[str, Any]:
    if not isinstance(setup, dict):
        return {}
    world = setup.get("world") or {}
    characters = setup.get("characters") or {}
    return {
        "version": setup.get("version"),
        "engine": setup.get("engine") or {},
        "world": {
            "completed": bool((world or {}).get("completed")),
            "answers": _compact_value((world or {}).get("answers") or {}, max_items=32, max_chars=1200),
            "summary": _compact_value((world or {}).get("summary") or {}, max_items=32, max_chars=1200),
        },
        "characters": {
            slot_name: {
                "completed": bool((node or {}).get("completed")),
                "answers": _compact_value((node or {}).get("answers") or {}, max_items=32, max_chars=1200),
                "summary": _compact_value((node or {}).get("summary") or {}, max_items=32, max_chars=1200),
            }
            for slot_name, node in characters.items()
            if isinstance(node, dict)
        },
    }


# Interne Buchhaltung, die der Narrator nie braucht. meta.combat ist zudem ein
# exaktes Duplikat des top-level combat-Eintrags im CONTEXT_PACKET.
NARRATOR_IRRELEVANT_META_KEYS = {
    "extraction_quarantine",
    "combat",
    "timing",
    "intro_state",
    "migrations",
    "world_codex_seed",
}

# Volle GM-Texte nur fuer die juengsten Turns; aeltere werden angeschnitten.
RECENT_TURNS_FULL_TEXT_COUNT = 3
RECENT_TURNS_TRIMMED_GM_CHARS = 400

COMBAT_ACTION_QUEUE_MAX = 6
PLOTPOINTS_MAX = 16
PLOTPOINT_NOTES_MAX_CHARS = 280
_RESOLVED_PLOTPOINT_STATUSES = {"resolved", "done", "closed", "abgeschlossen"}


def compact_meta_for_turn_context(meta: Any) -> Dict[str, Any]:
    if not isinstance(meta, dict):
        return {}
    return {str(key): value for key, value in meta.items() if key not in NARRATOR_IRRELEVANT_META_KEYS}


def compact_combat_for_turn_context(combat: Any) -> Dict[str, Any]:
    if not isinstance(combat, dict):
        return {}
    compact = dict(combat)
    queue = compact.get("action_queue")
    if isinstance(queue, list) and len(queue) > COMBAT_ACTION_QUEUE_MAX:
        compact["action_queue"] = queue[-COMBAT_ACTION_QUEUE_MAX:]
        compact["action_queue_omitted_count"] = len(queue) - COMBAT_ACTION_QUEUE_MAX
    return compact


def compact_plotpoints_for_turn_context(plotpoints: Any) -> list:
    if not isinstance(plotpoints, list):
        return []
    open_points = [
        point
        for point in plotpoints
        if isinstance(point, dict)
        and str(point.get("status") or "").strip().lower() not in _RESOLVED_PLOTPOINT_STATUSES
    ]
    compact = []
    for point in open_points[-PLOTPOINTS_MAX:]:
        entry = dict(point)
        entry["notes"] = _truncate_text(entry.get("notes"), max_chars=PLOTPOINT_NOTES_MAX_CHARS)
        compact.append(entry)
    return compact


def compact_recent_turn_for_turn_context(entry: Dict[str, Any], *, full_text: bool) -> Dict[str, Any]:
    if full_text:
        return entry
    compact = dict(entry)
    compact["gm_text"] = _truncate_text(compact.get("gm_text"), max_chars=RECENT_TURNS_TRIMMED_GM_CHARS)
    compact.pop("requests", None)
    return compact


def compact_world_for_turn_context(world: Any) -> Dict[str, Any]:
    if not isinstance(world, dict):
        return {}
    compact: Dict[str, Any] = {}
    for key, value in world.items():
        if key in LARGE_WORLD_CONTEXT_KEYS:
            continue
        compact[str(key)] = _compact_value(value, max_items=16, max_chars=1400)
    return compact


def compact_character_for_turn_context(character: Any) -> Dict[str, Any]:
    if not isinstance(character, dict):
        return {}
    compact: Dict[str, Any] = {}
    for key, value in character.items():
        if key in LARGE_CHARACTER_CONTEXT_KEYS:
            continue
        compact[str(key)] = _compact_value(value, max_items=16, max_chars=1200)
    return compact
