from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List

from app.services.turn.entity_guard_item_classifier import looks_like_item_payload, looks_like_moment_or_plotpoint
from app.services.world.entity_guard import build_entity_guard_report


def collect_patch_entities_for_guard(patch: dict | None) -> list[dict]:
    if not isinstance(patch, dict):
        return []
    entities: List[Dict[str, Any]] = []
    entities.extend(collect_item_entities(patch))
    entities.extend(collect_skill_entities(patch))
    entities.extend(collect_class_entities(patch))
    entities.extend(collect_location_entities(patch))
    entities.extend(collect_plotpoint_entities(patch))
    entities.extend(collect_faction_entities(patch))
    return _dedupe_entities(entities)


def build_patch_entity_guard_report(
    patch: dict | None,
    world_bible: dict | None = None,
    *,
    max_reports: int = 20,
) -> dict:
    entities = collect_patch_entities_for_guard(patch)
    report = build_entity_guard_report(entities[: max(0, int(max_reports or 0))], world_bible)
    for entity, entity_report in zip(entities, report.get("reports") or []):
        if entity.get("source_paths"):
            entity_report["source_paths"] = list(entity.get("source_paths") or [])
        elif entity.get("source_path"):
            entity_report["source_path"] = entity.get("source_path")
        if entity.get("slot_id"):
            entity_report["slot_id"] = entity.get("slot_id")
    return compact_entity_guard_report(report, max_reports=max_reports)


def compact_entity_guard_report(report: dict | None, *, max_reports: int = 12) -> dict:
    if not isinstance(report, dict):
        return {"summary": _empty_summary(), "reports": []}
    compact_reports = []
    for entry in (report.get("reports") or [])[: max(0, int(max_reports or 0))]:
        if not isinstance(entry, dict):
            continue
        compact_reports.append(
            {
                "entity_type": str(entry.get("entity_type") or ""),
                "name": str(entry.get("name") or ""),
                "status": str(entry.get("status") or "unknown"),
                "score": int(entry.get("score", 0) or 0),
                "reasons": [str(reason) for reason in (entry.get("reasons") or [])[:3]],
                "forbidden_terms_found": list(entry.get("forbidden_terms_found") or []),
                "avoid_terms_found": list(entry.get("avoid_terms_found") or []),
                "matched_roots": list(entry.get("matched_roots") or [])[:6],
                "source_path": entry.get("source_path", ""),
                "source_paths": list(entry.get("source_paths") or []),
                "slot_id": str(entry.get("slot_id") or ""),
                "requires_review": bool(entry.get("requires_review")),
            }
        )
    summary = dict(report.get("summary") or _empty_summary())
    summary["stored_reports"] = len(compact_reports)
    return {"summary": summary, "reports": compact_reports}


def entity_guard_report_has_findings(report: dict | None) -> bool:
    if not isinstance(report, dict):
        return False
    return any(
        isinstance(entry, dict) and entry.get("requires_review")
        for entry in (report.get("reports") or [])
    )


def collect_item_entities(patch: dict) -> list[dict]:
    entities = []
    items_new = patch.get("items_new") or {}
    if isinstance(items_new, dict):
        iterable = items_new.items()
    elif isinstance(items_new, list):
        iterable = enumerate(items_new)
    else:
        iterable = []
    for key, item in iterable:
        item = item if isinstance(item, dict) else {}
        if not looks_like_item_payload(item):
            continue
        name = _name_or_readable_id(item.get("name"), item.get("id") or key)
        if name:
            entities.append({"entity_type": "item", "name": name, "source_path": f"items_new[{key}].name"})
    return entities


def collect_skill_entities(patch: dict) -> list[dict]:
    entities = []
    for update_root, root_label in _character_update_roots(patch):
        for slot_id, update in update_root.items():
            if not isinstance(update, dict):
                continue
            for field in ("skills_set", "skills_add", "skills_update"):
                for key, skill in _iter_named_payloads(update.get(field)):
                    name = _name_or_readable_id((skill or {}).get("name") if isinstance(skill, dict) else "", key)
                    if name:
                        entities.append(
                            {
                                "entity_type": "skill",
                                "name": name,
                                "source_path": f"{root_label}.{slot_id}.{field}.{key}.name",
                                "slot_id": str(slot_id),
                            }
                        )
    return entities


def collect_class_entities(patch: dict) -> list[dict]:
    entities = []
    for update_root, root_label in _character_update_roots(patch):
        for slot_id, update in update_root.items():
            if not isinstance(update, dict):
                continue
            for field in ("class_set", "class_update", "class_current"):
                payload = update.get(field)
                if isinstance(payload, dict):
                    name = _name_or_readable_id(payload.get("name"), payload.get("id"))
                    if name:
                        entities.append(
                            {
                                "entity_type": "class",
                                "name": name,
                                "source_path": f"{root_label}.{slot_id}.{field}.name",
                                "slot_id": str(slot_id),
                            }
                        )
    return entities


