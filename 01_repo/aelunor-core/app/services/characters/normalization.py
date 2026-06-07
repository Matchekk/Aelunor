"""High-level character-state normalization and derived-stat rebuilds."""

from typing import Any, Dict, List, Optional

from app.config.feature_flags import ENABLE_LEGACY_SHADOW_WRITEBACK
from app.config.progression import SKILL_KEYS
from app.core.ids import deep_copy, make_id
from app.services.characters.appearance_state import (
    age_character_if_needed,
    build_age_modifiers,
    normalize_age_fields,
    normalize_appearance_state,
)
from app.services.characters.appearance_summary import rebuild_character_appearance
from app.services.characters.defaults import blank_character_state
from app.services.characters.derived_stats import (
    calculate_armor,
    calculate_attack_rating,
    calculate_carry_limit,
    calculate_carry_weight,
    calculate_defense,
    calculate_initiative,
    calculate_resistances,
)
from app.services.characters.living_profile import normalize_living_profile
from app.services.characters.combat_state import calculate_combat_flags
from app.services.characters.effects import migrate_effects_from_conditions
from app.services.characters.resource_maxima import (
    ensure_character_modifier_shape,
    rebuild_resource_maxima,
)
from app.services.characters.resources import (
    ingest_legacy_resources_into_canonical,
    reconcile_canonical_resources,
    resource_name_for_character,
    strip_legacy_shadow_fields,
    write_legacy_shadow_fields,
)
from app.services.items.inventory import ensure_item_shape
from app.services.progression.classes import migrate_legacy_role_to_class
from app.services.progression.skills import (
    ensure_character_progression_core,
    ensure_progression_shape,
    extract_skill_entries_for_character,
    normalize_skill_state,
    normalize_skill_store,
)
from app.services.world.injury_state import normalize_injury_state, normalize_scar_state
from app.services.world.math_utils import clamp
from app.services.world.progression import next_character_xp_for_level, normalize_class_current
from app.services.world.state_defaults import default_world_time
from app.services.world.time import normalize_world_time


def sync_scars_into_appearance(character: Dict[str, Any]) -> None:
    appearance = character.setdefault("appearance", {})
    appearance["scars"] = [
        {
            "id": scar.get("id"),
            "label": scar.get("title"),
            "source": scar.get("description"),
            "turn_number": scar.get("created_turn", 0),
            "visible": True,
        }
        for scar in (character.get("scars") or [])
        if isinstance(scar, dict) and scar.get("title")
    ]


def resolve_injury_healing(character: Dict[str, Any], current_turn: int) -> List[Dict[str, Any]]:
    new_scars: List[Dict[str, Any]] = []
    remaining_injuries: List[Dict[str, Any]] = []
    existing_titles = {entry.get("title") for entry in (character.get("scars") or []) if isinstance(entry, dict)}
    for injury in (character.get("injuries") or []):
        normalized = normalize_injury_state(injury)
        if not normalized:
            continue
        if normalized["healing_stage"] == "geheilt":
            if normalized["will_scar"]:
                scar_title = normalized["title"].replace("Schnitt", "Narbe").replace("Verletzung", "Narbe")
                scar = normalize_scar_state(
                    {
                        "id": make_id("scar"),
                        "title": scar_title,
                        "origin_injury_id": normalized["id"],
                        "description": normalized["notes"] or normalized["title"],
                        "created_turn": current_turn,
                    }
                )
                if scar and scar["title"] not in existing_titles:
                    new_scars.append(scar)
                    existing_titles.add(scar["title"])
            continue
        remaining_injuries.append(normalized)
    if new_scars:
        character.setdefault("scars", []).extend(new_scars)
    character["injuries"] = remaining_injuries
    sync_scars_into_appearance(character)
    return new_scars


def looks_like_legacy_seeded_skills(skills: Dict[str, Any]) -> bool:
    if not skills or set(skills.keys()) != set(SKILL_KEYS):
        return False
    for skill_name in SKILL_KEYS:
        skill = normalize_skill_state(skill_name, skills.get(skill_name))
        if int(skill.get("level", 0) or 0) != 1:
            return False
        if int(skill.get("xp", 0) or 0) != 0:
            return False
        if skill.get("path") or skill.get("evolutions") or skill.get("fusion_candidates"):
            return False
    return True


