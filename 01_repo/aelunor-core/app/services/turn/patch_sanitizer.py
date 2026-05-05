from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass(frozen=True)
class PatchSanitizerDependencies:
    normalize_patch_semantics: Callable[[Any], Dict[str, Any]]
    deep_copy: Callable[[Any], Any]
    clean_auto_item_name: Callable[[str], str]
    clean_creator_item_name: Callable[[str], str]
    ensure_item_shape: Callable[[str, Dict[str, Any]], Dict[str, Any]]
    infer_item_slot_from_definition: Callable[[Dict[str, Any]], str]
    normalize_equipment_slot_key: Callable[[Any], str]
    normalize_equipment_update_payload: Callable[[Any], Dict[str, str]]
    item_matches_equipment_slot: Callable[[Dict[str, Any], str], bool]
    normalize_class_current: Callable[[Any], Dict[str, Any]]
    skill_id_from_name: Callable[[str], str]
    normalize_dynamic_skill_state: Callable[..., Dict[str, Any]]
    resource_name_for_character: Callable[[Dict[str, Any], Optional[Dict[str, Any]]], str]
    normalize_skill_elements_for_world: Callable[[Dict[str, Any], Optional[Dict[str, Any]]], Dict[str, Any]]
    normalize_progression_event_list: Callable[..., list]
    normalize_injury_state: Callable[[Any], Optional[Dict[str, Any]]]
    normalize_scar_state: Callable[[Any], Optional[Dict[str, Any]]]
    normalize_plotpoint_entry: Callable[[Any], Optional[Dict[str, Any]]]
    normalize_plotpoint_update_entry: Callable[[Any], Optional[Dict[str, Any]]]
    clean_scene_name: Callable[[str], str]
    is_plausible_scene_name: Callable[[str], bool]
    is_generic_scene_identifier: Callable[[str, str], bool]
    clamp: Callable[[int, int, int], int]
    normalize_event_entry: Callable[[Any], Optional[str]]


_DEPS: Optional[PatchSanitizerDependencies] = None


def configure(deps: PatchSanitizerDependencies) -> None:
    global _DEPS
    _DEPS = deps


def _deps() -> PatchSanitizerDependencies:
    if _DEPS is None:
        raise RuntimeError("patch sanitizer dependencies are not configured")
    return _DEPS


