"""Runtime wiring for world element / species / race / beast generation.

This module owns the dependency-injection glue that previously lived in the
state runtime core: it imports the pure element/species primitives and wires
their keyword-only ports locally. The few LLM-backed entry points
(``generate_world_elements_with_llm`` and its callers) intentionally remain in
the state runtime core so existing monkeypatch-based check scripts keep working.
"""
import random
from typing import Any, Dict, List, Optional, Set, Tuple

from app.config.elements import (
    ELEMENT_CLASS_PATH_MAX,
    ELEMENT_CLASS_PATH_MIN,
    ELEMENT_CLASS_PATH_RANKS,
    ELEMENT_GENERATED_NAMES_FALLBACK,
    ELEMENT_RELATIONS,
    ELEMENT_SIMILARITY_BLACKLIST,
)
from app.core.ids import deep_copy, make_id
from app.services.progression.skills import normalize_skill_rank, skill_rank_sort_value
from app.services.world.codex import (
    build_entity_alias_variants,
    normalize_codex_alias_text,
    world_codex_sort_key,
)
from app.services.world.collections import stable_sorted_mapping
from app.services.world.element_class_paths import (
    generate_element_class_paths as _generate_element_class_paths,
    next_element_path_name as _next_element_path_name,
    normalize_class_path_rank_node as _normalize_class_path_rank_node,
    normalize_element_class_paths as _normalize_element_class_paths,
    resolve_class_element_id as _resolve_class_element_id,
    resolve_class_path_rank_node as _resolve_class_path_rank_node,
)
from app.services.world.element_generation import (
    candidate_from_fallback_element as _candidate_from_fallback_element,
    generate_world_elements_fallback as _generate_world_elements_fallback,
    generated_element_too_similar as _generated_element_too_similar,
    theme_flavor as _theme_flavor,
    theme_flavor_options as _theme_flavor_options,
)
from app.services.world.element_ids import (
    normalize_element_id_list as _normalize_element_id_list,
)
from app.services.world.element_profiles import (
    default_element_profile as _default_element_profile,
    element_id_from_name as _element_id_from_name,
    normalize_element_profile as _normalize_element_profile,
)
from app.services.world.element_relations import (
    apply_element_anchor_relation_rules as _apply_element_anchor_relation_rules,
    build_default_element_relations as _build_default_element_relations,
    build_element_alias_index as _build_element_alias_index,
    element_pair_rule_ids as _element_pair_rule_ids,
    element_sort_key as _element_sort_key,
    generate_element_relations as _generate_element_relations,
    get_element_relation as _get_element_relation,
    normalize_element_relation as _normalize_element_relation,
    normalize_element_relations as _normalize_element_relations,
    relation_sort_value as _relation_sort_value,
    resolve_element_relation as _resolve_element_relation,
    set_element_relation as _set_element_relation_impl,
)
from app.services.world.element_skills import (
    normalize_skill_elements_for_world as _normalize_skill_elements_for_world,
)
from app.services.world.math_utils import clamp
from app.services.world.naming import (
    generate_unique_fantasy_name as _generate_unique_fantasy_name,
    generate_world_name as _generate_world_name,
    pick_world_theme_anchor as _pick_world_theme_anchor,
)
from app.services.world.progression import normalize_class_current
from app.services.world.species_generation import (
    generate_world_beast_profiles as _generate_world_beast_profiles,
    generate_world_race_profiles as _generate_world_race_profiles,
)
from app.services.world.species_profiles import (
    beast_id_from_name as _beast_id_from_name,
    default_beast_profile as _default_beast_profile,
    default_race_profile as _default_race_profile,
    normalize_beast_profile as _normalize_beast_profile,
    normalize_race_profile as _normalize_race_profile,
    race_id_from_name as _race_id_from_name,
)

def race_id_from_name(name: str) -> str:
    return _race_id_from_name(
        name,
        normalize_codex_alias_text=normalize_codex_alias_text,
        make_id=make_id,
    )

def beast_id_from_name(name: str) -> str:
    return _beast_id_from_name(
        name,
        normalize_codex_alias_text=normalize_codex_alias_text,
        make_id=make_id,
    )

def default_race_profile(race_id: str, name: str) -> Dict[str, Any]:
    return _default_race_profile(str(race_id or race_id_from_name(name)).strip(), name)

def default_beast_profile(beast_id: str, name: str) -> Dict[str, Any]:
    return _default_beast_profile(str(beast_id or beast_id_from_name(name)).strip(), name)

def normalize_race_profile(raw: Any, *, fallback_id: str = "") -> Optional[Dict[str, Any]]:
    return _normalize_race_profile(
        raw,
        fallback_id=fallback_id,
        race_id_from_name=race_id_from_name,
        default_race_profile=default_race_profile,
    )

def normalize_beast_profile(raw: Any, *, fallback_id: str = "") -> Optional[Dict[str, Any]]:
    return _normalize_beast_profile(
        raw,
        fallback_id=fallback_id,
        beast_id_from_name=beast_id_from_name,
        default_beast_profile=default_beast_profile,
        clamp=clamp,
    )