def sync_legacy_character_fields(character: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> None:
    # Deprecated compatibility helper. Only active when explicit legacy writeback is enabled.
    if not ENABLE_LEGACY_SHADOW_WRITEBACK:
        return
    write_legacy_shadow_fields(character, world_settings)
    character["conditions"] = [
        effect.get("name", "")
        for effect in (character.get("effects") or [])
        if effect.get("visible", True) and effect.get("name")
    ][:6]


def rebuild_character_derived(
    character: Dict[str, Any],
    items_db: Dict[str, Any],
    world_time: Optional[Dict[str, Any]] = None,
) -> None:
    ensure_progression_shape(character)
    ensure_character_progression_core(character)
    effective_world_time = normalize_world_time({"world_time": world_time or default_world_time()})
    normalize_age_fields(character, effective_world_time)
    age_character_if_needed(character, effective_world_time)
    age_modifiers = build_age_modifiers(character)
    ensure_character_modifier_shape(character)
    current_corruption = (character.setdefault("resources", {}).setdefault("corruption", {}) or {}).get("current", 0)
    max_corruption = (character["resources"].get("corruption") or {}).get("max", 0)
    if int(max_corruption or 0) <= 10:
        character["resources"]["corruption"]["current"] = clamp(int(current_corruption or 0) * 10, 0, 100)
        character["resources"]["corruption"]["max"] = 100

    items_db = {item_id: ensure_item_shape(item_id, item) for item_id, item in (items_db or {}).items()}
    rebuild_resource_maxima(character, items_db, age_modifiers)
    rebuild_character_appearance(character, effective_world_time)
    carry_limit = calculate_carry_limit(character)
    carry_weight = calculate_carry_weight(character, items_db)
    encumbrance_state = "normal"
    if carry_weight > carry_limit and carry_weight <= int(carry_limit * 1.25):
        encumbrance_state = "burdened"
    elif carry_weight > int(carry_limit * 1.25):
        encumbrance_state = "overloaded"
    character["derived"] = {
        "defense": calculate_defense(character, items_db),
        "armor": calculate_armor(character, items_db),
        "attack_rating_mainhand": calculate_attack_rating(character, "weapon", items_db),
        "attack_rating_offhand": calculate_attack_rating(character, "offhand", items_db),
        "initiative": calculate_initiative(character, items_db),
        "carry_limit": carry_limit,
        "carry_weight": carry_weight,
        "encumbrance_state": encumbrance_state,
        "age_modifiers": age_modifiers,
        "resistances": calculate_resistances(character, items_db),
        "combat_flags": calculate_combat_flags(character),
    }
    reconcile_canonical_resources(character)
    strip_legacy_shadow_fields(character)
    if ENABLE_LEGACY_SHADOW_WRITEBACK:
        sync_legacy_character_fields(character)


def normalize_character_state(
    character: Dict[str, Any],
    slot_name: str,
    items_db: Dict[str, Any],
    world_time: Optional[Dict[str, Any]] = None,
    world_bible: Optional[Dict[str, Any]] = None,
    setup_answers: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    base = blank_character_state(slot_name)
    merged = deep_copy(base)
    merged.update(
        {
            key: value
            for key, value in character.items()
            if key
            not in (
                "bio",
                "resources",
                "attributes",
                "derived",
                "skills",
                "abilities",
                "inventory",
                "equipment",
                "progression",
                "journal",
                "appearance",
                "class_state",
                "class_current",
                "aging",
                "modifiers",
                "injuries",
                "scars",
                "hp",
                "stamina",
                "equip",
                "potential",
            )
        }
    )
    merged["bio"].update(character.get("bio", {}) or {})
    legacy_role_text = str((merged.get("bio") or {}).get("party_role", "") or "")
    merged["bio"].pop("party_role", None)
    merged["appearance"] = normalize_appearance_state({**merged, "appearance": character.get("appearance", {}) or {}})
    merged["appearance_history"] = [deep_copy(entry) for entry in (character.get("appearance_history") or []) if isinstance(entry, dict)]
    merged["class_current"] = normalize_class_current(character.get("class_current"))
    if not merged["class_current"]:
        legacy_class = character.get("class_state") or {}
        if isinstance(legacy_class, dict) and (legacy_class.get("class_id") or legacy_class.get("class_name")):
            merged["class_current"] = normalize_class_current(
                {
                    "id": legacy_class.get("class_id"),
                    "name": legacy_class.get("class_name"),
                    "rank": "F",
                    "level": 1,
                    "level_max": 10,
                    "affinity_tags": [],
                    "description": "",
                    "ascension": {"status": "none", "quest_id": None, "requirements": [], "result_hint": None},
                }
            )
    if not merged["class_current"]:
        merged["class_current"] = migrate_legacy_role_to_class(legacy_role_text)
    merged["faction_memberships"] = [deep_copy(entry) for entry in (character.get("faction_memberships") or []) if isinstance(entry, dict)]
    merged["aging"].update(character.get("aging", {}) or {})
    merged["modifiers"].update(character.get("modifiers", {}) or {})
    ensure_character_modifier_shape(merged)

    raw_legacy_resources = character.get("resources", {}) if isinstance(character.get("resources"), dict) else {}
    merged["resources"] = {
        key: deep_copy(value)
        for key, value in raw_legacy_resources.items()
        if key in {"stress", "corruption", "wounds"} and isinstance(value, dict)
    }

    merged["attributes"].update(character.get("attributes", {}) or {})
    merged["element_affinities"] = [str(value).strip() for value in (character.get("element_affinities") or []) if str(value).strip()][:8]
    merged["element_resistances"] = [str(value).strip() for value in (character.get("element_resistances") or []) if str(value).strip()][:8]
    merged["element_weaknesses"] = [str(value).strip() for value in (character.get("element_weaknesses") or []) if str(value).strip()][:8]
    raw_skills = character.get("skills", {}) or {}
    if looks_like_legacy_seeded_skills(raw_skills):
        raw_skills = {}
    merged["progression"].update(character.get("progression", {}) or {})
    ensure_progression_shape(merged)
    merged["level"] = max(
        1,
        int(
            character.get("level")
            or merged["progression"].get("character_level")
            or merged["progression"].get("system_level")
            or merged["progression"].get("rank")
            or merged.get("level", 1)
            or 1
        ),
    )
    merged["xp_current"] = max(0, int(character.get("xp_current", merged.get("xp_current", 0)) or 0))
    merged["xp_total"] = max(merged["xp_current"], int(character.get("xp_total", merged.get("xp_total", merged["xp_current"])) or merged["xp_current"]))
    merged["xp_to_next"] = max(
        1,
        int(character.get("xp_to_next", merged.get("xp_to_next", next_character_xp_for_level(merged["level"]))) or next_character_xp_for_level(merged["level"])),
    )
    merged["recent_progression_events"] = [deep_copy(entry) for entry in (character.get("recent_progression_events") or []) if isinstance(entry, dict)]
    ensure_character_progression_core(merged)
    merged["skills"] = extract_skill_entries_for_character({**character, "skills": raw_skills, "slot_id": slot_name, "progression": merged["progression"]})
    if ENABLE_LEGACY_SHADOW_WRITEBACK:
        merged["abilities"] = []
    else:
        merged.pop("abilities", None)
    merged["equipment"].update(character.get("equipment", {}) or {})
    merged["journal"].update(character.get("journal", {}) or {})

    inventory = character.get("inventory", {})
    if isinstance(inventory, list):
        merged["inventory"]["items"] = [{"item_id": str(item_id), "stack": 1} for item_id in inventory if item_id]
    elif isinstance(inventory, dict):
        merged["inventory"].update(inventory)
    if character.get("equip"):
        merged["equipment"]["weapon"] = character["equip"].get("weapon", merged["equipment"]["weapon"])
        merged["equipment"]["chest"] = character["equip"].get("armor", merged["equipment"]["chest"])
        merged["equipment"]["trinket"] = character["equip"].get("trinket", merged["equipment"]["trinket"])

    if character.get("potential"):
        merged["progression"]["potential_cards"] = [
            {"id": make_id("potential"), "name": str(name), "description": "", "tags": [], "requirements": [], "status": "locked"}
            for name in character.get("potential", []) if str(name).strip()
        ]

    merged["injuries"] = [entry for entry in (normalize_injury_state(raw) for raw in (character.get("injuries") or [])) if entry]
    scars_raw = character.get("scars") or []
    if not scars_raw and isinstance((merged.get("appearance") or {}).get("scars"), list):
        scars_raw = [
            {
                "id": entry.get("id") or make_id("scar"),
                "title": entry.get("label"),
                "origin_injury_id": None,
                "description": entry.get("source") or entry.get("label"),
                "created_turn": entry.get("turn_number", 0),
            }
            for entry in ((merged.get("appearance") or {}).get("scars") or [])
            if isinstance(entry, dict)
        ]
    merged["scars"] = [entry for entry in (normalize_scar_state(raw) for raw in scars_raw) if entry]
    merged["skills"] = normalize_skill_store(merged.get("skills") or {}, resource_name=resource_name_for_character(merged))
    migrate_effects_from_conditions(merged)
    ingest_legacy_resources_into_canonical(merged, source_character=character)
    reconcile_canonical_resources(merged)
    resolve_injury_healing(merged, int(((character.get("meta") or {}).get("turn", 0)) or 0))
    rebuild_character_derived(merged, items_db, world_time)
    ingest_legacy_resources_into_canonical(merged, source_character=character)
    reconcile_canonical_resources(merged)
    strip_legacy_shadow_fields(merged)
    if ENABLE_LEGACY_SHADOW_WRITEBACK:
        write_legacy_shadow_fields(merged)
    sync_scars_into_appearance(merged)
    merged["living_profile"] = normalize_living_profile(
        character.get("living_profile"),
        character=merged,
        world_bible=world_bible,
        setup_answers=setup_answers,
    )
    return merged


def rebuild_all_character_derived(campaign: Dict[str, Any]) -> None:
    state = campaign.get("state", {})
    items_db = state.get("items", {}) or {}
    world_time = normalize_world_time(state.get("meta", {}))
    for slot_name, character in (state.get("characters") or {}).items():
        state["characters"][slot_name] = normalize_character_state(character, slot_name, items_db, world_time)
