from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Set


@dataclass(frozen=True)
class PatchValidatorDependencies:
    normalize_patch_semantics: Callable[[Any], Dict[str, Any]]
    resource_name_for_character: Callable[[Dict[str, Any], Optional[Dict[str, Any]]], str]
    normalize_dynamic_skill_state: Callable[..., Dict[str, Any]]
    normalize_skill_elements_for_world: Callable[[Dict[str, Any], Optional[Dict[str, Any]]], Dict[str, Any]]
    normalized_eval_text: Callable[[Any], str]
    normalize_class_current: Callable[[Any], Dict[str, Any]]
    resolve_class_element_id: Callable[[Optional[Dict[str, Any]], Dict[str, Any]], Optional[str]]
    normalize_skill_rank: Callable[[Any], str]
    normalize_progression_event_list: Callable[..., list]
    is_skill_manifestation_name_plausible: Callable[[str, str], bool]
    normalize_injury_state: Callable[[Any], Optional[Dict[str, Any]]]
    normalize_scar_state: Callable[[Any], Optional[Dict[str, Any]]]
    normalize_equipment_update_payload: Callable[[Any], Dict[str, str]]
    item_matches_equipment_slot: Callable[[Dict[str, Any], str], bool]
    universal_skill_like_names: Set[str]
    injury_severities: Set[str]
    injury_healing_stages: Set[str]


_DEPS: Optional[PatchValidatorDependencies] = None


def configure(deps: PatchValidatorDependencies) -> None:
    global _DEPS
    _DEPS = deps


def _deps() -> PatchValidatorDependencies:
    if _DEPS is None:
        raise RuntimeError("patch validator dependencies are not configured")
    return _DEPS


