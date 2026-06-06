import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from app.helpers import setup_helpers


@dataclass(frozen=True)
class CharacterSummaryStateDependencies:
    clean_creator_item_name: Callable[[Any], str]
    derive_age_stage: Callable[[int], str]
    enable_legacy_shadow_writeback: bool
    generate_character_attribute_weights: Callable[[Dict[str, Any], str, Dict[str, Any]], Dict[str, Any]]
    infer_age_years: Callable[[str], int]
    level_one_attribute_budget: Callable[[Dict[str, Any]], int]
    level_one_attribute_cap: Callable[[Dict[str, Any]], int]
    level_one_attributes_from_weights: Callable[[Dict[str, Any], Dict[str, int]], Dict[str, int]]
    normalize_attribute_weight_pool: Callable[..., Dict[str, int]]
    normalize_class_current: Callable[[Any], Optional[Dict[str, Any]]]
    normalize_creator_item_list: Callable[[Any], Any]
    normalize_world_time: Callable[[Dict[str, Any]], Dict[str, Any]]
    normalized_eval_text: Callable[[Any], str]
    reconcile_canonical_resources: Callable[[Dict[str, Any], Dict[str, Any]], None]
    reconcile_creator_inventory_items: Callable[[Dict[str, Any], Dict[str, Any]], None]
    rebuild_character_derived: Callable[[Dict[str, Any], Dict[str, Any], Dict[str, Any]], None]
    refresh_skill_progression: Callable[[Dict[str, Any]], None]
    strip_legacy_shadow_fields: Callable[[Dict[str, Any], Dict[str, Any]], None]
    sync_scars_into_appearance: Callable[[Dict[str, Any]], None]
    write_legacy_shadow_fields: Callable[[Dict[str, Any], Dict[str, Any]], None]


def build_world_summary(campaign: Dict[str, Any], *, deps: setup_helpers.SetupHelperDependencies) -> Dict[str, Any]:
    return setup_helpers.build_world_summary(campaign, deps=deps)


def build_character_summary(campaign: Dict[str, Any], slot_name: str, *, deps: setup_helpers.SetupHelperDependencies) -> Dict[str, Any]:
    return setup_helpers.build_character_summary(campaign, slot_name, deps=deps)


def apply_character_summary_to_state(campaign: Dict[str, Any], slot_name: str, *, deps: CharacterSummaryStateDependencies) -> None:
    setup_node = campaign["setup"]["characters"][slot_name]
    summary = setup_node["summary"]
    character = campaign["state"]["characters"][slot_name]
    world_time = deps.normalize_world_time(campaign["state"]["meta"])
    age_years = deps.infer_age_years(summary.get("age_bucket", ""))
    character["bio"] = {
        "name": summary.get("display_name", ""),
        "gender": summary.get("gender", ""),
        "age": summary.get("age_bucket", ""),
        "age_years": age_years,
        "age_stage": deps.derive_age_stage(age_years),
        "earth_life": summary.get("earth_life", ""),
        "personality": summary.get("personality_tags", []),
        "background_tags": summary.get("background_tags", []),
        "strength": summary.get("strength", ""),
        "weakness": summary.get("weakness", ""),
        "focus": summary.get("current_focus", ""),
        "goal": summary.get("first_goal", ""),
        "isekai_price": summary.get("isekai_price", ""),
        "earth_items": deps.normalize_creator_item_list(summary.get("earth_items", [])),
        "signature_item": deps.clean_creator_item_name(summary.get("signature_item", "")),
    }
    assignment = summary.get("attribute_assignment")
    if not isinstance(assignment, dict) or not isinstance(assignment.get("weights"), dict):
        assignment = deps.generate_character_attribute_weights(campaign, slot_name, summary)
        summary["attribute_assignment"] = assignment
    weights = deps.normalize_attribute_weight_pool(assignment.get("weights", {}), total=120)
    attributes = deps.level_one_attributes_from_weights(campaign, weights)
    summary["attribute_assignment"] = {
        "weights": weights,
        "source": assignment.get("source", "fallback"),
        "pool_total": 120,
        "level_one_budget": deps.level_one_attribute_budget(campaign),
        "level_one_cap": deps.level_one_attribute_cap(campaign),
        "values": attributes,
    }
    character["attributes"] = attributes
    character["aging"] = {
        "arrival_absolute_day": world_time["absolute_day"],
        "days_since_arrival": 0,
        "last_aged_absolute_day": world_time["absolute_day"],
        "age_effects_applied": [],
    }
    character.setdefault("progression", {})
    world_settings = (((campaign.get("state") or {}).get("world") or {}).get("settings") or {})
    character["progression"]["resource_name"] = str(world_settings.get("resource_name") or "Aether")
    character["progression"]["resource_current"] = int(character.get("res_current", 5) or 5)
    character["progression"]["resource_max"] = int(character.get("res_max", 5) or 5)
    class_start_mode = deps.normalized_eval_text(summary.get("class_start_mode", ""))
    if "ki" in class_start_mode:
        seed = summary.get("class_seed") or summary.get("current_focus") or summary.get("strength") or "Ãœberlebender"
        character["class_current"] = deps.normalize_class_current(
            {
                "id": f"class_{re.sub(r'[^a-z0-9]+', '_', deps.normalized_eval_text(seed)).strip('_') or 'wanderer'}",
                "name": str(seed).strip().title(),
                "rank": "F",
                "level": 1,
                "level_max": 10,
                "xp": 0,
                "xp_next": 100,
                "affinity_tags": [str(summary.get("strength") or "").strip().split("/", 1)[0].lower().replace(" ", "_"), str(summary.get("current_focus") or "").strip().split("/", 1)[0].lower().replace(" ", "_")],
                "description": f"Eine frÃ¼he Klasse, geformt aus {summary.get('strength', 'Ãœberleben')} und dem Fokus {summary.get('current_focus', 'Unbekannt')}.",
                "ascension": {"status": "none", "quest_id": None, "requirements": [], "result_hint": None},
            }
        )
    elif "selbst" in class_start_mode or (not class_start_mode and deps.normalized_eval_text(summary.get("class_custom_name", ""))):
        character["class_current"] = deps.normalize_class_current(
            {
                "id": f"class_{re.sub(r'[^a-z0-9]+', '_', deps.normalized_eval_text(summary.get('class_custom_name', '') or 'eigen')).strip('_') or 'eigen'}",
                "name": summary.get("class_custom_name") or "Eigene Klasse",
                "rank": "F",
                "level": 1,
                "level_max": 10,
                "xp": 0,
                "xp_next": 100,
                "affinity_tags": summary.get("class_custom_tags") or [],
                "description": summary.get("class_custom_description") or "",
                "ascension": {"status": "none", "quest_id": None, "requirements": [], "result_hint": None},
            }
        )
    else:
        character["class_current"] = None
    deps.reconcile_creator_inventory_items(campaign["state"], character)
    deps.refresh_skill_progression(character)
    deps.rebuild_character_derived(character, campaign["state"].get("items", {}), world_time)
    deps.reconcile_canonical_resources(character, world_settings)
    deps.strip_legacy_shadow_fields(character, world_settings)
    if deps.enable_legacy_shadow_writeback:
        deps.write_legacy_shadow_fields(character, world_settings)
    deps.sync_scars_into_appearance(character)