def sanitize_patch(state: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    deps = _deps()
    patch = deps.normalize_patch_semantics(patch)
    sanitized = deps.deep_copy(patch)
    cleaned_items_new: Dict[str, Any] = {}
    for item_id, raw_item in ((sanitized.get("items_new") or {}).items()):
        if not isinstance(raw_item, dict):
            continue
        candidate_name = deps.clean_auto_item_name(str(raw_item.get("name") or ""))
        if not candidate_name:
            candidate_name = deps.clean_creator_item_name(str(raw_item.get("name") or ""))
        if not candidate_name:
            continue
        normalized_item = deps.ensure_item_shape(item_id, raw_item)
        normalized_item["name"] = candidate_name[0].upper() + candidate_name[1:] if candidate_name else candidate_name
        inferred_slot = deps.infer_item_slot_from_definition(normalized_item)
        if inferred_slot and not deps.normalize_equipment_slot_key(normalized_item.get("slot")):
            normalized_item["slot"] = inferred_slot
        cleaned_items_new[item_id] = normalized_item
    sanitized["items_new"] = cleaned_items_new
    known_items = set((state.get("items") or {}).keys()) | set(cleaned_items_new.keys())
    characters = sanitized.get("characters") or {}
    for slot_name in list(characters.keys()):
        if slot_name not in state["characters"]:
            characters.pop(slot_name, None)
            continue
        upd = characters[slot_name]
        upd["inventory_add"] = [item_id for item_id in (upd.get("inventory_add") or []) if item_id in known_items]
        eq = deps.normalize_equipment_update_payload(upd.get("equip_set") or upd.get("equipment_set") or {})
        for equip_slot in list(eq.keys()):
            item_id = eq.get(equip_slot, "")
            if not item_id or item_id not in known_items:
                eq.pop(equip_slot, None)
                continue
            item_ref = (state.get("items", {}) or {}).get(item_id) or cleaned_items_new.get(item_id) or {}
            if not deps.item_matches_equipment_slot(item_ref, equip_slot):
                eq.pop(equip_slot, None)
        if eq:
            upd["equipment_set"] = eq
            upd.pop("equip_set", None)
        else:
            upd.pop("equipment_set", None)
            upd.pop("equip_set", None)
        upd.pop("derived", None)
        if "class_set" in upd:
            normalized_class = deps.normalize_class_current(upd.get("class_set"))
            if normalized_class:
                upd["class_set"] = normalized_class
            else:
                upd.pop("class_set", None)
        if upd.get("class_update"):
            upd["class_update"] = deps.deep_copy(upd["class_update"])
        if upd.get("skills_set"):
            normalized_skill_updates = {}
            for raw_key, raw_value in (upd.get("skills_set") or {}).items():
                skill_name = (raw_value or {}).get("name", raw_key) if isinstance(raw_value, dict) else raw_key
                skill_key = deps.skill_id_from_name(str(skill_name or raw_key))
                normalized_skill_updates[skill_key] = deps.normalize_dynamic_skill_state(
                    raw_value,
                    skill_id=skill_key,
                    skill_name=str(skill_name or raw_key),
                    resource_name=deps.resource_name_for_character(
                        state["characters"][slot_name],
                        ((state.get("world") or {}).get("settings") or {}),
                    ),
                )
                normalized_skill_updates[skill_key] = deps.normalize_skill_elements_for_world(
                    normalized_skill_updates[skill_key],
                    state.get("world") if isinstance(state.get("world"), dict) else {},
                )
            upd["skills_set"] = normalized_skill_updates
        if upd.get("skills_delta"):
            normalized_skill_deltas = {}
            for raw_key, raw_value in (upd.get("skills_delta") or {}).items():
                skill_name = (raw_value or {}).get("name", raw_key) if isinstance(raw_value, dict) else raw_key
                skill_key = deps.skill_id_from_name(str(skill_name or raw_key))
                existing_delta = normalized_skill_deltas.get(skill_key)
                if isinstance(existing_delta, dict) and isinstance(raw_value, dict):
                    merged_delta = deps.deep_copy(existing_delta)
                    merged_delta.update(deps.deep_copy(raw_value))
                    normalized_skill_deltas[skill_key] = merged_delta
                elif isinstance(existing_delta, int) and isinstance(raw_value, int):
                    normalized_skill_deltas[skill_key] = existing_delta + raw_value
                else:
                    normalized_skill_deltas[skill_key] = deps.deep_copy(raw_value)
            upd["skills_delta"] = normalized_skill_deltas
        if "progression_events" in upd:
            source_turn = int((state.get("meta") or {}).get("turn", 0) or 0) + 1
            upd["progression_events"] = deps.normalize_progression_event_list(
                upd.get("progression_events"),
                actor=slot_name,
                source_turn=source_turn,
            )
        if upd.get("injuries_add"):
            upd["injuries_add"] = [entry for entry in (deps.normalize_injury_state(raw) for raw in (upd.get("injuries_add") or [])) if entry]
        if upd.get("injuries_update"):
            cleaned_updates = []
            for raw in (upd.get("injuries_update") or []):
                if isinstance(raw, dict) and str(raw.get("id") or "").strip():
                    cleaned_updates.append(deps.deep_copy(raw))
            upd["injuries_update"] = cleaned_updates
        if upd.get("injuries_heal"):
            upd["injuries_heal"] = [str(entry).strip() for entry in (upd.get("injuries_heal") or []) if str(entry).strip()]
        if upd.get("scars_add"):
            upd["scars_add"] = [entry for entry in (deps.normalize_scar_state(raw) for raw in (upd.get("scars_add") or [])) if entry]
    sanitized["characters"] = characters
    sanitized["plotpoints_add"] = [
        entry
        for entry in (deps.normalize_plotpoint_entry(raw) for raw in (sanitized.get("plotpoints_add") or []))
        if entry
    ]
    sanitized["plotpoints_update"] = [
        entry
        for entry in (deps.normalize_plotpoint_update_entry(raw) for raw in (sanitized.get("plotpoints_update") or []))
        if entry
    ]
    sanitized_map_nodes: List[Dict[str, Any]] = []
    for node in (sanitized.get("map_add_nodes") or []):
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or "").strip()
        if not node_id:
            continue
        node_name = deps.clean_scene_name(str(node.get("name") or node.get("id") or ""))
        if not node_name:
            continue
        if not deps.is_plausible_scene_name(node_name):
            continue
        if deps.is_generic_scene_identifier(node_id, node_name):
            continue
        sanitized_map_nodes.append(
            {
                "id": node_id,
                "name": node_name,
                "type": str(node.get("type") or "location").strip() or "location",
                "danger": deps.clamp(int(node.get("danger", 1) or 1), 0, 10),
                "discovered": bool(node.get("discovered", True)),
            }
        )
    sanitized["map_add_nodes"] = sanitized_map_nodes
    sanitized["map_add_edges"] = [
        {
            "from": str(edge.get("from") or "").strip(),
            "to": str(edge.get("to") or "").strip(),
            "kind": str(edge.get("kind") or "path").strip() or "path",
        }
        for edge in (sanitized.get("map_add_edges") or [])
        if isinstance(edge, dict) and str(edge.get("from") or "").strip() and str(edge.get("to") or "").strip()
    ]
    sanitized["events_add"] = [
        entry
        for entry in (deps.normalize_event_entry(raw) for raw in (sanitized.get("events_add") or []))
        if entry
    ]
    return sanitized