def collect_location_entities(patch: dict) -> list[dict]:
    entities = []
    for key in ("map_add_nodes", "locations_add", "scenes_add"):
        for index, node in enumerate(_list(patch.get(key))):
            name = _node_name(node)
            if name:
                entities.append({"entity_type": "location", "name": name, "source_path": f"{key}[{index}].name"})
    map_payload = patch.get("map") if isinstance(patch.get("map"), dict) else {}
    for key in ("nodes_add", "locations_add"):
        for index, node in enumerate(_list(map_payload.get(key))):
            name = _node_name(node)
            if name:
                entities.append({"entity_type": "location", "name": name, "source_path": f"map.{key}[{index}].name"})
    return entities


def collect_plotpoint_entities(patch: dict) -> list[dict]:
    entities = []
    for key in ("plotpoints_add", "plotpoints_update"):
        for index, plotpoint in enumerate(_list(patch.get(key))):
            if isinstance(plotpoint, dict):
                name = _text(plotpoint.get("title") or plotpoint.get("name"))
                if name:
                    entities.append({"entity_type": "plotpoint", "name": name, "source_path": f"{key}[{index}].title"})
    items_new = patch.get("items_new") or {}
    if isinstance(items_new, dict):
        iterable = items_new.items()
    elif isinstance(items_new, list):
        iterable = enumerate(items_new)
    else:
        iterable = []
    for key, item in iterable:
        if not isinstance(item, dict) or looks_like_item_payload(item):
            continue
        name = _text(item.get("title") or item.get("name"))
        if name and looks_like_moment_or_plotpoint(item, name):
            entities.append({"entity_type": "plotpoint", "name": name, "source_path": f"items_new[{key}].title"})
    return entities


def collect_faction_entities(patch: dict) -> list[dict]:
    entities = []
    for key in ("factions_add", "factions_update"):
        for index, faction in enumerate(_list(patch.get(key))):
            name = _node_name(faction)
            if name:
                entities.append({"entity_type": "faction", "name": name, "source_path": f"{key}[{index}].name"})
    for update_root, root_label in _character_update_roots(patch):
        for slot_id, update in update_root.items():
            if not isinstance(update, dict):
                continue
            faction_join = update.get("faction_join")
            if isinstance(faction_join, dict):
                name = _node_name(faction_join)
                if name:
                    entities.append({"entity_type": "faction", "name": name, "source_path": f"{root_label}.{slot_id}.faction_join.name", "slot_id": str(slot_id)})
            for index, faction in enumerate(_list(update.get("faction_memberships"))):
                name = _node_name(faction)
                if name:
                    entities.append({"entity_type": "faction", "name": name, "source_path": f"{root_label}.{slot_id}.faction_memberships[{index}].name", "slot_id": str(slot_id)})
    return entities


def _character_update_roots(patch: dict) -> Iterable[tuple[dict, str]]:
    for key in ("characters", "character_updates"):
        root = patch.get(key)
        if isinstance(root, dict):
            yield root, key


def _iter_named_payloads(value: Any) -> Iterable[tuple[Any, dict]]:
    if isinstance(value, dict):
        for key, payload in value.items():
            yield key, payload if isinstance(payload, dict) else {}
    elif isinstance(value, list):
        for index, payload in enumerate(value):
            yield index, payload if isinstance(payload, dict) else {}


def _dedupe_entities(entities: list[dict]) -> list[dict]:
    deduped: Dict[str, Dict[str, Any]] = {}
    for entity in entities:
        name = _text(entity.get("name"))
        entity_type = _text(entity.get("entity_type"))
        if not name or not entity_type:
            continue
        key = f"{entity_type}:{_norm(name)}"
        current = deduped.setdefault(key, {**entity, "source_paths": []})
        source_path = entity.get("source_path")
        if source_path and source_path not in current["source_paths"]:
            current["source_paths"].append(source_path)
        if entity.get("slot_id") and not current.get("slot_id"):
            current["slot_id"] = entity.get("slot_id")
    return list(deduped.values())


def _node_name(value: Any) -> str:
    if isinstance(value, dict):
        return _text(value.get("name") or value.get("label") or value.get("title"))
    return ""


def _name_or_readable_id(name: Any, fallback_id: Any) -> str:
    name_text = _text(name)
    if name_text:
        return name_text
    fallback = _text(fallback_id)
    return fallback if _looks_human_readable_id(fallback) else ""


def _looks_human_readable_id(value: str) -> bool:
    text = _text(value)
    if not text:
        return False
    return not bool(re.fullmatch(r"(item|skill|class|loc|node|id)?_?[a-f0-9]{6,}", text.lower()))


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm(value: Any) -> str:
    text = _text(value).lower()
    text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _empty_summary() -> dict:
    return {"total": 0, "ok": 0, "weak": 0, "generic": 0, "forbidden": 0, "needs_review": 0, "unknown": 0}