def validate_patch(state: Dict[str, Any], patch: Dict[str, Any]) -> None:
    deps = _deps()
    patch = deps.normalize_patch_semantics(patch)
    known_scene_ids = set((state.get("scenes") or {}).keys()) | set(((state.get("map") or {}).get("nodes") or {}).keys()) | {
        str(node.get("id") or "").strip() for node in (patch.get("map_add_nodes") or []) if isinstance(node, dict)
    }
    for slot_name, upd in (patch.get("characters") or {}).items():
        if slot_name not in state["characters"]:
            raise ValueError(f"Unbekannter Slot im Patch: {slot_name}")
        if "derived" in upd:
            raise ValueError(f"Derived stats duerfen nicht direkt gepatcht werden: {slot_name}")
        if upd.get("scene_id") and upd.get("scene_id") not in known_scene_ids:
            raise ValueError(f"Unknown scene id for {slot_name}: {upd.get('scene_id')}")
        resource_name = deps.resource_name_for_character(
            state["characters"][slot_name],
            ((state.get("world") or {}).get("settings") or {}),
        )
        world_model = state.get("world") if isinstance(state.get("world"), dict) else {}
        for skill_id, skill_value in (upd.get("skills_set") or {}).items():
            normalized_skill = deps.normalize_dynamic_skill_state(
                skill_value,
                skill_id=str(skill_id),
                skill_name=(skill_value or {}).get("name", skill_id) if isinstance(skill_value, dict) else str(skill_id),
                resource_name=resource_name,
            )
            normalized_skill = deps.normalize_skill_elements_for_world(normalized_skill, world_model)
            if normalized_skill.get("elements") and not all(
                element_id in ((world_model.get("elements") or {}).keys())
                for element_id in (normalized_skill.get("elements") or [])
            ):
                raise ValueError(f"Skill mit unbekanntem Element auf {slot_name}: {normalized_skill.get('name')}")
            cost = normalized_skill.get("cost")
            if cost and str(cost.get("resource") or "") != resource_name:
                raise ValueError(f"Skill-Kosten nutzen fuer {slot_name} die falsche Ressource: {normalized_skill.get('name')}")
            combat_relevant = bool(
                {
                    deps.normalized_eval_text(tag)
                    for tag in (normalized_skill.get("tags") or [])
                    if deps.normalized_eval_text(tag)
                }
                & {"kampf", "magie", "zauber", "waffe", "technik", "rune", "shadow", "holy"}
            )
            if combat_relevant and not cost:
                raise ValueError(f"Kampf-Skill ohne Kostenvertrag auf {slot_name}: {normalized_skill.get('name')}")
        for skill_id, delta in (upd.get("skills_delta") or {}).items():
            if isinstance(delta, dict):
                cost = (delta.get("cost") or {})
                if cost and str(cost.get("resource") or "") != resource_name:
                    raise ValueError(f"Skill-Delta nutzt fuer {slot_name} die falsche Ressource: {skill_id}")
        for ability in upd.get("abilities_add", []) or []:
            if ability.get("owner") != slot_name:
                raise ValueError(f"Ability owner mismatch: {ability.get('id')} owner={ability.get('owner')} expected={slot_name}")
            if deps.normalized_eval_text(ability.get("name", "")) in deps.universal_skill_like_names:
                raise ValueError(f"Ability wirkt wie universelle Fertigkeit auf {slot_name}: {ability.get('name')}")
        for faction in upd.get("factions_add", []) or []:
            if not faction.get("faction_id"):
                raise ValueError(f"Faction membership without faction_id on {slot_name}")
        class_set = deps.normalize_class_current(upd.get("class_set"))
        class_update = upd.get("class_update") or {}
        if upd.get("class_set") and not class_set:
            raise ValueError(f"class_set ohne gueltige Klasse auf {slot_name}")
        if class_set and not (class_set.get("affinity_tags") or []):
            raise ValueError(f"class_set ohne affinity_tags auf {slot_name}")
        if class_set:
            resolved_class_element = deps.resolve_class_element_id(class_set, world_model)
            if class_set.get("element_id") and not resolved_class_element:
                raise ValueError(f"class_set mit unbekanntem Element auf {slot_name}: {class_set.get('element_id')}")
        if class_update and not state["characters"][slot_name].get("class_current"):
            raise ValueError(f"class_update ohne bestehende Klasse auf {slot_name}")
        if class_update.get("rank") and deps.normalize_skill_rank(class_update.get("rank")) != str(class_update.get("rank")).upper():
            raise ValueError(f"class_update mit ungueltigem Rank auf {slot_name}")
        if "progression_events" in upd:
            normalized_events = deps.normalize_progression_event_list(
                upd.get("progression_events"),
                actor=slot_name,
                source_turn=int((state.get("meta") or {}).get("turn", 0) or 0) + 1,
            )
            if len(normalized_events) != len(upd.get("progression_events") or []):
                raise ValueError(f"ungueltige progression_events auf {slot_name}")
            for event in normalized_events:
                if str(event.get("actor") or "").strip() != slot_name:
                    raise ValueError(f"progression_event actor mismatch auf {slot_name}")
                if str(event.get("type") or "").strip().lower() == "skill_manifestation":
                    skill_payload = event.get("skill") if isinstance(event.get("skill"), dict) else {}
                    if not skill_payload and not str(event.get("target_skill_id") or "").strip():
                        raise ValueError(f"skill_manifestation ohne Skill-Definition auf {slot_name}")
                    skill_name = str((skill_payload or {}).get("name") or "").strip()
                    actor_name = str((((state.get("characters") or {}).get(slot_name) or {}).get("bio") or {}).get("name") or slot_name)
                    if skill_name and not deps.is_skill_manifestation_name_plausible(skill_name, actor_name):
                        raise ValueError(f"skill_manifestation mit unplausiblem Skillnamen auf {slot_name}: {skill_name}")
                    if skill_payload:
                        normalized_manifest = deps.normalize_dynamic_skill_state(
                            skill_payload,
                            skill_id=str((skill_payload or {}).get("id") or ""),
                            skill_name=str((skill_payload or {}).get("name") or ""),
                            resource_name=resource_name,
                        )
                        normalized_manifest = deps.normalize_skill_elements_for_world(
                            normalized_manifest,
                            world_model,
                        )
                        if normalized_manifest.get("elements") and not all(
                            element_id in ((world_model.get("elements") or {}).keys())
                            for element_id in (normalized_manifest.get("elements") or [])
                        ):
                            raise ValueError(f"skill_manifestation mit unbekanntem Element auf {slot_name}")
        for injury in upd.get("injuries_add", []) or []:
            if not deps.normalize_injury_state(injury):
                raise ValueError(f"ungueltige Injury auf {slot_name}")
        for injury in upd.get("injuries_update", []) or []:
            if not isinstance(injury, dict) or not str(injury.get("id") or "").strip():
                raise ValueError(f"injuries_update ohne id auf {slot_name}")
            if injury.get("severity") and str(injury.get("severity")).strip().lower() not in deps.injury_severities:
                raise ValueError(f"injuries_update mit ungueltiger severity auf {slot_name}")
            if injury.get("healing_stage") and str(injury.get("healing_stage")).strip().lower() not in deps.injury_healing_stages:
                raise ValueError(f"injuries_update mit ungueltiger healing_stage auf {slot_name}")
        for scar in upd.get("scars_add", []) or []:
            if not deps.normalize_scar_state(scar):
                raise ValueError(f"ungueltige Scar auf {slot_name}")
        resources_set = upd.get("resources_set") or {}
        for key in ("hp_current", "hp_max", "sta_current", "sta_max", "res_current", "res_max", "carry_current", "carry_max"):
            if key in resources_set and int(resources_set.get(key, 0) or 0) < 0:
                raise ValueError(f"negative Ressource in resources_set fuer {slot_name}: {key}")

    items_new = patch.get("items_new") or {}
    for item_id, item in (items_new or {}).items():
        if not isinstance(item, dict):
            raise ValueError(f"Ungültiges Item für {item_id}")
        weapon_profile = item.get("weapon_profile") if isinstance(item.get("weapon_profile"), dict) else {}
        if weapon_profile:
            for numeric_key in ("attack_bonus", "damage_min", "damage_max"):
                if numeric_key in weapon_profile and not isinstance(weapon_profile.get(numeric_key), int):
                    raise ValueError(f"weapon_profile.{numeric_key} muss integer sein ({item_id})")
    known_items = set(state.get("items", {}).keys()) | set(items_new.keys())
    for slot_name, upd in (patch.get("characters") or {}).items():
        for item_id in upd.get("inventory_add", []) or []:
            if item_id not in known_items:
                raise ValueError(f"Unknown item id in inventory_add for {slot_name}: {item_id}")
        eq = deps.normalize_equipment_update_payload(upd.get("equip_set") or upd.get("equipment_set") or {})
        for equip_slot, value in eq.items():
            if value and value not in known_items:
                raise ValueError(f"Unknown item id in equipment_set.{equip_slot} for {slot_name}: {value}")
            if value:
                item_ref = (state.get("items", {}) or {}).get(value) or (items_new.get(value) or {})
                if not deps.item_matches_equipment_slot(item_ref, equip_slot):
                    raise ValueError(f"Item {value} passt nicht in equipment_set.{equip_slot} fuer {slot_name}")