def element_id_from_name(name: str) -> str:
    return _element_id_from_name(
        name,
        normalize_codex_alias_text=normalize_codex_alias_text,
        make_id=make_id,
    )

def default_element_profile(element_id: str, name: str, *, origin: str = "generated") -> Dict[str, Any]:
    return _default_element_profile(str(element_id or element_id_from_name(name)).strip(), name, origin=origin)

def normalize_element_profile(raw: Any, *, fallback_id: str = "", fallback_origin: str = "generated") -> Optional[Dict[str, Any]]:
    return _normalize_element_profile(
        raw,
        fallback_id=fallback_id,
        fallback_origin=fallback_origin,
        element_id_from_name=element_id_from_name,
        default_element_profile=default_element_profile,
    )

def element_sort_key(entry: Tuple[str, Dict[str, Any]]) -> Tuple[str, str]:
    return _element_sort_key(entry, normalize_codex_alias_text=normalize_codex_alias_text)

def relation_sort_value(value: str) -> int:
    return _relation_sort_value(value)

def normalize_element_relation(value: Any) -> str:
    return _normalize_element_relation(value, element_relations=set(ELEMENT_RELATIONS))

def build_element_alias_index(elements: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
    return _build_element_alias_index(
        elements,
        build_entity_alias_variants=build_entity_alias_variants,
        normalize_codex_alias_text=normalize_codex_alias_text,
        stable_sorted_mapping=stable_sorted_mapping,
    )

def build_default_element_relations(elements: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    return _build_default_element_relations(elements)

def _set_element_relation(relations: Dict[str, Dict[str, str]], source_id: str, target_id: str, relation: str) -> None:
    _set_element_relation_impl(
        relations,
        source_id,
        target_id,
        relation,
        normalize_element_relation=normalize_element_relation,
    )

def element_pair_rule_ids(elements: Dict[str, Dict[str, Any]], name_a: str, name_b: str) -> Tuple[str, str]:
    return _element_pair_rule_ids(
        elements,
        name_a,
        name_b,
        normalize_codex_alias_text=normalize_codex_alias_text,
    )

def apply_element_anchor_relation_rules(elements: Dict[str, Dict[str, Any]], relations: Dict[str, Dict[str, str]]) -> None:
    _apply_element_anchor_relation_rules(
        elements,
        relations,
        element_pair_rule_ids=element_pair_rule_ids,
        set_element_relation=_set_element_relation,
    )

def normalize_element_relations(
    relations: Any,
    elements: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, str]]:
    return _normalize_element_relations(
        relations,
        elements,
        build_default_element_relations=build_default_element_relations,
        normalize_element_relation=normalize_element_relation,
        stable_sorted_mapping=stable_sorted_mapping,
    )

def generated_element_too_similar(candidate: Dict[str, Any], existing: List[Dict[str, Any]]) -> Tuple[bool, str]:
    return _generated_element_too_similar(
        candidate,
        existing,
        normalize_codex_alias_text=normalize_codex_alias_text,
        element_similarity_blacklist=ELEMENT_SIMILARITY_BLACKLIST,
    )

def _theme_flavor_options(anchor: str) -> List[Tuple[str, str, List[str], List[str]]]:
    return _theme_flavor_options(anchor)

def _theme_flavor(seed: random.Random, anchor: str) -> Tuple[str, str, List[str], List[str]]:
    return _theme_flavor(seed, anchor)

def _candidate_from_fallback_element(
    raw_name: str,
    short: str,
    theme: str,
    status_tags: List[str],
    weak_tags: List[str],
    anchor: str,
) -> Dict[str, Any]:
    return _candidate_from_fallback_element(raw_name, short, theme, status_tags, weak_tags, anchor)

def generate_world_elements_fallback(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    return _generate_world_elements_fallback(
        summary,
        deep_copy=deep_copy,
        element_generated_names_fallback=ELEMENT_GENERATED_NAMES_FALLBACK,
        pick_world_theme_anchor=pick_world_theme_anchor,
        generated_element_too_similar=generated_element_too_similar,
    )

def generate_element_relations(elements: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    return _generate_element_relations(
        elements,
        build_default_element_relations=build_default_element_relations,
        apply_element_anchor_relation_rules=apply_element_anchor_relation_rules,
        normalize_codex_alias_text=normalize_codex_alias_text,
        set_element_relation=_set_element_relation,
        normalize_element_relations=normalize_element_relations,
    )

def next_element_path_name(element_name: str, rank: str, path_seed: int) -> str:
    return _next_element_path_name(element_name, rank, path_seed)

def generate_element_class_paths(elements: Dict[str, Dict[str, Any]], summary: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    return _generate_element_class_paths(
        elements,
        summary,
        clamp=clamp,
        element_class_path_min=ELEMENT_CLASS_PATH_MIN,
        element_class_path_max=ELEMENT_CLASS_PATH_MAX,
        element_class_path_ranks=ELEMENT_CLASS_PATH_RANKS,
        normalize_codex_alias_text=normalize_codex_alias_text,
        skill_rank_sort_value=skill_rank_sort_value,
        next_element_path_name=next_element_path_name,
        stable_sorted_mapping=stable_sorted_mapping,
    )

def normalize_class_path_rank_node(raw_node: Any, *, default_rank: str, element_id: str, path_id: str) -> Optional[Dict[str, Any]]:
    return _normalize_class_path_rank_node(
        raw_node,
        default_rank=default_rank,
        element_id=element_id,
        path_id=path_id,
        normalize_skill_rank=normalize_skill_rank,
    )

def normalize_element_class_paths(
    raw_paths: Any,
    elements: Dict[str, Dict[str, Any]],
    summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    return _normalize_element_class_paths(
        raw_paths,
        elements,
        summary,
        generate_element_class_paths=generate_element_class_paths,
        element_class_path_max=ELEMENT_CLASS_PATH_MAX,
        element_class_path_ranks=ELEMENT_CLASS_PATH_RANKS,
        normalize_skill_rank=normalize_skill_rank,
        deep_copy=deep_copy,
        stable_sorted_mapping=stable_sorted_mapping,
    )

def resolve_element_relation(world: Dict[str, Any], source_element_id: str, target_element_id: str) -> str:
    return _resolve_element_relation(
        world,
        source_element_id,
        target_element_id,
        normalize_element_relation=normalize_element_relation,
    )

def get_element_relation(world: Dict[str, Any], source_element_id: str, target_element_id: str) -> str:
    return _get_element_relation(
        world,
        source_element_id,
        target_element_id,
        normalize_element_relation=normalize_element_relation,
    )

def normalize_element_id_list(values: Any, world: Optional[Dict[str, Any]] = None) -> List[str]:
    return _normalize_element_id_list(
        values,
        world,
        normalize_codex_alias_text=normalize_codex_alias_text,
        element_id_from_name=element_id_from_name,
    )

def normalize_skill_elements_for_world(skill: Dict[str, Any], world: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return _normalize_skill_elements_for_world(
        skill,
        world,
        deep_copy=deep_copy,
        normalize_element_id_list=normalize_element_id_list,
    )

def resolve_class_element_id(current_class: Optional[Dict[str, Any]], world: Dict[str, Any]) -> Optional[str]:
    return _resolve_class_element_id(
        current_class,
        world,
        normalize_class_current=normalize_class_current,
        normalize_element_id_list=normalize_element_id_list,
    )

def resolve_class_path_rank_node(world: Dict[str, Any], current_class: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return _resolve_class_path_rank_node(
        world,
        current_class,
        normalize_class_current=normalize_class_current,
        resolve_class_element_id=resolve_class_element_id,
        normalize_skill_rank=normalize_skill_rank,
        deep_copy=deep_copy,
    )

def pick_world_theme_anchor(summary: Dict[str, Any]) -> str:
    return _pick_world_theme_anchor(summary, normalize_codex_alias_text=normalize_codex_alias_text)

def generate_unique_fantasy_name(
    rng: random.Random,
    used: Set[str],
    *,
    anchor: str,
    suffixes: List[str],
    max_attempts: int = 40,
) -> str:
    return _generate_unique_fantasy_name(
        rng,
        used,
        anchor=anchor,
        suffixes=suffixes,
        normalize_codex_alias_text=normalize_codex_alias_text,
        max_attempts=max_attempts,
    )

def generate_world_name(summary: Dict[str, Any], seed_hint: str) -> str:
    return _generate_world_name(summary, seed_hint, normalize_codex_alias_text=normalize_codex_alias_text)

def generate_world_race_profiles(summary: Dict[str, Any], *, seed_hint: str = "") -> Dict[str, Dict[str, Any]]:
    return _generate_world_race_profiles(
        summary,
        seed_hint=seed_hint,
        normalize_codex_alias_text=normalize_codex_alias_text,
        clamp=clamp,
        race_id_from_name=race_id_from_name,
        normalize_race_profile=normalize_race_profile,
        default_race_profile=default_race_profile,
        stable_sorted_mapping=stable_sorted_mapping,
        world_codex_sort_key=world_codex_sort_key,
    )

def generate_world_beast_profiles(summary: Dict[str, Any], *, seed_hint: str = "") -> Dict[str, Dict[str, Any]]:
    return _generate_world_beast_profiles(
        summary,
        seed_hint=seed_hint,
        normalize_codex_alias_text=normalize_codex_alias_text,
        clamp=clamp,
        beast_id_from_name=beast_id_from_name,
        normalize_beast_profile=normalize_beast_profile,
        default_beast_profile=default_beast_profile,
        stable_sorted_mapping=stable_sorted_mapping,
        world_codex_sort_key=world_codex_sort_key,
    )
