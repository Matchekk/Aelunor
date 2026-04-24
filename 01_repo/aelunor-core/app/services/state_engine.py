import hashlib
import json
import math
import os
import random
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import requests
from fastapi import HTTPException
from app.helpers import setup_helpers

_CONFIGURED = False

def configure(main_globals: Dict[str, Any]) -> None:
    """Inject main-module globals needed by extracted state-engine helpers."""
    global _CONFIGURED
    globals().update(main_globals)
    _CONFIGURED = True

EXPORTED_SYMBOLS = [
    "make_join_code",
    "slot_id",
    "slot_index",
    "is_slot_id",
    "ordered_slots",
    "blank_patch",
    "npc_id_from_name",
    "normalize_npc_alias",
    "normalize_codex_alias_text",
    "strip_name_parenthetical",
    "strip_codex_name_prefix",
    "safe_last_token_variants",
    "build_entity_alias_variants",
    "race_id_from_name",
    "beast_id_from_name",
    "default_race_profile",
    "default_beast_profile",
    "normalize_race_profile",
    "normalize_beast_profile",
    "element_id_from_name",
    "default_element_profile",
    "normalize_element_profile",
    "element_sort_key",
    "relation_sort_value",
    "normalize_element_relation",
    "build_element_alias_index",
    "build_default_element_relations",
    "_set_element_relation",
    "element_pair_rule_ids",
    "apply_element_anchor_relation_rules",
    "normalize_element_relations",
    "generated_element_too_similar",
    "_theme_flavor",
    "generate_world_elements_fallback",
    "generate_world_elements_with_llm",
    "generate_world_element_profiles",
    "generate_element_relations",
    "next_element_path_name",
    "generate_element_class_paths",
    "normalize_class_path_rank_node",
    "normalize_element_class_paths",
    "ensure_world_element_system_from_setup",
    "resolve_element_relation",
    "get_element_relation",
    "normalize_element_id_list",
    "normalize_skill_elements_for_world",
    "resolve_class_element_id",
    "resolve_class_path_rank_node",
    "stable_sorted_mapping",
    "codex_block_order",
    "codex_blocks_for_level",
    "merge_known_facts_stable",
    "stable_sorted_unique_strings",
    "default_race_codex_entry",
    "default_beast_codex_entry",
    "normalize_codex_entry_stable",
    "race_profile_block_facts",
    "beast_profile_block_facts",
    "codex_facts_for_blocks",
    "build_world_alias_indexes",
    "build_world_exact_name_index",
    "resolve_codex_entity_ids",
    "world_codex_sort_key",
    "normalize_world_codex_structures",
    "pick_world_theme_anchor",
    "codex_seed_for_state",
    "fantasy_syllables_for_anchor",
    "generate_unique_fantasy_name",
    "generate_world_name",
    "generate_world_race_profiles",
    "generate_world_beast_profiles",
    "ensure_world_codex_from_setup",
    "default_npc_entry",
    "normalize_npc_entry",
    "normalize_npc_codex_state",
    "seed_npc_codex_from_story_cards",
    "default_world_time",
    "default_intro_state",
    "default_appearance_profile",
    "default_character_modifiers",
    "default_class_current",
    "default_injury_state",
    "default_scar_state",
    "blank_character_state",
    "skill_rank_for_level",
    "next_skill_xp_for_level",
    "next_character_xp_for_level",
    "next_class_xp_for_level",
    "default_skill_state",
    "normalize_skill_state",
    "ability_id_from_name",
    "next_ability_xp_for_level",
    "default_ability_state",
    "normalize_ability_state",
    "normalize_resource_name",
    "resource_name_for_character",
    "skill_id_from_name",
    "display_skill_name_from_id",
    "clean_extracted_skill_name",
    "split_extracted_skill_names",
    "infer_skill_name_from_description",
    "normalize_skill_store",
    "dynamic_skill_default",
    "normalize_skill_rank",
    "normalize_dynamic_skill_state",
    "merge_dynamic_skill",
    "skill_rank_sort_value",
    "extract_skill_entries_for_character",
    "build_skill_fusion_hints",
    "skill_display_name",
    "skill_level_value",
    "role_key",
    "class_rank_sort_value",
    "normalize_class_current",
    "normalize_injury_state",
    "normalize_scar_state",
    "migrate_legacy_role_to_class",
    "class_affinity_match",
    "sentence_mentions_actor_name",
    "effective_skill_progress_multiplier",
    "setup_question_is_applicable",
    "canonical_resource_field_name",
    "ingest_legacy_resources_into_canonical",
    "reconcile_canonical_resources",
    "build_compat_resources_view",
    "strip_legacy_resource_shadows",
    "strip_legacy_shadow_fields",
    "legacy_misc_resources_set_from_payload",
    "legacy_misc_resource_deltas_from_update",
    "write_legacy_shadow_fields",
    "sync_canonical_resources",
    "sync_scars_into_appearance",
    "resolve_injury_healing",
    "looks_like_legacy_seeded_skills",
    "default_boards",
    "resource_delta_payload",
    "canonical_resources_set_from_payload",
    "canonical_resource_deltas_from_update",
    "clamp",
    "normalize_world_time",
    "infer_age_years",
    "derive_age_stage",
    "normalize_appearance_state",
    "normalize_age_fields",
    "age_character_if_needed",
    "build_age_modifiers",
    "item_weight",
    "item_modifier_value",
    "ensure_character_modifier_shape",
    "modifier_resource_key",
    "calculate_base_resource_maxima",
    "calculate_bonus_resource_maxima",
    "migrate_legacy_resource_bonus_modifiers",
    "rebuild_resource_maxima",
    "item_by_id",
    "list_inventory_items",
    "iter_equipped_item_ids",
    "ensure_item_shape",
    "normalize_equipment_slot_key",
    "normalize_equipment_update_payload",
    "infer_item_slot_from_definition",
    "item_matches_equipment_slot",
    "sync_legacy_character_fields",
    "calculate_carry_limit",
    "calculate_carry_weight",
    "calculate_resistances",
    "calculate_derived_bonus",
    "calculate_skill_modifier_bonus",
    "build_stat_based_appearance",
    "corruption_bucket",
    "build_corruption_visuals",
    "build_faction_visuals",
    "build_class_visuals",
    "build_appearance_summary_short",
    "build_appearance_summary_full",
    "rebuild_character_appearance",
    "appearance_event_id",
    "format_appearance_message",
    "record_appearance_change",
    "sync_appearance_changes",
    "append_character_change_events",
    "calculate_armor",
    "calculate_defense",
    "calculate_initiative",
    "calculate_attack_rating",
    "calculate_combat_flags",
    "skill_effective_bonus",
    "ensure_progression_shape",
    "ensure_character_progression_core",
    "progression_speed_multiplier",
    "normalize_progression_event_severity",
    "normalize_progression_event",
    "is_skill_manifestation_name_plausible",
    "canonicalize_manifested_skill_payload",
    "append_recent_progression_event",
    "resolve_skill_id_for_event",
    "apply_system_xp",
    "apply_class_xp",
    "build_elemental_core_skill_payload",
    "ensure_class_rank_core_skills",
    "refresh_skill_progression",
    "grant_skill_xp",
    "parse_skill_event",
    "normalize_progression_event_list",
    "progression_event_priority",
    "_event_origin",
    "reduce_progression_event_density",
    "patch_has_explicit_skill_progression_for_actor",
    "normalize_progression_claim_type",
    "progression_claim_text_for_actor",
    "detect_progression_claim_types",
    "progression_claim_coverage_for_actor_patch",
    "normalized_progression_claims",
    "progression_missing_claim_types",
    "normalize_progression_extractor_character_patch",
    "progression_event_dedupe_key",
    "merge_progression_patch_additive",
    "evaluate_progression_extractor_confidence",
    "call_progression_canon_extractor",
    "run_canon_gate",
    "manifestation_seed_from_skill",
    "upsert_class_path_seed",
    "infer_manifested_skill_name_with_llm",
    "infer_manifestation_progression_events_from_story",
    "infer_progression_events_from_patch",
    "apply_progression_event_xp",
    "manifest_skill_from_progression_event",
    "apply_progression_events",
    "build_skill_system_requests",
    "apply_skill_events",
    "rebuild_character_derived",
    "migrate_effects_from_conditions",
    "normalize_character_state",
    "rebuild_all_character_derived",
    "derive_scene_name",
    "build_world_question_queue",
    "build_character_question_queue",
    "default_setup",
    "normalize_answer_summary_defaults",
    "default_campaign_length_settings",
    "default_meta_timing",
    "clamp_float",
    "default_combat_meta",
    "default_attribute_influence_meta",
    "default_extraction_quarantine",
    "normalize_extraction_quarantine_meta",
    "normalize_meta_migrations",
    "normalize_world_settings",
    "normalize_meta_timing",
    "normalize_combat_meta",
    "normalize_attribute_influence_meta",
    "active_pacing_profile",
    "compute_turn_budget_estimates",
    "update_turn_timing_ema",
    "milestone_state_for_turn",
    "build_pacing_instruction_block",
    "_hash_unit_interval",
    "derive_attribute_relevance",
    "compute_attribute_bias",
    "compose_attribute_prompt_hints",
    "apply_attribute_bias_to_resolution",
    "_scale_negative_delta",
    "apply_attribute_bias_to_patch",
    "infer_skill_cost_deltas_from_text",
    "apply_skill_cost_deltas_to_patch",
    "skill_rank_power_weight",
    "entity_element_profile_for_character",
    "entity_element_profile_for_npc",
    "element_matchup_multiplier",
    "compute_character_combat_score",
    "compute_npc_combat_score",
    "build_combat_scaling_context",
    "apply_combat_scaling_to_patch",
    "infer_combat_context",
    "patch_has_combat_signal",
    "update_combat_meta_after_turn",
    "normalize_ruleset_choice",
    "normalize_campaign_length_choice",
    "parse_attribute_range",
    "world_attribute_scale",
    "level_one_attribute_budget",
    "level_one_attribute_cap",
    "normalize_attribute_weight_pool",
    "allocate_weighted_attributes",
    "fallback_character_attribute_weights",
    "generate_character_attribute_weights",
    "level_one_attributes_from_weights",
    "default_character_setup_node",
    "save_json",
    "load_json",
    "campaign_path",
    "list_campaign_ids",
    "extract_text_answer",
    "parse_lines",
    "split_creator_item_blocks",
    "summarize_creator_item_name",
    "parse_earth_items",
    "parse_factions",
    "legacy_select_answer_payload",
    "load_setup_catalog",
    "build_rules_profile",
    "attribute_cap_for_campaign",
    "campaign_slots",
    "player_claim",
    "display_name_for_slot",
    "active_party",
    "expected_setup_slots",
    "setup_slot_statuses",
    "public_player",
    "default_player_diary_entry",
    "available_slots",
    "compact_conditions",
    "build_party_overview",
    "build_character_sheet_view",
    "build_npc_sheet_view",
    "current_question_id",
    "answered_count",
    "progress_payload",
    "setup_chapter_config",
    "setup_question_chapter_key",
    "setup_chapter_progress",
    "setup_global_progress",
    "setup_phase_display",
    "setup_summary_preview",
    "ollama_request_seed",
    "call_ollama_text",
    "ollama_format_fallback_needed",
    "is_turn_response_schema",
    "schema_fallback_instruction",
    "strip_json_fences",
    "first_balanced_json_object",
    "extract_json_payload",
    "repair_truncated_json_object",
    "normalize_plotpoint_entry",
    "normalize_plotpoint_update_entry",
    "normalize_event_entry",
    "repair_json_payload_with_model",
    "normalize_patch_payload",
    "normalize_patch_semantics",
    "merge_character_patch_update",
    "merge_patch_payloads",
    "canonical_scene_id",
    "clean_scene_name",
    "is_plausible_scene_name",
    "is_generic_scene_identifier",
    "extract_scene_candidates",
    "extract_descriptive_scene_name",
    "build_scene_patch_from_text",
    "infer_scene_name_from_recent_story",
    "reconcile_scene_ids_with_story",
    "infer_injury_severity",
    "infer_injury_effects",
    "clean_auto_injury_title",
    "extract_auto_story_injuries",
    "sorted_npc_codex_entries",
    "build_npc_codex_summary",
    "sorted_world_profiles",
    "build_race_codex_summary",
    "build_beast_codex_summary",
    "build_world_element_summary",
    "build_extractor_context_packet",
    "normalize_extractor_output_patch",
    "resolve_extractor_conflicts",
    "make_extraction_candidate",
    "candidate_status_rank",
    "item_name_in_character_inventory",
    "extract_environment_item_mentions",
    "build_heuristic_candidates",
    "classify_heuristic_candidate",
    "split_candidates",
    "append_extraction_quarantine",
    "safe_candidates_to_patch",
    "merge_safe_patch_additive",
    "call_canon_extractor",
    "scene_name_from_state",
    "existing_pc_aliases",
    "is_generic_npc_name",
    "resolve_npc_scene_hint",
    "best_matching_npc_id",
    "npc_relevance_score",
    "pick_more_specific_text",
    "apply_npc_upserts",
    "contains_any_normalized_token",
    "collect_beast_observed_abilities",
    "collect_codex_triggers",
    "apply_codex_triggers",
    "build_npc_extractor_context_packet",
    "call_npc_extractor",
    "normalize_request_option_text",
    "normalize_request_entry",
    "normalize_requests_payload",
    "normalize_model_output_payload",
    "call_ollama_chat",
    "call_ollama_json",
    "call_ollama_schema",
    "clean_setup_ai_copy",
    "is_bad_setup_ai_copy",
    "generate_setup_ai_copy",
    "get_persisted_question_ai_copy",
    "store_question_ai_copy",
    "ensure_question_ai_copy",
    "build_setup_option_context",
    "append_context_hint",
    "dynamic_option_description",
    "dynamic_other_hint",
    "build_dynamic_option_entries",
    "build_question_payload",
    "setup_helper_dependencies",
    "validate_answer_payload",
    "fallback_random_text",
    "fallback_random_answer_payload",
    "generate_random_setup_answer",
    "store_setup_answer",
    "setup_answer_to_input_payload",
    "setup_answer_preview_text",
    "build_random_setup_preview",
    "apply_random_setup_preview",
    "finalize_world_setup",
    "finalize_character_setup",
    "build_world_summary",
    "build_character_summary",
    "apply_world_summary_to_boards",
    "initialize_dynamic_slots",
    "apply_character_summary_to_state",
    "is_legacy_campaign",
    "remap_turn_context_slot_names",
    "migrate_campaign_to_dynamic_slots",
    "normalize_campaign",
    "load_campaign",
    "save_campaign",
    "active_turns",
    "is_host",
    "is_campaign_player",
    "build_patch_summary",
    "is_continue_story_content",
    "public_turn",
    "build_world_question_state",
    "build_character_question_state",
    "build_viewer_context",
    "build_setup_runtime",
    "filter_private_diary_content",
    "build_public_boards",
    "build_campaign_view",
    "remember_recent_story",
    "heuristic_memory_summary",
    "rebuild_memory_summary",
    "build_context_packet",
    "is_suspicious_story_text",
    "normalized_eval_text",
    "context_state_signature",
    "strip_markdown_like",
    "parse_context_intent",
    "build_context_knowledge_index",
    "resolve_context_target",
    "build_context_result_payload",
    "deterministic_context_result_from_entry",
    "context_meta_drift_detected",
    "build_reduced_context_snippets",
    "build_context_result_via_llm",
    "extract_story_target_evidence",
    "context_result_to_answer_text",
    "clean_auto_ability_name",
    "clean_auto_item_name",
    "actor_relevant_story_sentences",
    "infer_item_slot_from_text",
    "build_auto_item_stub",
    "clean_creator_item_name",
    "item_id_from_name",
    "materialize_inventory_item",
    "normalize_creator_item_list",
    "reconcile_creator_inventory_items",
    "infer_auto_skill_tags",
    "infer_auto_class_tags",
    "normalize_class_rank_text",
    "clean_auto_class_name",
    "extract_auto_class_change",
    "extract_auto_learned_abilities",
    "extract_auto_story_item_events",
    "extract_auto_story_items",
    "story_sentences_for_actor",
    "build_turn_journal_notes",
    "inject_turn_story_journal",
    "inject_story_unlock_abilities",
    "materialize_character_ability",
    "inject_story_items",
    "inject_story_injuries",
    "materialize_story_items_from_turn_history",
    "materialize_story_abilities_from_turn_history",
    "run_legacy_normalize_backfill",
    "apply_world_time_advance",
    "log_board_revision",
    "intro_state",
    "can_start_adventure",
    "try_generate_adventure_intro",
    "maybe_start_adventure",
    "new_player",
    "create_campaign_record",
    "ensure_campaign_storage",
    "find_campaign_by_join_code",
    "touch_player",
    "authenticate_player",
    "require_host",
    "require_claim",
]

def make_join_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(6))

def slot_id(index: int) -> str:
    return f"{SLOT_PREFIX}{index}"

def slot_index(value: str) -> int:
    if not value.startswith(SLOT_PREFIX):
        return 9999
    try:
        return int(value.split("_", 1)[1])
    except (IndexError, ValueError):
        return 9999

def is_slot_id(value: str) -> bool:
    return bool(re.fullmatch(r"slot_[1-9]\d*", value or ""))

def ordered_slots(keys: List[str]) -> List[str]:
    return sorted(keys, key=slot_index)

def blank_patch() -> Dict[str, Any]:
    return {
        "meta": {},
        "characters": {},
        "items_new": {},
        "plotpoints_add": [],
        "plotpoints_update": [],
        "map_add_nodes": [],
        "map_add_edges": [],
        "events_add": [],
    }

def npc_id_from_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", normalized_eval_text(name)).strip("_")
    if not slug:
        slug = make_id("npc").split("_", 1)[1]
    return f"npc_{slug[:48]}"

def normalize_npc_alias(text: str) -> str:
    alias = normalized_eval_text(text)
    alias = re.sub(r"\b(der|die|das|ein|eine|einen|einem|einer|herr|frau|sir|lady)\b", " ", alias)
    alias = re.sub(r"\s+", " ", alias).strip()
    return alias

def normalize_codex_alias_text(text: Any) -> str:
    alias = normalized_eval_text(text)
    alias = (
        alias.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    alias = re.sub(r"\b(der|die|das|ein|eine|einen|einem|einer)\b", " ", alias)
    alias = re.sub(r"[\-_]+", " ", alias)
    alias = re.sub(r"\s+", " ", alias).strip()
    return alias

def strip_name_parenthetical(name: str) -> str:
    cleaned = re.sub(r"\s*\([^)]*\)", " ", str(name or ""))
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.;:!?")
    return cleaned

def strip_codex_name_prefix(name: str) -> str:
    cleaned = str(name or "").strip()
    cleaned = re.sub(
        r"^(?:volk|stamm|orden)\s+(?:der|des)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()
    return cleaned

def safe_last_token_variants(token: str, *, max_variants: int = 6) -> List[str]:
    base = normalize_codex_alias_text(token)
    if not base or len(base) < 4:
        return [base] if base else []
    variants: List[str] = [base]
    suffixes = ("s", "e", "en", "er")
    for suffix in suffixes:
        if len(variants) >= max_variants:
            break
        if base.endswith(suffix) and len(base) - len(suffix) >= 3:
            variants.append(base[: -len(suffix)])
    for suffix in suffixes:
        if len(variants) >= max_variants:
            break
        if not base.endswith(suffix):
            variants.append(base + suffix)
    deduped: List[str] = []
    seen = set()
    for variant in variants:
        normalized = normalize_codex_alias_text(variant)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
        if len(deduped) >= max_variants:
            break
    return deduped

def build_entity_alias_variants(name: str, aliases: Optional[List[str]] = None) -> List[str]:
    raw_candidates: List[str] = []
    base = str(name or "").strip()
    if base:
        raw_candidates.append(base)
        base_without_parenthetical = strip_name_parenthetical(base)
        if base_without_parenthetical:
            raw_candidates.append(base_without_parenthetical)
            stripped_prefix = strip_codex_name_prefix(base_without_parenthetical)
            if stripped_prefix:
                raw_candidates.append(stripped_prefix)
    for alias in (aliases or []):
        alias_text = str(alias or "").strip()
        if not alias_text:
            continue
        raw_candidates.append(alias_text)
        alias_without_parenthetical = strip_name_parenthetical(alias_text)
        if alias_without_parenthetical:
            raw_candidates.append(alias_without_parenthetical)

    normalized_variants: List[str] = []
    seen = set()
    for candidate in raw_candidates:
        normalized = normalize_codex_alias_text(candidate)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        normalized_variants.append(normalized)
        tokens = normalized.split()
        if len(tokens) > 1 and len(tokens[-1]) >= 4:
            short_alias = normalize_codex_alias_text(tokens[-1])
            if short_alias and short_alias not in seen:
                seen.add(short_alias)
                normalized_variants.append(short_alias)
            for short_variant in safe_last_token_variants(tokens[-1], max_variants=4):
                if short_variant and short_variant not in seen:
                    seen.add(short_variant)
                    normalized_variants.append(short_variant)
        if not tokens or len(tokens[-1]) < 4:
            continue
        prefix = tokens[:-1]
        for token_variant in safe_last_token_variants(tokens[-1], max_variants=6):
            rebuilt = " ".join([*prefix, token_variant]).strip()
            normalized_rebuilt = normalize_codex_alias_text(rebuilt)
            if not normalized_rebuilt or normalized_rebuilt in seen:
                continue
            seen.add(normalized_rebuilt)
            normalized_variants.append(normalized_rebuilt)
    return normalized_variants

def race_id_from_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", normalize_codex_alias_text(name)).strip("_")
    if not slug:
        slug = make_id("race").split("_", 1)[1]
    return f"race_{slug[:48]}"

def beast_id_from_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", normalize_codex_alias_text(name)).strip("_")
    if not slug:
        slug = make_id("beast").split("_", 1)[1]
    return f"beast_{slug[:48]}"

def default_race_profile(race_id: str, name: str) -> Dict[str, Any]:
    return {
        "id": str(race_id or race_id_from_name(name)).strip(),
        "name": str(name or "Unbekannte Rasse").strip() or "Unbekannte Rasse",
        "kind": "volk",
        "rarity": "gewöhnlich",
        "description_short": "",
        "appearance": "",
        "homeland": "",
        "culture": "",
        "temperament": "",
        "strength_tags": [],
        "weakness_tags": [],
        "class_affinities": [],
        "skill_affinities": [],
        "social_reputation": "",
        "playable": True,
        "notable_traits": [],
        "aliases": [],
    }

def default_beast_profile(beast_id: str, name: str) -> Dict[str, Any]:
    return {
        "id": str(beast_id or beast_id_from_name(name)).strip(),
        "name": str(name or "Unbekannte Bestie").strip() or "Unbekannte Bestie",
        "category": "bestie",
        "danger_rating": 1,
        "habitat": "",
        "behavior": "",
        "appearance": "",
        "strength_tags": [],
        "weakness_tags": [],
        "combat_style": "",
        "known_abilities": [],
        "loot_tags": [],
        "lore_notes": [],
        "aliases": [],
    }

def normalize_race_profile(raw: Any, *, fallback_id: str = "") -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip()
    if not name:
        return None
    race_id = str(raw.get("id") or fallback_id or race_id_from_name(name)).strip()
    if not race_id:
        return None
    profile = default_race_profile(race_id, name)
    profile["kind"] = str(raw.get("kind") or profile["kind"]).strip() or profile["kind"]
    profile["rarity"] = str(raw.get("rarity") or profile["rarity"]).strip() or profile["rarity"]
    profile["description_short"] = str(raw.get("description_short") or "").strip()
    profile["appearance"] = str(raw.get("appearance") or "").strip()
    profile["homeland"] = str(raw.get("homeland") or "").strip()
    profile["culture"] = str(raw.get("culture") or "").strip()
    profile["temperament"] = str(raw.get("temperament") or "").strip()
    profile["social_reputation"] = str(raw.get("social_reputation") or "").strip()
    profile["playable"] = bool(raw.get("playable", True))
    for key in ("strength_tags", "weakness_tags", "class_affinities", "skill_affinities", "notable_traits", "aliases"):
        values = [str(entry).strip() for entry in (raw.get(key) or []) if str(entry).strip()]
        profile[key] = list(dict.fromkeys(values))
    return profile

def normalize_beast_profile(raw: Any, *, fallback_id: str = "") -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip()
    if not name:
        return None
    beast_id = str(raw.get("id") or fallback_id or beast_id_from_name(name)).strip()
    if not beast_id:
        return None
    profile = default_beast_profile(beast_id, name)
    profile["category"] = str(raw.get("category") or profile["category"]).strip() or profile["category"]
    profile["danger_rating"] = clamp(int(raw.get("danger_rating", 1) or 1), 1, 20)
    profile["habitat"] = str(raw.get("habitat") or "").strip()
    profile["behavior"] = str(raw.get("behavior") or "").strip()
    profile["appearance"] = str(raw.get("appearance") or "").strip()
    profile["combat_style"] = str(raw.get("combat_style") or "").strip()
    for key in ("strength_tags", "weakness_tags", "known_abilities", "loot_tags", "lore_notes", "aliases"):
        values = [str(entry).strip() for entry in (raw.get(key) or []) if str(entry).strip()]
        profile[key] = list(dict.fromkeys(values))
    return profile

def element_id_from_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", normalize_codex_alias_text(name)).strip("_")
    if not slug:
        slug = make_id("element").split("_", 1)[1]
    return f"elem_{slug[:48]}"

def default_element_profile(element_id: str, name: str, *, origin: str = "generated") -> Dict[str, Any]:
    return {
        "id": str(element_id or element_id_from_name(name)).strip(),
        "name": str(name or "Unbenanntes Element").strip() or "Unbenanntes Element",
        "rarity": "gewöhnlich",
        "description": "",
        "theme": "",
        "origin": origin if origin in {"core", "generated", "emergent"} else "generated",
        "strengths_against": [],
        "weaknesses_against": [],
        "synergies_with": [],
        "status_effect_tags": [],
        "class_affinities": [],
        "skill_affinities": [],
        "discoverable": True,
        "lore_notes": [],
        "visual_motif": "",
        "temperament": "",
        "environment_bias": "",
        "aliases": [],
    }

def normalize_element_profile(raw: Any, *, fallback_id: str = "", fallback_origin: str = "generated") -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip()
    if not name:
        return None
    element_id = str(raw.get("id") or fallback_id or element_id_from_name(name)).strip()
    if not element_id:
        return None
    profile = default_element_profile(element_id, name, origin=fallback_origin)
    profile.update({k: v for k, v in raw.items() if k in profile})
    profile["id"] = element_id
    profile["name"] = str(profile.get("name") or name).strip() or name
    profile["rarity"] = str(profile.get("rarity") or "gewöhnlich").strip() or "gewöhnlich"
    profile["description"] = str(profile.get("description") or "").strip()
    profile["theme"] = str(profile.get("theme") or "").strip()
    origin = str(profile.get("origin") or fallback_origin).strip().lower()
    profile["origin"] = origin if origin in {"core", "generated", "emergent"} else fallback_origin
    for key in (
        "strengths_against",
        "weaknesses_against",
        "synergies_with",
        "status_effect_tags",
        "class_affinities",
        "skill_affinities",
        "lore_notes",
        "aliases",
    ):
        profile[key] = list(dict.fromkeys([str(entry).strip() for entry in (profile.get(key) or []) if str(entry).strip()]))
    profile["discoverable"] = bool(profile.get("discoverable", True))
    profile["visual_motif"] = str(profile.get("visual_motif") or "").strip()
    profile["temperament"] = str(profile.get("temperament") or "").strip()
    profile["environment_bias"] = str(profile.get("environment_bias") or "").strip()
    return profile

def element_sort_key(entry: Tuple[str, Dict[str, Any]]) -> Tuple[str, str]:
    element_id, payload = entry
    return (normalize_codex_alias_text((payload or {}).get("name", "")), str(element_id))

def relation_sort_value(value: str) -> int:
    order = {"countered": 0, "weak": 1, "neutral": 2, "strong": 3, "dominant": 4}
    return order.get(str(value or "neutral").strip().lower(), 2)

def normalize_element_relation(value: Any) -> str:
    relation = str(value or "neutral").strip().lower()
    return relation if relation in ELEMENT_RELATIONS else "neutral"

def build_element_alias_index(elements: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
    index: Dict[str, List[str]] = {}
    for element_id, profile in (elements or {}).items():
        if not isinstance(profile, dict):
            continue
        variants = build_entity_alias_variants(str(profile.get("name") or element_id), profile.get("aliases") or [])
        for alias in variants:
            normalized = normalize_codex_alias_text(alias)
            if not normalized:
                continue
            index.setdefault(normalized, [])
            if element_id not in index[normalized]:
                index[normalized].append(element_id)
    for alias, ids in list(index.items()):
        index[alias] = sorted(set(ids), key=str)
    return stable_sorted_mapping(index, key_fn=lambda item: item[0])

def build_default_element_relations(elements: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    relation_map: Dict[str, Dict[str, str]] = {}
    element_ids = list((elements or {}).keys())
    for source_id in element_ids:
        relation_map[source_id] = {}
        for target_id in element_ids:
            relation_map[source_id][target_id] = "neutral"
    return relation_map

def _set_element_relation(relations: Dict[str, Dict[str, str]], source_id: str, target_id: str, relation: str) -> None:
    if source_id not in relations:
        relations[source_id] = {}
    relations[source_id][target_id] = normalize_element_relation(relation)

def element_pair_rule_ids(elements: Dict[str, Dict[str, Any]], name_a: str, name_b: str) -> Tuple[str, str]:
    wanted_a = normalize_codex_alias_text(name_a)
    wanted_b = normalize_codex_alias_text(name_b)
    found_a = ""
    found_b = ""
    for element_id, profile in (elements or {}).items():
        normalized_name = normalize_codex_alias_text((profile or {}).get("name", ""))
        if not found_a and normalized_name == wanted_a:
            found_a = element_id
        if not found_b and normalized_name == wanted_b:
            found_b = element_id
    return found_a, found_b

def apply_element_anchor_relation_rules(elements: Dict[str, Dict[str, Any]], relations: Dict[str, Dict[str, str]]) -> None:
    predefined = [
        ("Feuer", "Wasser", "weak"),
        ("Wasser", "Feuer", "strong"),
        ("Feuer", "Erde", "strong"),
        ("Erde", "Feuer", "neutral"),
        ("Luft", "Erde", "strong"),
        ("Erde", "Luft", "weak"),
        ("Licht", "Schatten", "strong"),
        ("Schatten", "Licht", "countered"),
        ("Wasser", "Erde", "weak"),
        ("Erde", "Wasser", "strong"),
        ("Luft", "Wasser", "neutral"),
        ("Wasser", "Luft", "neutral"),
    ]
    for src_name, dst_name, relation in predefined:
        src_id, dst_id = element_pair_rule_ids(elements, src_name, dst_name)
        if src_id and dst_id:
            _set_element_relation(relations, src_id, dst_id, relation)

def normalize_element_relations(
    relations: Any,
    elements: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, str]]:
    element_ids = list((elements or {}).keys())
    normalized = build_default_element_relations(elements)
    raw = relations if isinstance(relations, dict) else {}
    for source_id, target_map in raw.items():
        source = str(source_id or "").strip()
        if source not in normalized or not isinstance(target_map, dict):
            continue
        for target_id, value in target_map.items():
            target = str(target_id or "").strip()
            if target not in normalized[source]:
                continue
            normalized[source][target] = normalize_element_relation(value)
    for element_id in element_ids:
        normalized.setdefault(element_id, {})
        for target_id in element_ids:
            normalized[element_id][target_id] = normalize_element_relation(
                normalized[element_id].get(target_id, "neutral")
            )
    # deterministically set self-relations (default neutral)
    for element_id in element_ids:
        if element_id not in normalized:
            normalized[element_id] = {}
        normalized[element_id][element_id] = normalize_element_relation(
            normalized[element_id].get(element_id, "neutral")
        )
    return stable_sorted_mapping(
        {src: stable_sorted_mapping(dst_map, key_fn=lambda item: item[0]) for src, dst_map in normalized.items()},
        key_fn=lambda item: item[0],
    )

def generated_element_too_similar(candidate: Dict[str, Any], existing: List[Dict[str, Any]]) -> Tuple[bool, str]:
    name_norm = normalize_codex_alias_text(candidate.get("name", ""))
    theme_norm = normalize_codex_alias_text(candidate.get("theme", ""))
    if not name_norm:
        return True, "EMPTY_NAME"
    for core_norm, terms in ELEMENT_SIMILARITY_BLACKLIST.items():
        if name_norm == core_norm:
            return True, "TOO_SIMILAR_TO_CORE"
        if any(term in name_norm for term in terms):
            return True, "TOO_SIMILAR_TO_CORE"
        if theme_norm and any(term in theme_norm for term in terms):
            return True, "TOO_SIMILAR_TO_CORE"
    for entry in existing:
        existing_name_norm = normalize_codex_alias_text(entry.get("name", ""))
        existing_theme_norm = normalize_codex_alias_text(entry.get("theme", ""))
        if not existing_name_norm:
            continue
        if name_norm == existing_name_norm:
            return True, "DUPLICATE_NAME"
        if name_norm.startswith(existing_name_norm) or existing_name_norm.startswith(name_norm):
            return True, "DUPLICATE_THEME"
        if theme_norm and existing_theme_norm and (
            theme_norm == existing_theme_norm
            or theme_norm in existing_theme_norm
            or existing_theme_norm in theme_norm
        ):
            return True, "DUPLICATE_THEME"
    return False, ""

def _theme_flavor(seed: random.Random, anchor: str) -> Tuple[str, str, List[str], List[str]]:
    motifs = [
        ("Resonanz von Schwingungen und Klang", "resonanz", ["desorientierung", "echo"], ["ruhe", "stille"]),
        ("Nebel aus Erinnerung und Täuschung", "nebel", ["blindheit", "verwirrung"], ["wind", "fokus"]),
        ("Asche als Rest alter Flammen", "asche", ["brandspur", "erstickung"], ["wasser", "reinigung"]),
        ("Sternenstaub und kosmische Splitter", "sterne", ["strahl", "markierung"], ["schatten", "erde"]),
        ("Leere und entziehende Kälte", "leere", ["auszehrung", "druck"], ["licht", "bindung"]),
        ("Traum zwischen Hoffnung und Alb", "traum", ["schlaf", "furcht"], ["klarheit", "lärm"]),
        ("Blutpakt und Lebensrausch", "blut", ["blutung", "rausch"], ["reinheit", "frost"]),
        ("Dornenwuchs und uraltes Grün", "dornen", ["fessel", "gift"], ["feuer", "schneide"]),
        ("Donnerglas und geladene Splitter", "donnerglas", ["schock", "bruch"], ["erde", "isolierung"]),
        ("Gezeitenstahl aus flüssigem Metall", "gezeitenstahl", ["schnitt", "druck"], ["magnet", "säure"]),
    ]
    choice = seed.choice(motifs)
    theme = f"{choice[0]} ({anchor})"
    return choice[1], theme, choice[2], choice[3]

def generate_world_elements_fallback(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    seed_text = json.dumps(
        {"theme": summary.get("theme", ""), "tone": summary.get("tone", ""), "premise": summary.get("premise", "")},
        ensure_ascii=False,
        sort_keys=True,
    )
    seed = random.Random(int(hashlib.sha1(seed_text.encode("utf-8")).hexdigest(), 16) % (2**32))
    anchor = pick_world_theme_anchor(summary)
    names = deep_copy(ELEMENT_GENERATED_NAMES_FALLBACK)
    seed.shuffle(names)
    picked: List[Dict[str, Any]] = []
    for raw_name in names:
        short, theme, status_tags, weak_tags = _theme_flavor(seed, anchor)
        candidate = {
            "name": raw_name,
            "rarity": "ungewöhnlich",
            "description": f"{raw_name} prägt Konflikte dieser Welt durch {theme.lower()}.",
            "theme": theme,
            "origin": "generated",
            "strengths_against": [],
            "weaknesses_against": weak_tags[:2],
            "synergies_with": [],
            "status_effect_tags": status_tags[:2],
            "class_affinities": [short],
            "skill_affinities": [short],
            "discoverable": True,
            "lore_notes": [f"{raw_name} wird in {anchor} mit alten Ritualen verknüpft."],
            "visual_motif": short,
            "temperament": "unruhig",
            "environment_bias": anchor,
            "aliases": [],
        }
        too_similar, _reason = generated_element_too_similar(candidate, picked)
        if too_similar:
            continue
        picked.append(candidate)
        if len(picked) >= 6:
            break
    return picked[:6]

def generate_world_elements_with_llm(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    user = (
        "Erzeuge genau 6 neue Elemente fuer diese Welt. "
        "Nicht Feuer/Wasser/Erde/Luft/Licht/Schatten und keine reinen Umbenennungen davon. "
        "Jedes Element braucht klar unterscheidbares Thema.\n"
        f"Weltprofil: {json.dumps({'theme': summary.get('theme', ''), 'tone': summary.get('tone', ''), 'premise': summary.get('premise', '')}, ensure_ascii=False)}"
    )
    response = call_ollama_schema(
        "Du bist ein präziser Worldbuilder. Antworte nur als JSON gemäß Schema.",
        user,
        ELEMENT_GENERATOR_SCHEMA,
        timeout=120,
        temperature=0.55,
    )
    rows = response.get("elements") if isinstance(response, dict) else []
    if not isinstance(rows, list):
        return []
    out: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        candidate = {
            "name": str(row.get("name") or "").strip(),
            "rarity": str(row.get("rarity") or "ungewöhnlich").strip() or "ungewöhnlich",
            "description": str(row.get("description") or "").strip(),
            "theme": str(row.get("theme") or "").strip(),
            "origin": "generated",
            "strengths_against": [],
            "weaknesses_against": [],
            "synergies_with": [],
            "status_effect_tags": [str(entry).strip() for entry in (row.get("status_effect_tags") or []) if str(entry).strip()],
            "class_affinities": [str(entry).strip() for entry in (row.get("class_affinities") or []) if str(entry).strip()],
            "skill_affinities": [str(entry).strip() for entry in (row.get("skill_affinities") or []) if str(entry).strip()],
            "discoverable": True,
            "lore_notes": [str(entry).strip() for entry in (row.get("lore_notes") or []) if str(entry).strip()],
            "visual_motif": str(row.get("visual_motif") or "").strip(),
            "temperament": str(row.get("temperament") or "").strip(),
            "environment_bias": str(row.get("environment_bias") or "").strip(),
            "aliases": [str(entry).strip() for entry in (row.get("aliases") or []) if str(entry).strip()],
        }
        out.append(candidate)
    return out

def generate_world_element_profiles(summary: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    elements: Dict[str, Dict[str, Any]] = {}
    core_templates = [
        ("Feuer", "core", "Zerstörerische Hitze und treibende Energie", "Verbrennung und Druck", ["brand", "hitzewallung"]),
        ("Wasser", "core", "Fluss, Anpassung und Bindung", "Kontrolle, Heilung und Sog", ["durchnässung", "strudel"]),
        ("Erde", "core", "Standfestigkeit, Last und Struktur", "Panzerung und Zermalmung", ["bruch", "fessel"]),
        ("Luft", "core", "Tempo, Reichweite und Präzision", "Bewegung und Distanzkontrolle", ["verwirbelung", "stoß"]),
        ("Licht", "core", "Offenbarung, Reinheit und Ordnung", "Blendung und Läuterung", ["blendung", "reinbrand"]),
        ("Schatten", "core", "Verhüllung, Furcht und Umgehung", "Täuschung und Entzug", ["furcht", "verhüllung"]),
    ]
    for name, origin, desc, theme, effects in core_templates:
        element_id = element_id_from_name(name)
        elements[element_id] = normalize_element_profile(
            {
                "id": element_id,
                "name": name,
                "rarity": "anker",
                "description": desc,
                "theme": theme,
                "origin": origin,
                "status_effect_tags": effects,
                "class_affinities": [normalize_codex_alias_text(name)],
                "skill_affinities": [normalize_codex_alias_text(name)],
                "discoverable": True,
                "aliases": [name],
            },
            fallback_id=element_id,
            fallback_origin=origin,
        ) or default_element_profile(element_id, name, origin=origin)

    generated_candidates: List[Dict[str, Any]] = []
    llm_attempts = 0
    max_llm_attempts = 3
    while llm_attempts < max_llm_attempts and len(generated_candidates) < 6:
        llm_attempts += 1
        try:
            batch = generate_world_elements_with_llm(summary)
        except Exception:
            batch = []
        if not batch:
            continue
        generated_candidates.extend(batch)
    accepted: List[Dict[str, Any]] = []
    rejection_notes: List[str] = []
    for candidate in generated_candidates:
        too_similar, reason = generated_element_too_similar(candidate, accepted + list(elements.values()))
        if too_similar:
            rejection_notes.append(reason)
            continue
        accepted.append(candidate)
        if len(accepted) >= 6:
            break
    if len(accepted) < 6:
        for fallback in generate_world_elements_fallback(summary):
            too_similar, reason = generated_element_too_similar(fallback, accepted + list(elements.values()))
            if too_similar:
                rejection_notes.append(reason)
                continue
            accepted.append(fallback)
            if len(accepted) >= 6:
                break
    for candidate in accepted[:6]:
        element_id = element_id_from_name(candidate.get("name", ""))
        normalized = normalize_element_profile(
            {
                **candidate,
                "id": element_id,
                "origin": "generated",
                "discoverable": True,
            },
            fallback_id=element_id,
            fallback_origin="generated",
        )
        if normalized:
            elements[element_id] = normalized
    # hard clamp to 12 elements deterministically
    elements = dict(list(stable_sorted_mapping(elements, key_fn=element_sort_key).items())[:ELEMENT_TOTAL_COUNT])
    if rejection_notes:
        meta_notes = summary.setdefault("_element_generation_notes", [])
        if isinstance(meta_notes, list):
            meta_notes.extend(rejection_notes[:12])
    return stable_sorted_mapping(elements, key_fn=element_sort_key)

def generate_element_relations(elements: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    relations = build_default_element_relations(elements)
    apply_element_anchor_relation_rules(elements, relations)
    # generated/emergent relation hints from weaknesses/strengths/synergies
    ids_by_name = {
        normalize_codex_alias_text((profile or {}).get("name", "")): element_id
        for element_id, profile in (elements or {}).items()
        if isinstance(profile, dict)
    }
    for source_id, profile in (elements or {}).items():
        if not isinstance(profile, dict):
            continue
        for target_name in (profile.get("strengths_against") or []):
            target_id = ids_by_name.get(normalize_codex_alias_text(target_name))
            if target_id:
                _set_element_relation(relations, source_id, target_id, "strong")
        for target_name in (profile.get("weaknesses_against") or []):
            target_id = ids_by_name.get(normalize_codex_alias_text(target_name))
            if target_id:
                _set_element_relation(relations, source_id, target_id, "weak")
        for target_name in (profile.get("synergies_with") or []):
            target_id = ids_by_name.get(normalize_codex_alias_text(target_name))
            if target_id and relations.get(source_id, {}).get(target_id) == "neutral":
                _set_element_relation(relations, source_id, target_id, "strong")
    return normalize_element_relations(relations, elements)

def next_element_path_name(element_name: str, rank: str, path_seed: int) -> str:
    suffixes = {
        "F": ["Novize", "Student", "Lehrling"],
        "C": ["Magier", "Wandler", "Hüter"],
        "B": ["Adept", "Weber", "Kernträger"],
        "A": ["Erzrufer", "Meister", "Archon"],
        "S": ["Legende", "Erbe", "Ultimus"],
    }
    picks = suffixes.get(rank, ["Adept"])
    return f"{element_name}-{picks[path_seed % len(picks)]}"

def generate_element_class_paths(elements: Dict[str, Dict[str, Any]], summary: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    seed_text = json.dumps(
        {"theme": summary.get("theme", ""), "tone": summary.get("tone", ""), "premise": summary.get("premise", "")},
        ensure_ascii=False,
        sort_keys=True,
    )
    rng = random.Random(int(hashlib.sha1(seed_text.encode("utf-8")).hexdigest(), 16) % (2**32))
    out: Dict[str, List[Dict[str, Any]]] = {}
    for element_id, profile in (elements or {}).items():
        if not isinstance(profile, dict):
            continue
        name = str(profile.get("name") or element_id).strip()
        path_count = clamp(1 + rng.randint(0, 2), ELEMENT_CLASS_PATH_MIN, ELEMENT_CLASS_PATH_MAX)
        paths: List[Dict[str, Any]] = []
        for path_index in range(path_count):
            path_id = f"path_{element_id}_{path_index+1}"
            rank_nodes: Dict[str, Dict[str, Any]] = {}
            for rank in ELEMENT_CLASS_PATH_RANKS:
                rank_skill_base = normalize_codex_alias_text(name).replace(" ", "_") or "element"
                rank_nodes[rank] = {
                    "id": f"{path_id}_{rank.lower()}",
                    "name": next_element_path_name(name, rank, path_index + skill_rank_sort_value(rank)),
                    "rank": rank,
                    "element_id": element_id,
                    "description": f"Pfadstufe {rank} des Elements {name}.",
                    "required_level": 1 + (skill_rank_sort_value(rank) * 3),
                    "required_class_level": 1 + skill_rank_sort_value(rank),
                    "required_affinity_tags": list(dict.fromkeys([normalize_codex_alias_text(name), *profile.get("class_affinities", [])]))[:4],
                    "required_skills": [],
                    "core_skills_required": [
                        f"{name} {['Impuls','Schnitt','Bindung'][path_index % 3]}",
                        f"{name} Fokus",
                    ],
                    "core_skills_unlockable": [
                        f"{name} Schub {rank}",
                        f"{name} Mantel {rank}",
                    ],
                    "signature_skills": [f"{name} Signatur {rank}"],
                    "signature_theme": str(profile.get("theme") or name),
                    "next_paths": [],
                    "skill_prefix": rank_skill_base,
                }
            paths.append(
                {
                    "id": path_id,
                    "name": f"{name}-Pfad {path_index+1}",
                    "element_id": element_id,
                    "signature_theme": str(profile.get("theme") or name),
                    "ranks": rank_nodes,
                }
            )
        out[element_id] = paths
    return stable_sorted_mapping(out, key_fn=lambda item: item[0])

def normalize_class_path_rank_node(raw_node: Any, *, default_rank: str, element_id: str, path_id: str) -> Optional[Dict[str, Any]]:
    if not isinstance(raw_node, dict):
        return None
    rank = normalize_skill_rank(raw_node.get("rank", default_rank))
    node_id = str(raw_node.get("id") or f"{path_id}_{rank.lower()}").strip() or f"{path_id}_{rank.lower()}"
    name = str(raw_node.get("name") or "").strip()
    if not name:
        return None
    required_affinity_tags = [str(tag).strip() for tag in (raw_node.get("required_affinity_tags") or []) if str(tag).strip()]
    required_skills = [str(skill).strip() for skill in (raw_node.get("required_skills") or []) if str(skill).strip()]
    core_required = [str(skill).strip() for skill in (raw_node.get("core_skills_required") or []) if str(skill).strip()]
    core_unlockable = [str(skill).strip() for skill in (raw_node.get("core_skills_unlockable") or []) if str(skill).strip()]
    signature_skills = [str(skill).strip() for skill in (raw_node.get("signature_skills") or []) if str(skill).strip()]
    if not core_required:
        return None
    return {
        "id": node_id,
        "name": name,
        "rank": rank,
        "element_id": str(raw_node.get("element_id") or element_id).strip() or element_id,
        "description": str(raw_node.get("description") or "").strip(),
        "required_level": max(1, int(raw_node.get("required_level", 1) or 1)),
        "required_class_level": max(1, int(raw_node.get("required_class_level", 1) or 1)),
        "required_affinity_tags": list(dict.fromkeys(required_affinity_tags)),
        "required_skills": list(dict.fromkeys(required_skills)),
        "core_skills_required": list(dict.fromkeys(core_required)),
        "core_skills_unlockable": list(dict.fromkeys(core_unlockable)),
        "signature_skills": list(dict.fromkeys(signature_skills)),
        "signature_theme": str(raw_node.get("signature_theme") or "").strip(),
        "next_paths": [str(path).strip() for path in (raw_node.get("next_paths") or []) if str(path).strip()],
        "skill_prefix": str(raw_node.get("skill_prefix") or "").strip(),
    }

def normalize_element_class_paths(
    raw_paths: Any,
    elements: Dict[str, Dict[str, Any]],
    summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    generated_defaults = generate_element_class_paths(elements, summary or {})
    if not isinstance(raw_paths, dict):
        return generated_defaults
    normalized: Dict[str, List[Dict[str, Any]]] = {}
    for element_id, element_profile in (elements or {}).items():
        bucket = raw_paths.get(element_id) if isinstance(raw_paths.get(element_id), list) else []
        valid_paths: List[Dict[str, Any]] = []
        for raw_path in bucket[:ELEMENT_CLASS_PATH_MAX]:
            if not isinstance(raw_path, dict):
                continue
            path_id = str(raw_path.get("id") or "").strip() or f"path_{element_id}_{len(valid_paths)+1}"
            path_name = str(raw_path.get("name") or "").strip()
            ranks_raw = raw_path.get("ranks") if isinstance(raw_path.get("ranks"), dict) else {}
            normalized_ranks: Dict[str, Dict[str, Any]] = {}
            complete = True
            for rank in ELEMENT_CLASS_PATH_RANKS:
                node = normalize_class_path_rank_node(
                    ranks_raw.get(rank),
                    default_rank=rank,
                    element_id=element_id,
                    path_id=path_id,
                )
                if not node:
                    complete = False
                    break
                normalized_ranks[rank] = node
            if not complete or not path_name:
                continue
            valid_paths.append(
                {
                    "id": path_id,
                    "name": path_name,
                    "element_id": element_id,
                    "signature_theme": str(raw_path.get("signature_theme") or element_profile.get("theme") or "").strip(),
                    "ranks": normalized_ranks,
                }
            )
        if not valid_paths:
            valid_paths = deep_copy(generated_defaults.get(element_id) or [])
        normalized[element_id] = valid_paths[:ELEMENT_CLASS_PATH_MAX]
    return stable_sorted_mapping(normalized, key_fn=lambda item: str(item[0]))

def ensure_world_element_system_from_setup(state: Dict[str, Any], setup_summary: Dict[str, Any]) -> None:
    world = state.setdefault("world", {})
    elements_raw = world.get("elements") if isinstance(world.get("elements"), dict) else {}
    normalized_elements: Dict[str, Dict[str, Any]] = {}
    for element_id, raw_element in elements_raw.items():
        normalized = normalize_element_profile(raw_element, fallback_id=str(element_id), fallback_origin="generated")
        if normalized:
            normalized_elements[normalized["id"]] = normalized
    if len(normalized_elements) != ELEMENT_TOTAL_COUNT:
        normalized_elements = generate_world_element_profiles(setup_summary or {})
    world["elements"] = stable_sorted_mapping(normalized_elements, key_fn=element_sort_key)
    world["element_alias_index"] = build_element_alias_index(world["elements"])
    world["element_relations"] = normalize_element_relations(world.get("element_relations"), world["elements"])
    world["element_class_paths"] = normalize_element_class_paths(
        world.get("element_class_paths"),
        world["elements"],
        setup_summary or {},
    )
    # reflect strengths/weaknesses from relation table to keep profiles coherent
    for source_id, profile in (world["elements"] or {}).items():
        rel_map = (world.get("element_relations") or {}).get(source_id) or {}
        strengths = [target for target, rel in rel_map.items() if normalize_element_relation(rel) in {"strong", "dominant"} and target != source_id]
        weaknesses = [target for target, rel in rel_map.items() if normalize_element_relation(rel) in {"weak", "countered"} and target != source_id]
        profile["strengths_against"] = strengths
        profile["weaknesses_against"] = weaknesses
    world["elements"] = stable_sorted_mapping(world["elements"], key_fn=element_sort_key)

def resolve_element_relation(world: Dict[str, Any], source_element_id: str, target_element_id: str) -> str:
    source = str(source_element_id or "").strip()
    target = str(target_element_id or "").strip()
    if not source or not target:
        return "neutral"
    relations = (world or {}).get("element_relations") if isinstance((world or {}).get("element_relations"), dict) else {}
    source_map = relations.get(source) if isinstance(relations.get(source), dict) else {}
    return normalize_element_relation(source_map.get(target, "neutral"))

def get_element_relation(world: Dict[str, Any], source_element_id: str, target_element_id: str) -> str:
    return resolve_element_relation(world, source_element_id, target_element_id)

def normalize_element_id_list(values: Any, world: Optional[Dict[str, Any]] = None) -> List[str]:
    ids = set(((world or {}).get("elements") or {}).keys()) if isinstance((world or {}).get("elements"), dict) else set()
    alias_index = ((world or {}).get("element_alias_index") or {}) if isinstance((world or {}).get("element_alias_index"), dict) else {}
    out: List[str] = []
    for raw in (values or []):
        text = str(raw or "").strip()
        if not text:
            continue
        if text in ids:
            out.append(text)
            continue
        normalized = normalize_codex_alias_text(text)
        matched = alias_index.get(normalized) if isinstance(alias_index.get(normalized), list) else []
        if isinstance(matched, list) and len(matched) == 1:
            out.append(str(matched[0]))
            continue
        candidate_id = element_id_from_name(text)
        if candidate_id in ids:
            out.append(candidate_id)
    return list(dict.fromkeys([entry for entry in out if entry]))

def normalize_skill_elements_for_world(skill: Dict[str, Any], world: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    normalized = deep_copy(skill or {})
    normalized["elements"] = normalize_element_id_list(normalized.get("elements") or [], world or {})
    primary_candidates = normalize_element_id_list([normalized.get("element_primary")], world or {})
    normalized["element_primary"] = primary_candidates[0] if primary_candidates else (normalized["elements"][0] if normalized["elements"] else None)
    if normalized.get("element_primary") and normalized["element_primary"] not in (normalized.get("elements") or []):
        normalized["elements"] = [normalized["element_primary"], *(normalized.get("elements") or [])]
    normalized["element_synergies"] = normalize_element_id_list(normalized.get("element_synergies") or [], world or {}) or None
    return normalized

def resolve_class_element_id(current_class: Optional[Dict[str, Any]], world: Dict[str, Any]) -> Optional[str]:
    klass = normalize_class_current(current_class)
    if not klass:
        return None
    existing = str(klass.get("element_id") or "").strip()
    if existing and existing in ((world.get("elements") or {})):
        return existing
    for tag in (klass.get("element_tags") or []) + (klass.get("affinity_tags") or []):
        found = normalize_element_id_list([tag], world)
        if found:
            return found[0]
    found_from_name = normalize_element_id_list([klass.get("name", "")], world)
    return found_from_name[0] if found_from_name else None

def resolve_class_path_rank_node(world: Dict[str, Any], current_class: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    klass = normalize_class_current(current_class)
    if not klass:
        return None
    element_id = resolve_class_element_id(klass, world)
    if not element_id:
        return None
    all_paths = ((world.get("element_class_paths") or {}).get(element_id) or [])
    if not isinstance(all_paths, list) or not all_paths:
        return None
    wanted_path_id = str(klass.get("path_id") or "").strip()
    rank = normalize_skill_rank(klass.get("rank", "F"))
    selected_path = None
    if wanted_path_id:
        selected_path = next((path for path in all_paths if str((path or {}).get("id") or "") == wanted_path_id), None)
    if not selected_path:
        selected_path = all_paths[0]
    ranks = (selected_path or {}).get("ranks") if isinstance((selected_path or {}).get("ranks"), dict) else {}
    node = ranks.get(rank) if isinstance(ranks.get(rank), dict) else None
    if not node:
        return None
    return {
        "path_id": str((selected_path or {}).get("id") or ""),
        "path_name": str((selected_path or {}).get("name") or ""),
        "element_id": element_id,
        "rank": rank,
        "node": deep_copy(node),
    }

def stable_sorted_mapping(values: Dict[str, Any], *, key_fn=None) -> Dict[str, Any]:
    if not isinstance(values, dict):
        return {}
    if key_fn is None:
        key_fn = lambda item: str(item[0])
    items = sorted(values.items(), key=key_fn)
    return {key: value for key, value in items}

def codex_block_order(kind: str) -> List[str]:
    if str(kind or "").strip().lower() == CODEX_KIND_RACE:
        return list(RACE_CODEX_BLOCK_ORDER)
    return list(BEAST_CODEX_BLOCK_ORDER)

def codex_blocks_for_level(kind: str, level: int) -> List[str]:
    clamped_level = clamp(int(level or 0), CODEX_KNOWLEDGE_LEVEL_MIN, CODEX_KNOWLEDGE_LEVEL_MAX)
    block_map = RACE_BLOCKS_BY_LEVEL if str(kind or "").strip().lower() == CODEX_KIND_RACE else BEAST_BLOCKS_BY_LEVEL
    ordered = codex_block_order(kind)
    unlocked: List[str] = []
    for idx in range(1, clamped_level + 1):
        for block in (block_map.get(idx) or []):
            if block in ordered and block not in unlocked:
                unlocked.append(block)
    return unlocked

def merge_known_facts_stable(existing: Any, incoming: Any) -> List[str]:
    merged: List[str] = []
    seen_keys = set()
    for source in (existing or []), (incoming or []):
        for raw in source:
            fact = str(raw or "").strip()
            if not fact:
                continue
            fact_key = normalize_codex_alias_text(fact)
            if not fact_key or fact_key in seen_keys:
                continue
            seen_keys.add(fact_key)
            merged.append(fact)
    return merged

def stable_sorted_unique_strings(values: Any, *, limit: int = 64) -> List[str]:
    cleaned = [str(value or "").strip() for value in (values or []) if str(value or "").strip()]
    deduped = sorted(set(cleaned), key=lambda value: normalize_codex_alias_text(value))
    return deduped[: max(1, int(limit or 1))]

def default_race_codex_entry(race_id: str) -> Dict[str, Any]:
    return {
        "discovered": False,
        "knowledge_level": 0,
        "known_blocks": [],
        "known_facts": [],
        "encounter_count": 0,
        "first_seen_turn": 0,
        "last_updated_turn": 0,
        "known_individuals": [],
    }

def default_beast_codex_entry(beast_id: str) -> Dict[str, Any]:
    return {
        "discovered": False,
        "knowledge_level": 0,
        "known_blocks": [],
        "known_facts": [],
        "encounter_count": 0,
        "first_seen_turn": 0,
        "last_updated_turn": 0,
        "defeated_count": 0,
        "observed_abilities": [],
    }

def normalize_codex_entry_stable(raw_entry: Any, *, kind: str) -> Dict[str, Any]:
    base = deep_copy(raw_entry) if isinstance(raw_entry, dict) else {}
    defaults = default_race_codex_entry("") if str(kind or "").strip().lower() == CODEX_KIND_RACE else default_beast_codex_entry("")
    normalized = deep_copy(defaults)
    normalized["discovered"] = bool(base.get("discovered", defaults["discovered"]))
    normalized["knowledge_level"] = clamp(
        int(base.get("knowledge_level", defaults["knowledge_level"]) or defaults["knowledge_level"]),
        CODEX_KNOWLEDGE_LEVEL_MIN,
        CODEX_KNOWLEDGE_LEVEL_MAX,
    )
    normalized["encounter_count"] = max(0, int(base.get("encounter_count", defaults["encounter_count"]) or defaults["encounter_count"]))
    normalized["first_seen_turn"] = max(0, int(base.get("first_seen_turn", defaults["first_seen_turn"]) or defaults["first_seen_turn"]))
    normalized["last_updated_turn"] = max(
        normalized["first_seen_turn"],
        int(base.get("last_updated_turn", defaults["last_updated_turn"]) or defaults["last_updated_turn"]),
    )
    order = codex_block_order(kind)
    raw_blocks = [str(block or "").strip() for block in (base.get("known_blocks") or []) if str(block or "").strip()]
    seen_blocks = set()
    known_blocks: List[str] = []
    for block in order:
        if block in raw_blocks and block not in seen_blocks:
            seen_blocks.add(block)
            known_blocks.append(block)
    normalized["known_blocks"] = known_blocks
    normalized["known_facts"] = merge_known_facts_stable(base.get("known_facts") or [], [])

    if str(kind or "").strip().lower() == CODEX_KIND_RACE:
        normalized["known_individuals"] = stable_sorted_unique_strings(base.get("known_individuals") or [], limit=64)
    else:
        normalized["defeated_count"] = max(0, int(base.get("defeated_count", defaults.get("defeated_count", 0)) or defaults.get("defeated_count", 0)))
        normalized["observed_abilities"] = stable_sorted_unique_strings(base.get("observed_abilities") or [], limit=64)
    return normalized

def race_profile_block_facts(profile: Dict[str, Any]) -> Dict[str, List[str]]:
    return {
        "identity": [
            f"Art: {profile.get('kind') or 'Volk'}",
            f"Seltenheit: {profile.get('rarity') or 'gewöhnlich'}",
            f"Kurzprofil: {profile.get('description_short') or 'Noch kein Eintrag.'}",
        ],
        "appearance": [f"Erscheinung: {profile.get('appearance') or 'Noch unbekannt.'}"],
        "culture": [
            f"Kultur: {profile.get('culture') or 'Noch unbekannt.'}",
            f"Temperament: {profile.get('temperament') or 'Noch unbekannt.'}",
        ],
        "homeland": [f"Heimat: {profile.get('homeland') or 'Unbekannt.'}"],
        "class_affinities": [f"Klassen-Affinitäten: {', '.join(profile.get('class_affinities') or []) or 'Keine gesicherten Daten.'}"],
        "skill_affinities": [f"Skill-Affinitäten: {', '.join(profile.get('skill_affinities') or []) or 'Keine gesicherten Daten.'}"],
        "strengths": [f"Stärken: {', '.join(profile.get('strength_tags') or []) or 'Noch unbekannt.'}"],
        "weaknesses": [f"Schwächen: {', '.join(profile.get('weakness_tags') or []) or 'Noch unbekannt.'}"],
        "relations": [f"Sozialer Ruf: {profile.get('social_reputation') or 'Noch unklar.'}"],
        "notable_individuals": [f"Bekannte Merkmale: {', '.join(profile.get('notable_traits') or []) or 'Noch keine bekannten Merkmale.'}"],
    }

def beast_profile_block_facts(profile: Dict[str, Any]) -> Dict[str, List[str]]:
    return {
        "identity": [
            f"Kategorie: {profile.get('category') or 'Bestie'}",
            f"Gefahrenstufe: {int(profile.get('danger_rating', 1) or 1)}",
        ],
        "appearance": [f"Erscheinung: {profile.get('appearance') or 'Noch unbekannt.'}"],
        "habitat": [f"Lebensraum: {profile.get('habitat') or 'Noch unbekannt.'}"],
        "behavior": [f"Verhalten: {profile.get('behavior') or 'Noch unbekannt.'}"],
        "combat_style": [f"Kampfstil: {profile.get('combat_style') or 'Noch unbekannt.'}"],
        "known_abilities": [f"Bekannte Fähigkeiten: {', '.join(profile.get('known_abilities') or []) or 'Noch keine gesicherten Daten.'}"],
        "strengths": [f"Stärken: {', '.join(profile.get('strength_tags') or []) or 'Noch unbekannt.'}"],
        "weaknesses": [f"Schwächen: {', '.join(profile.get('weakness_tags') or []) or 'Noch unbekannt.'}"],
        "loot": [f"Loot-Hinweise: {', '.join(profile.get('loot_tags') or []) or 'Noch keine Hinweise.'}"],
        "lore": [f"Lore: {', '.join(profile.get('lore_notes') or []) or 'Noch keine Aufzeichnungen.'}"],
    }

def codex_facts_for_blocks(kind: str, profile: Dict[str, Any], blocks: List[str]) -> List[str]:
    kind_key = str(kind or "").strip().lower()
    block_map = race_profile_block_facts(profile) if kind_key == CODEX_KIND_RACE else beast_profile_block_facts(profile)
    ordered_blocks = [block for block in codex_block_order(kind_key) if block in (blocks or [])]
    facts: List[str] = []
    for block in ordered_blocks:
        facts = merge_known_facts_stable(facts, block_map.get(block) or [])
    return facts

def build_world_alias_indexes(world: Dict[str, Any]) -> Dict[str, Dict[str, List[str]]]:
    race_aliases: Dict[str, set] = {}
    beast_aliases: Dict[str, set] = {}
    for race_id, race in ((world.get("races") or {}).items()):
        if not isinstance(race, dict):
            continue
        variants = build_entity_alias_variants(str(race.get("name") or ""), race.get("aliases") if isinstance(race.get("aliases"), list) else [])
        for alias in variants:
            race_aliases.setdefault(alias, set()).add(str(race_id))
    for beast_id, beast in ((world.get("beast_types") or {}).items()):
        if not isinstance(beast, dict):
            continue
        variants = build_entity_alias_variants(str(beast.get("name") or ""), beast.get("aliases") if isinstance(beast.get("aliases"), list) else [])
        for alias in variants:
            beast_aliases.setdefault(alias, set()).add(str(beast_id))
    race_index = {alias: sorted(ids) for alias, ids in stable_sorted_mapping(race_aliases).items()}
    beast_index = {alias: sorted(ids) for alias, ids in stable_sorted_mapping(beast_aliases).items()}
    return {"race_alias_index": race_index, "beast_alias_index": beast_index}

def build_world_exact_name_index(world: Dict[str, Any]) -> Dict[str, Dict[str, List[str]]]:
    race_names: Dict[str, set] = {}
    beast_names: Dict[str, set] = {}
    for race_id, race in ((world.get("races") or {}).items()):
        name_norm = normalize_codex_alias_text((race or {}).get("name", ""))
        if name_norm:
            race_names.setdefault(name_norm, set()).add(str(race_id))
    for beast_id, beast in ((world.get("beast_types") or {}).items()):
        name_norm = normalize_codex_alias_text((beast or {}).get("name", ""))
        if name_norm:
            beast_names.setdefault(name_norm, set()).add(str(beast_id))
    return {
        "race_names": {alias: sorted(ids) for alias, ids in stable_sorted_mapping(race_names).items()},
        "beast_names": {alias: sorted(ids) for alias, ids in stable_sorted_mapping(beast_names).items()},
    }

def resolve_codex_entity_ids(text: str, alias_index: Dict[str, List[str]], exact_names: Optional[Dict[str, List[str]]] = None) -> Dict[str, Any]:
    normalized_text = normalize_codex_alias_text(text)
    if not normalized_text:
        return {"matched": [], "ambiguous": [], "matched_aliases": {}}
    matched_aliases: Dict[str, set] = {}
    ambiguous: List[Dict[str, Any]] = []
    search_space: Dict[str, List[str]] = {}

    for alias, ids in (alias_index or {}).items():
        alias_norm = normalize_codex_alias_text(alias)
        if not alias_norm:
            continue
        dedup_ids = sorted({str(entry).strip() for entry in (ids or []) if str(entry).strip()})
        if dedup_ids:
            search_space[alias_norm] = dedup_ids
    for alias, ids in (exact_names or {}).items():
        alias_norm = normalize_codex_alias_text(alias)
        if not alias_norm or alias_norm in search_space:
            continue
        dedup_ids = sorted({str(entry).strip() for entry in (ids or []) if str(entry).strip()})
        if dedup_ids:
            search_space[alias_norm] = dedup_ids

    for alias in sorted(search_space.keys(), key=lambda value: (-len(value), value)):
        pattern = rf"(?<!\w){re.escape(alias)}(?!\w)"
        if not re.search(pattern, normalized_text):
            continue
        ids = search_space[alias]
        if len(ids) == 1:
            matched_aliases.setdefault(ids[0], set()).add(alias)
        else:
            ambiguous.append({"alias": alias, "entity_ids": list(ids)})

    matched_ids = sorted(matched_aliases.keys())
    return {
        "matched": matched_ids,
        "ambiguous": ambiguous,
        "matched_aliases": {entity_id: sorted(aliases) for entity_id, aliases in matched_aliases.items()},
    }

def world_codex_sort_key(entry: Tuple[str, Dict[str, Any]]) -> Tuple[str, str]:
    entity_id, payload = entry
    return (normalize_codex_alias_text((payload or {}).get("name", "")), str(entity_id))

def normalize_world_codex_structures(state: Dict[str, Any]) -> None:
    world = state.setdefault("world", {})
    world_races = world.get("races") if isinstance(world.get("races"), dict) else {}
    world_beasts = world.get("beast_types") if isinstance(world.get("beast_types"), dict) else {}
    world_elements = world.get("elements") if isinstance(world.get("elements"), dict) else {}

    cleaned_races: Dict[str, Dict[str, Any]] = {}
    for raw_id, raw_profile in world_races.items():
        profile = normalize_race_profile(raw_profile, fallback_id=str(raw_id))
        if not profile:
            continue
        cleaned_races[profile["id"]] = profile
    cleaned_races = stable_sorted_mapping(cleaned_races, key_fn=world_codex_sort_key)

    cleaned_beasts: Dict[str, Dict[str, Any]] = {}
    for raw_id, raw_profile in world_beasts.items():
        profile = normalize_beast_profile(raw_profile, fallback_id=str(raw_id))
        if not profile:
            continue
        cleaned_beasts[profile["id"]] = profile
    cleaned_beasts = stable_sorted_mapping(cleaned_beasts, key_fn=world_codex_sort_key)

    cleaned_elements: Dict[str, Dict[str, Any]] = {}
    for raw_id, raw_profile in world_elements.items():
        fallback_origin = "core" if normalize_codex_alias_text((raw_profile or {}).get("name", "")) in {
            normalize_codex_alias_text(name) for name in ELEMENT_CORE_NAMES
        } else "generated"
        profile = normalize_element_profile(raw_profile, fallback_id=str(raw_id), fallback_origin=fallback_origin)
        if not profile:
            continue
        cleaned_elements[profile["id"]] = profile
    cleaned_elements = stable_sorted_mapping(cleaned_elements, key_fn=element_sort_key)

    world["races"] = cleaned_races
    world["beast_types"] = cleaned_beasts
    world["elements"] = cleaned_elements
    alias_indexes = build_world_alias_indexes(world)
    world["race_alias_index"] = alias_indexes["race_alias_index"]
    world["beast_alias_index"] = alias_indexes["beast_alias_index"]
    world["element_alias_index"] = build_element_alias_index(cleaned_elements)
    world["element_relations"] = normalize_element_relations(world.get("element_relations"), cleaned_elements)
    world["element_class_paths"] = normalize_element_class_paths(
        world.get("element_class_paths"),
        cleaned_elements,
        ((state.get("setup") or {}).get("world") or {}).get("summary") or {},
    )

    codex = state.setdefault("codex", {})
    codex_meta = codex.get("meta") if isinstance(codex.get("meta"), dict) else {}
    normalized_meta = deep_copy(CODEX_DEFAULT_META)
    normalized_meta.update({str(key): value for key, value in codex_meta.items()})
    codex["meta"] = normalized_meta

    codex_races_raw = codex.get("races") if isinstance(codex.get("races"), dict) else {}
    codex_beasts_raw = codex.get("beasts") if isinstance(codex.get("beasts"), dict) else {}
    normalized_codex_races: Dict[str, Dict[str, Any]] = {}
    normalized_codex_beasts: Dict[str, Dict[str, Any]] = {}
    for race_id in cleaned_races.keys():
        normalized_codex_races[race_id] = normalize_codex_entry_stable(codex_races_raw.get(race_id), kind=CODEX_KIND_RACE)
    for beast_id in cleaned_beasts.keys():
        normalized_codex_beasts[beast_id] = normalize_codex_entry_stable(codex_beasts_raw.get(beast_id), kind=CODEX_KIND_BEAST)
    for raw_id, raw_entry in codex_races_raw.items():
        race_id = str(raw_id or "").strip()
        if race_id and race_id not in normalized_codex_races:
            normalized_codex_races[race_id] = normalize_codex_entry_stable(raw_entry, kind=CODEX_KIND_RACE)
    for raw_id, raw_entry in codex_beasts_raw.items():
        beast_id = str(raw_id or "").strip()
        if beast_id and beast_id not in normalized_codex_beasts:
            normalized_codex_beasts[beast_id] = normalize_codex_entry_stable(raw_entry, kind=CODEX_KIND_BEAST)

    codex["races"] = stable_sorted_mapping(
        normalized_codex_races,
        key_fn=lambda item: (
            normalize_codex_alias_text(str((((world.get("races") or {}).get(item[0]) or {}).get("name") or item[0]))),
            item[0],
        ),
    )
    codex["beasts"] = stable_sorted_mapping(
        normalized_codex_beasts,
        key_fn=lambda item: (
            normalize_codex_alias_text(str((((world.get("beast_types") or {}).get(item[0]) or {}).get("name") or item[0]))),
            item[0],
        ),
    )

def pick_world_theme_anchor(summary: Dict[str, Any]) -> str:
    theme = normalize_codex_alias_text(summary.get("theme", ""))
    if "wuest" in theme or "sand" in theme:
        return "desert"
    if "wald" in theme or "forest" in theme:
        return "forest"
    if "urban" in theme or "stadt" in theme:
        return "urban"
    if "isekai" in theme or "hybrid" in theme:
        return "hybrid"
    return "default"

def codex_seed_for_state(state: Dict[str, Any]) -> str:
    meta = state.setdefault("meta", {})
    seed = str(meta.get("world_codex_seed") or "").strip()
    if not seed:
        seed = make_id("wseed")
        meta["world_codex_seed"] = seed
    return seed

def fantasy_syllables_for_anchor(anchor: str) -> Tuple[List[str], List[str], List[str]]:
    if anchor == "desert":
        return (
            ["ash", "zar", "qir", "sah", "tal", "mir", "kha"],
            ["a", "e", "o", "u", "ir", "ar"],
            ["dun", "kar", "mir", "zar", "thar", "ren"],
        )
    if anchor == "forest":
        return (
            ["sil", "tha", "fen", "lor", "ny", "ael", "bri"],
            ["a", "e", "i", "ia", "ae", "el"],
            ["wen", "lith", "rien", "vale", "dor", "mir"],
        )
    if anchor == "urban":
        return (
            ["vor", "ka", "dra", "ser", "mor", "lin", "tek"],
            ["a", "e", "i", "o", "ur", "en"],
            ["gard", "port", "vex", "tarn", "heim", "crest"],
        )
    if anchor == "hybrid":
        return (
            ["neo", "ae", "ry", "sol", "ky", "zen", "myr"],
            ["a", "e", "io", "ae", "u", "i"],
            ["flux", "lume", "veil", "core", "ryn", "nex"],
        )
    return (
        ["el", "ka", "mor", "val", "rin", "tor", "lys"],
        ["a", "e", "i", "o", "ae", "ia"],
        ["dor", "ria", "en", "or", "is", "ane"],
    )

def generate_unique_fantasy_name(
    rng: random.Random,
    used: Set[str],
    *,
    anchor: str,
    suffixes: List[str],
    max_attempts: int = 40,
) -> str:
    prefixes, middles, tails = fantasy_syllables_for_anchor(anchor)
    for _ in range(max_attempts):
        parts = [rng.choice(prefixes), rng.choice(middles), rng.choice(tails)]
        if rng.random() < 0.3:
            parts.insert(2, rng.choice(["n", "r", "l", "th"]))
        base = "".join(parts).replace(" ", "")
        raw_name = f"{base}{rng.choice(suffixes)}".strip()
        name = raw_name[:1].upper() + raw_name[1:]
        key = normalize_codex_alias_text(name)
        if key and key not in used:
            used.add(key)
            return name
    fallback = f"{rng.choice(['Ael', 'Vor', 'Kael', 'Nyx'])}{rng.randint(100, 999)}"
    used.add(normalize_codex_alias_text(fallback))
    return fallback

def generate_world_name(summary: Dict[str, Any], seed_hint: str) -> str:
    anchor = pick_world_theme_anchor(summary)
    seed_text = json.dumps(
        {
            "theme": summary.get("theme", ""),
            "tone": summary.get("tone", ""),
            "seed": seed_hint,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    rng = random.Random(int(hashlib.sha1(seed_text.encode("utf-8")).hexdigest(), 16) % (2**32))
    used: Set[str] = set()
    return generate_unique_fantasy_name(rng, used, anchor=anchor, suffixes=["", "ia", "or", "is"])

def generate_world_race_profiles(summary: Dict[str, Any], *, seed_hint: str = "") -> Dict[str, Dict[str, Any]]:
    anchor = pick_world_theme_anchor(summary)
    seed_text = json.dumps(
        {
            "theme": summary.get("theme", ""),
            "tone": summary.get("tone", ""),
            "conflict": summary.get("central_conflict", ""),
            "anchor": anchor,
            "seed": seed_hint,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    rng = random.Random(int(hashlib.sha1(seed_text.encode("utf-8")).hexdigest(), 16) % (2**32))
    race_count = clamp(5 + rng.randint(0, 2), 5, 7)
    used_names: Set[str] = set()
    race_suffixes = ["ar", "en", "iden", "ari", "orn", "eth", "yr"]
    temperaments = ["ruhig", "wachsam", "stur", "berechnend", "pflichtbewusst", "wechselhaft", "intensiv"]
    archetypes = [
        {
            "kind": "menschenvolk",
            "rarity": "gewöhnlich",
            "description_short": "Anpassungsfähiges Volk mit schneller sozialer Dynamik.",
            "appearance": "Vielfältige Erscheinungsbilder und praktische Reiseausrüstung.",
            "homeland": "Grenzstädte und Handelsachsen",
            "culture": "Pragmatisch, fraktionsnah und zielorientiert",
            "strength_tags": ["anpassung", "diplomatie", "handwerk"],
            "weakness_tags": ["interne_spaltung", "kurze_lebensspanne"],
            "class_affinities": ["ritter", "schuetze", "haendler"],
            "skill_affinities": ["führung", "taktik", "überleben"],
            "social_reputation": "dominant, aber umkämpft",
            "notable_traits": ["schnelle lernkurve", "fraktionsnetzwerke"],
        },
        {
            "kind": "langlebiges magiervolk",
            "rarity": "selten",
            "description_short": "Langlebiges Volk mit strenger Erinnerungskultur und arkaner Disziplin.",
            "appearance": "Feine Gesichtszüge und leuchtende Runenlinien.",
            "homeland": "Haine, Archive und uralte Observatorien",
            "culture": "Ritualisiert und wissenszentriert",
            "strength_tags": ["arkane_praezision", "mentale_disziplin"],
            "weakness_tags": ["fragile_koerper", "ueberheblichkeit"],
            "class_affinities": ["runenweber", "mystiker", "hüter"],
            "skill_affinities": ["analyse", "barrieren", "kanalisierung"],
            "social_reputation": "respektiert und gefürchtet",
            "notable_traits": ["langes gedächtnis", "rituelle namenbindung"],
        },
        {
            "kind": "robustes bergvolk",
            "rarity": "ungewöhnlich",
            "description_short": "Robustes Volk mit strikten Eiden und handwerklicher Kriegskultur.",
            "appearance": "Massiger Körperbau, Narben und metallene Tätowierungen.",
            "homeland": "Gebirgsschächte, Basaltfesten und Erzpfade",
            "culture": "Ehrenkodex, Schuldbücher und Werkbanktradition",
            "strength_tags": ["zähigkeit", "rüstungshandwerk", "nahkampf"],
            "weakness_tags": ["starre_riten", "langsame_anpassung"],
            "class_affinities": ["vorhut", "schmied", "waechter"],
            "skill_affinities": ["schildtechnik", "metallkunde", "standhaftigkeit"],
            "social_reputation": "verlässlich, aber unnachgiebig",
            "notable_traits": ["eidsiegel", "steinlieder"],
        },
    ]
    while len(archetypes) < race_count:
        archetypes.append(
            {
                "kind": rng.choice(["schleierkultur", "resonanzvolk", "nomadenvolk", "karglandvolk", "lichtordenvolk"]),
                "rarity": rng.choice(["gewöhnlich", "ungewöhnlich", "selten"]),
                "description_short": rng.choice(
                    [
                        "Eigenständiges Volk mit starker Bindung an lokale Weltgesetze.",
                        "Grenzvolk, dessen Überleben auf strengen Pakten beruht.",
                        "Kultur mit ausgeprägter Ritual- und Verpflichtungslogik.",
                    ]
                ),
                "appearance": rng.choice(
                    [
                        "Markante Hautmuster und rituelle Kleidungsschichten.",
                        "Körpermale, die bei Ressourcennutzung sichtbar pulsieren.",
                        "Praktische Panzerstoffe mit kulturellen Siegelzeichen.",
                    ]
                ),
                "homeland": rng.choice(
                    [
                        "Nebelgrenzen und zerfallene Grenzruinen",
                        "Aschepfade, Kraterfelder und Schutzzelte",
                        "Klüfte, Archive und halbversunkene Bastionen",
                    ]
                ),
                "culture": rng.choice(
                    [
                        "Schwurbündnisse, Ahnenpfade und strenge Mentorenlinien",
                        "Tauschrituale, Schuldzeichen und Pflichtkataloge",
                        "Prüfpfade, Bündnisrecht und Überlebensethos",
                    ]
                ),
                "strength_tags": rng.sample(["täuschung", "resonanz", "ausdauer", "spurlesen", "barriere", "segen"], 3),
                "weakness_tags": rng.sample(["lichtempfindlich", "dogmatisch", "starre_riten", "wasserknappheit", "überlastung"], 2),
                "class_affinities": rng.sample(["späher", "hexer", "hüter", "katalysator", "jäger", "totemkrieger"], 3),
                "skill_affinities": rng.sample(["verschleierung", "kanalisierung", "fährtenlesen", "durchhaltewillen", "sigillen"], 3),
                "social_reputation": rng.choice(["misstrauisch beobachtet", "politisch umkämpft", "respektiert als Grenzmacht"]),
                "notable_traits": rng.sample(["namensmasken", "resonanzkrisen", "ahnenmasken", "wahrheitssiegel", "schuldbänder"], 2),
            }
        )
    races: Dict[str, Dict[str, Any]] = {}
    for template in archetypes[:race_count]:
        name = generate_unique_fantasy_name(rng, used_names, anchor=anchor, suffixes=race_suffixes)
        race_id = race_id_from_name(name)
        temperament = rng.choice(temperaments)
        races[race_id] = normalize_race_profile({**template, "id": race_id}, fallback_id=race_id) or default_race_profile(race_id, template.get("name", ""))
        races[race_id]["name"] = name
        races[race_id]["temperament"] = temperament
        races[race_id]["aliases"] = [f"Volk von {name}", f"{name}er"]
    return stable_sorted_mapping(races, key_fn=world_codex_sort_key)

def generate_world_beast_profiles(summary: Dict[str, Any], *, seed_hint: str = "") -> Dict[str, Dict[str, Any]]:
    anchor = pick_world_theme_anchor(summary)
    seed_text = json.dumps(
        {
            "theme": summary.get("theme", ""),
            "tone": summary.get("tone", ""),
            "density": summary.get("monsters_density", ""),
            "anchor": anchor,
            "seed": seed_hint,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    rng = random.Random(int(hashlib.sha1(seed_text.encode("utf-8")).hexdigest(), 16) % (2**32))
    beast_count = clamp(6 + rng.randint(0, 6), 6, 12)
    used_names: Set[str] = set()
    beast_suffixes = ["fang", "wyrm", "krall", "stachel", "geist", "mimik", "hydra", "schnitter"]
    categories = ["bestie", "aberration", "flugbestie", "koloss", "geistbestie", "schwarm", "konstrukt", "wasserbestie"]
    habitats = [
        "Nebelwälder",
        "Obeliskenruinen",
        "Kraterpfade",
        "Grenzgräben und Ruinenfelder",
        "Felsstädte und Kapellenruinen",
        "Vergiftete Feuchtlande",
        "Versunkene Tempel",
    ]
    behaviors = [
        "jagt aus dem Hinterhalt und umkreist verwundete Ziele",
        "patrouilliert feste Reviere und reagiert auf Ressourcenimpulse",
        "lockt Gruppen in ungünstige Positionen",
        "verteidigt Brutreviere aggressiv",
    ]
    beasts: Dict[str, Dict[str, Any]] = {}
    for _ in range(beast_count):
        name = generate_unique_fantasy_name(rng, used_names, anchor=anchor, suffixes=beast_suffixes)
        beast_id = beast_id_from_name(name)
        template = {
            "id": beast_id,
            "name": name,
            "category": rng.choice(categories),
            "danger_rating": clamp(2 + rng.randint(0, 10), 1, 20),
            "habitat": rng.choice(habitats),
            "behavior": rng.choice(behaviors),
            "appearance": rng.choice(
                [
                    "Panzerartige Hautsegmente mit unruhigem Schimmer.",
                    "Sehniger Körperbau mit markanten Klingen- und Hornstrukturen.",
                    "Schattenhafte Konturen, die im Kampf flackern.",
                ]
            ),
            "strength_tags": rng.sample(["hinterhalt", "wucht", "regeneration", "schnelligkeit", "panzerung", "schwarmdruck"], 2),
            "weakness_tags": rng.sample(["blendlicht", "feuer", "eis", "resonanzzauber", "netzfallen", "ritualkreide"], 2),
            "combat_style": rng.choice(["schnelle Flankenangriffe", "Dauerdruck über Reichweite", "kurze Burst-Angriffe aus Tarnung", "wuchtige Zonenangriffe"]),
            "known_abilities": rng.sample(["Nebeltritt", "Kernstoß", "Dornenwurf", "Kältefessel", "Truemmerwelle", "Sogkante"], 2),
            "loot_tags": rng.sample(["kernsplitter", "sehnenfaser", "schuppenstück", "geiststaub", "kralle"], 2),
            "lore_notes": [rng.choice(["Meidet geweihte Feuerlinien.", "Reagiert stark auf resonierende Metallklänge.", "Wird bei knapper Ressource aggressiver."])],
            "aliases": [f"{name}-Typ", f"{name}rudel"],
        }
        beasts[beast_id] = normalize_beast_profile(template, fallback_id=beast_id) or default_beast_profile(beast_id, name)
    return stable_sorted_mapping(beasts, key_fn=world_codex_sort_key)

def ensure_world_codex_from_setup(state: Dict[str, Any], setup_summary: Dict[str, Any]) -> None:
    world = state.setdefault("world", {})
    seed_hint = codex_seed_for_state(state)
    world_races = world.get("races") if isinstance(world.get("races"), dict) else {}
    world_beasts = world.get("beast_types") if isinstance(world.get("beast_types"), dict) else {}
    setup_summary = setup_summary or {}
    if not str(setup_summary.get("world_name") or "").strip():
        setup_summary["world_name"] = generate_world_name(setup_summary, seed_hint)
    if not world_races:
        world["races"] = generate_world_race_profiles(setup_summary, seed_hint=seed_hint)
    if not world_beasts:
        world["beast_types"] = generate_world_beast_profiles(setup_summary, seed_hint=seed_hint)
    ensure_world_element_system_from_setup(state, setup_summary)
    normalize_world_codex_structures(state)

def default_npc_entry(npc_id: str, name: str) -> Dict[str, Any]:
    return {
        "npc_id": npc_id,
        "name": str(name or "").strip(),
        "race": "Unbekannt",
        "age": "Unbekannt",
        "goal": "",
        "level": 1,
        "backstory_short": "",
        "role_hint": "",
        "faction": "",
        "last_seen_scene_id": "",
        "first_seen_turn": 0,
        "last_seen_turn": 0,
        "mention_count": 1,
        "relevance_score": 0,
        "status": "active",
        "tags": ["npc", "story_relevant"],
        "history_notes": [],
        "class_current": None,
        "skills": {},
        "xp_total": 0,
        "xp_current": 0,
        "xp_to_next": 120,
        "hp_current": 10,
        "hp_max": 10,
        "sta_current": 8,
        "sta_max": 8,
        "res_current": 4,
        "res_max": 4,
        "element_affinities": [],
        "element_resistances": [],
        "element_weaknesses": [],
        "conditions": [],
        "injuries": [],
        "scars": [],
    }

def normalize_npc_entry(raw: Any, *, fallback_npc_id: str = "") -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip()
    if not name:
        return None
    npc_id = str(raw.get("npc_id") or fallback_npc_id or npc_id_from_name(name)).strip()
    if not npc_id:
        return None
    entry = default_npc_entry(npc_id, name)
    entry["race"] = str(raw.get("race") or entry["race"]).strip() or "Unbekannt"
    entry["age"] = str(raw.get("age") or entry["age"]).strip() or "Unbekannt"
    entry["goal"] = str(raw.get("goal") or "").strip()
    entry["level"] = clamp(int(raw.get("level", 1) or 1), 1, 999)
    entry["backstory_short"] = str(raw.get("backstory_short") or "").strip()
    entry["role_hint"] = str(raw.get("role_hint") or "").strip()
    entry["faction"] = str(raw.get("faction") or "").strip()
    entry["last_seen_scene_id"] = str(raw.get("last_seen_scene_id") or "").strip()
    entry["first_seen_turn"] = max(0, int(raw.get("first_seen_turn", 0) or 0))
    entry["last_seen_turn"] = max(entry["first_seen_turn"], int(raw.get("last_seen_turn", 0) or 0))
    entry["mention_count"] = max(1, int(raw.get("mention_count", 1) or 1))
    entry["relevance_score"] = max(0, int(raw.get("relevance_score", 0) or 0))
    status = str(raw.get("status") or "active").strip().lower()
    entry["status"] = status if status in NPC_STATUS_ALLOWED else "active"
    tags = [str(tag).strip() for tag in (raw.get("tags") or []) if str(tag).strip()]
    entry["tags"] = list(dict.fromkeys(tags or entry["tags"]))
    history_notes = [str(note).strip() for note in (raw.get("history_notes") or []) if str(note).strip()]
    entry["history_notes"] = history_notes[-20:]
    entry["class_current"] = normalize_class_current(raw.get("class_current"))
    npc_resource_name = normalize_resource_name((((raw.get("progression") or {}).get("resource_name")) or "Aether"), "Aether")
    entry["skills"] = normalize_skill_store(raw.get("skills") or {}, resource_name=npc_resource_name)
    entry["xp_total"] = max(0, int(raw.get("xp_total", entry.get("xp_total", 0)) or entry.get("xp_total", 0)))
    entry["xp_to_next"] = max(1, int(raw.get("xp_to_next", entry.get("xp_to_next", next_character_xp_for_level(entry["level"]))) or next_character_xp_for_level(entry["level"])))
    entry["xp_current"] = clamp(int(raw.get("xp_current", entry.get("xp_current", 0)) or entry.get("xp_current", 0)), 0, entry["xp_to_next"])
    entry["hp_max"] = max(1, int(raw.get("hp_max", entry.get("hp_max", 10)) or entry.get("hp_max", 10)))
    entry["hp_current"] = clamp(int(raw.get("hp_current", entry.get("hp_current", entry["hp_max"])) or entry.get("hp_current", entry["hp_max"])), 0, entry["hp_max"])
    entry["sta_max"] = max(0, int(raw.get("sta_max", entry.get("sta_max", 8)) or entry.get("sta_max", 8)))
    entry["sta_current"] = clamp(int(raw.get("sta_current", entry.get("sta_current", entry["sta_max"])) or entry.get("sta_current", entry["sta_max"])), 0, entry["sta_max"])
    entry["res_max"] = max(0, int(raw.get("res_max", entry.get("res_max", 4)) or entry.get("res_max", 4)))
    entry["res_current"] = clamp(int(raw.get("res_current", entry.get("res_current", entry["res_max"])) or entry.get("res_current", entry["res_max"])), 0, entry["res_max"])
    entry["element_affinities"] = [str(value).strip() for value in (raw.get("element_affinities") or []) if str(value).strip()][:8]
    entry["element_resistances"] = [str(value).strip() for value in (raw.get("element_resistances") or []) if str(value).strip()][:8]
    entry["element_weaknesses"] = [str(value).strip() for value in (raw.get("element_weaknesses") or []) if str(value).strip()][:8]
    entry["conditions"] = [str(cond).strip() for cond in (raw.get("conditions") or []) if str(cond).strip()][:12]
    entry["injuries"] = [deep_copy(item) for item in (raw.get("injuries") or []) if isinstance(item, dict)][:16]
    entry["scars"] = [deep_copy(item) for item in (raw.get("scars") or []) if isinstance(item, dict)][:24]
    return entry

def normalize_npc_codex_state(campaign: Dict[str, Any]) -> None:
    state = campaign.setdefault("state", {})
    state.setdefault("npc_codex", {})
    state.setdefault("npc_alias_index", {})
    cleaned_codex: Dict[str, Dict[str, Any]] = {}
    cleaned_alias: Dict[str, str] = {}
    for raw_id, raw_entry in (state.get("npc_codex") or {}).items():
        normalized_entry = normalize_npc_entry(raw_entry, fallback_npc_id=str(raw_id or "").strip())
        if not normalized_entry:
            continue
        npc_id = normalized_entry["npc_id"]
        normalized_entry["element_affinities"] = normalize_element_id_list(normalized_entry.get("element_affinities") or [], state.get("world") or {})
        normalized_entry["element_resistances"] = normalize_element_id_list(normalized_entry.get("element_resistances") or [], state.get("world") or {})
        normalized_entry["element_weaknesses"] = normalize_element_id_list(normalized_entry.get("element_weaknesses") or [], state.get("world") or {})
        npc_resource_name = normalize_resource_name((((normalized_entry.get("progression") or {}).get("resource_name")) or "Aether"), "Aether")
        normalized_skills: Dict[str, Dict[str, Any]] = {}
        for skill_id, raw_skill in ((normalized_entry.get("skills") or {}).items()):
            skill = normalize_dynamic_skill_state(raw_skill, skill_id=str(skill_id), resource_name=npc_resource_name)
            skill = normalize_skill_elements_for_world(skill, state.get("world") or {})
            normalized_skills[skill["id"]] = skill
        normalized_entry["skills"] = normalized_skills
        cleaned_codex[npc_id] = normalized_entry
        alias = normalize_npc_alias(normalized_entry.get("name", ""))
        if alias:
            cleaned_alias[alias] = npc_id
    for raw_alias, raw_npc_id in (state.get("npc_alias_index") or {}).items():
        alias = normalize_npc_alias(str(raw_alias or ""))
        npc_id = str(raw_npc_id or "").strip()
        if alias and npc_id in cleaned_codex:
            cleaned_alias[alias] = npc_id
    state["npc_codex"] = cleaned_codex
    state["npc_alias_index"] = cleaned_alias

def seed_npc_codex_from_story_cards(campaign: Dict[str, Any]) -> None:
    state = campaign.setdefault("state", {})
    codex = state.setdefault("npc_codex", {})
    alias_index = state.setdefault("npc_alias_index", {})
    turn = int(((state.get("meta") or {}).get("turn") or 0))
    for card in (campaign.get("boards", {}).get("story_cards") or []):
        if not isinstance(card, dict) or str(card.get("kind") or "").strip().lower() != "npc":
            continue
        name = str(card.get("title") or "").strip()
        if not name:
            continue
        npc_id = npc_id_from_name(name)
        if npc_id in codex:
            continue
        entry = default_npc_entry(npc_id, name)
        entry["backstory_short"] = str(card.get("content") or "").strip()[:260]
        entry["first_seen_turn"] = turn
        entry["last_seen_turn"] = turn
        entry["relevance_score"] = 2
        entry["history_notes"] = [f"Aus Story-Karte übernommen: {entry['backstory_short'][:120]}"] if entry["backstory_short"] else []
        codex[npc_id] = entry
        alias = normalize_npc_alias(name)
        if alias:
            alias_index[alias] = npc_id

def default_world_time() -> Dict[str, Any]:
    return {
        "day": 1,
        "month": 1,
        "year": 1,
        "time_of_day": "night",
        "weather": "",
        "absolute_day": 1,
    }

def default_intro_state() -> Dict[str, Any]:
    return {
        "status": "idle",
        "last_error": "",
        "last_attempt_at": "",
        "generated_turn_id": "",
    }

def default_appearance_profile() -> Dict[str, Any]:
    return {
        "height": "average",
        "build": "neutral",
        "muscle": 0,
        "fat": 0,
        "scars": [],
        "aura": "none",
        "eyes": {
            "base": "",
            "current": "",
        },
        "hair": {
            "color": "",
            "style": "",
            "current": "",
        },
        "skin_marks": [],
        "voice_tone": "",
        "visual_modifiers": [],
        "summary_short": "",
        "summary_full": "",
    }

def default_character_modifiers() -> Dict[str, Any]:
    return {
        "resource_max": [],
        "derived": [],
        "appearance_flags": [],
        "skill_effective": [],
    }

def default_class_current() -> Dict[str, Any]:
    return {
        "id": "",
        "name": "",
        "rank": "F",
        "path_id": "",
        "path_rank": "F",
        "element_id": "",
        "element_tags": [],
        "level": 1,
        "level_max": 10,
        "xp": 0,
        "xp_next": 100,
        "class_id": "",
        "class_name": "",
        "class_rank": "F",
        "class_level": 1,
        "class_level_max": 10,
        "class_xp": 0,
        "class_xp_to_next": 100,
        "affinity_tags": [],
        "description": "",
        "class_traits": [],
        "class_mastery": 0,
        "ascension": {
            "status": "none",
            "quest_id": None,
            "requirements": [],
            "result_hint": None,
        },
    }

def default_injury_state() -> Dict[str, Any]:
    return {
        "id": "",
        "title": "",
        "severity": "leicht",
        "effects": [],
        "healing_stage": "frisch",
        "will_scar": False,
        "created_turn": 0,
        "notes": "",
    }

def default_scar_state() -> Dict[str, Any]:
    return {
        "id": "",
        "title": "",
        "origin_injury_id": None,
        "description": "",
        "created_turn": 0,
    }

def blank_character_state(slot_name: str) -> Dict[str, Any]:
    return {
        "slot_id": slot_name,
        "bio": {
            "name": "",
            "gender": "",
            "age": "",
            "age_years": 0,
            "age_stage": "young",
            "earth_life": "",
            "personality": [],
            "goal": "",
            "isekai_price": "",
            "background_tags": [],
            "strength": "",
            "weakness": "",
            "focus": "",
            "earth_items": [],
            "signature_item": "",
        },
        "scene_id": "",
        "appearance": default_appearance_profile(),
        "appearance_history": [],
        "class_current": None,
        "faction_memberships": [],
        "aging": {
            "arrival_absolute_day": 1,
            "days_since_arrival": 0,
            "last_aged_absolute_day": 1,
            "age_effects_applied": [],
        },
        "modifiers": default_character_modifiers(),
        "resources": {
            "hp": {"current": 10, "base_max": 10, "bonus_max": 0, "max": 10},
            "stamina": {"current": 10, "base_max": 10, "bonus_max": 0, "max": 10},
            "aether": {"current": 5, "base_max": 5, "bonus_max": 0, "max": 5},
            "stress": {"current": 0, "base_max": 10, "bonus_max": 0, "max": 10},
            "corruption": {"current": 0, "base_max": 10, "bonus_max": 0, "max": 10},
            "wounds": {"current": 0, "base_max": 3, "bonus_max": 0, "max": 3},
        },
        "hp_current": 10,
        "hp_max": 10,
        "sta_current": 10,
        "sta_max": 10,
        "res_current": 5,
        "res_max": 5,
        "element_affinities": [],
        "element_resistances": [],
        "element_weaknesses": [],
        "carry_current": 0,
        "carry_max": 10,
        "level": 1,
        "xp_total": 0,
        "xp_current": 0,
        "xp_to_next": 120,
        "recent_progression_events": [],
        "class_path_seeds": [],
        "attributes": {
            "str": 0,
            "dex": 0,
            "con": 0,
            "int": 0,
            "wis": 0,
            "cha": 0,
            "luck": 0,
        },
        "derived": {
            "defense": 10,
            "armor": 0,
            "attack_rating_mainhand": 0,
            "attack_rating_offhand": 0,
            "initiative": 0,
            "carry_limit": 10,
            "carry_weight": 0,
            "encumbrance_state": "normal",
            "age_modifiers": {
                "stage": "young",
                "resource_deltas": {"hp_max": 0, "stamina_max": 0},
                "skill_bonuses": {},
                "notes": [],
            },
            "resistances": {
                "physical": 0,
                "fire": 0,
                "cold": 0,
                "lightning": 0,
                "poison": 0,
                "bleed": 0,
                "shadow": 0,
                "holy": 0,
                "curse": 0,
                "fear": 0,
            },
            "combat_flags": {
                "in_combat": False,
                "downed": False,
                "can_act": True,
            },
        },
        "skills": {},
        "abilities": [],
        "effects": [],
        "inventory": {
            "items": [],
            "quick_slots": {
                "slot_1": "",
                "slot_2": "",
                "slot_3": "",
                "slot_4": "",
            },
        },
        "equipment": {
            "weapon": "",
            "offhand": "",
            "head": "",
            "chest": "",
            "gloves": "",
            "boots": "",
            "amulet": "",
            "ring_1": "",
            "ring_2": "",
            "trinket": "",
        },
        "progression": {
            "rank": 1,
            "xp": 0,
            "next_xp": 100,
            "system_level": 1,
            "system_xp": 0,
            "next_system_xp": 100,
            "resource_name": "Aether",
            "resource_current": 5,
            "resource_max": 5,
            "system_fragments": 0,
            "system_cores": 0,
            "attribute_points": 0,
            "skill_points": 0,
            "talent_points": 0,
            "paths": [],
            "potential_cards": [],
        },
        "injuries": [],
        "scars": [],
        "journal": {
            "notes": [],
            "npc_relationships": [],
            "reputation": [],
            "personal_plotpoints": [],
        },
        # compatibility mirrors for older turns/UI
        "hp": 10,
        "stamina": 10,
        "conditions": [],
        "equip": {"weapon": "", "armor": "", "trinket": ""},
        "potential": [],
    }

def skill_rank_for_level(level: int) -> str:
    normalized = int(level or 0)
    if normalized <= 0:
        return "-"
    for rank, min_level in SKILL_RANK_THRESHOLDS:
        if normalized >= min_level:
            return rank
    return "-"

def next_skill_xp_for_level(level: int) -> int:
    normalized = int(level or 0)
    if normalized <= 0:
        return 60
    return 100 + ((normalized - 1) * 35)

def next_character_xp_for_level(level: int) -> int:
    normalized = max(1, int(level or 1))
    return int(120 + ((normalized - 1) * 60) + (max(0, normalized - 1) ** 1.4) * 14)

def next_class_xp_for_level(level: int) -> int:
    normalized = max(1, int(level or 1))
    return int(100 + ((normalized - 1) * 50) + (max(0, normalized - 1) ** 1.35) * 10)

def default_skill_state(skill_name: str) -> Dict[str, Any]:
    return {
        "id": skill_name,
        "level": 0,
        "xp": 0,
        "next_xp": next_skill_xp_for_level(0),
        "rank": "-",
        "mastery": 0,
        "path": "",
        "evolutions": [],
        "fusion_candidates": [],
        "unlocks": [],
        "awakened": False,
    }

def normalize_skill_state(skill_name: str, value: Any) -> Dict[str, Any]:
    skill = default_skill_state(skill_name)
    if isinstance(value, int):
        skill["level"] = clamp(value if value >= 0 else 0, 0, 20)
    elif isinstance(value, dict):
        skill.update({key: deep_copy(val) for key, val in value.items()})
    skill["id"] = skill_name
    skill["level"] = clamp(int(skill.get("level", 0) or 0), 0, 20)
    skill["next_xp"] = max(1, int(skill.get("next_xp", next_skill_xp_for_level(skill["level"])) or next_skill_xp_for_level(skill["level"])))
    skill["xp"] = clamp(int(skill.get("xp", 0) or 0), 0, skill["next_xp"])
    skill["rank"] = skill_rank_for_level(skill["level"])
    if skill["level"] <= 0:
        skill["mastery"] = 0
    elif skill["level"] >= 20:
        skill["mastery"] = 100
    else:
        skill["mastery"] = clamp(int((skill["xp"] / skill["next_xp"]) * 100), 0, 100)
    skill["path"] = str(skill.get("path", "") or "")
    skill["evolutions"] = list(skill.get("evolutions", []) or [])
    skill["fusion_candidates"] = list(skill.get("fusion_candidates", []) or [])
    skill["unlocks"] = list(skill.get("unlocks", []) or [])
    skill["awakened"] = bool(skill.get("awakened", False))
    skill["path_choice_available"] = bool(skill.get("path_choice_available", False))
    skill["path_options"] = list(skill.get("path_options", []) or [])
    return skill

def ability_id_from_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", normalized_eval_text(name)).strip("-")
    slug = slug[:36] or make_id("ability")
    return f"ability_{slug}"

def next_ability_xp_for_level(level: int) -> int:
    return next_skill_xp_for_level(level)

def default_ability_state(ability_id: str = "", ability_name: str = "") -> Dict[str, Any]:
    return {
        "id": ability_id or ability_id_from_name(ability_name or "faehigkeit"),
        "name": ability_name or "Unbenannte Fähigkeit",
        "owner": "",
        "description": "",
        "type": "active",
        "level": 1,
        "xp": 0,
        "next_xp": next_ability_xp_for_level(1),
        "rank": skill_rank_for_level(1),
        "mastery": 0,
        "charges": 0,
        "max_charges": 0,
        "cooldown_turns": 0,
        "cost": {},
        "tags": [],
        "scaling": {},
        "requirements": [],
        "source": "",
        "active": True,
        "awakened": False,
        "unlocks": [],
        "notes": "",
    }

def normalize_ability_state(value: Any, owner_slot: str = "") -> Dict[str, Any]:
    ability_name = ""
    if isinstance(value, dict):
        ability_name = str(value.get("name", "") or "")
    elif isinstance(value, str):
        ability_name = value
    ability = default_ability_state(ability_name=ability_name)
    if isinstance(value, str):
        ability["name"] = value.strip() or ability["name"]
    elif isinstance(value, dict):
        ability.update({key: deep_copy(val) for key, val in value.items()})

    ability["id"] = str(ability.get("id") or ability_id_from_name(str(ability.get("name", "") or ""))).strip() or ability_id_from_name(str(ability.get("name", "") or "faehigkeit"))
    ability["name"] = str(ability.get("name", "") or "Unbenannte Fähigkeit").strip() or "Unbenannte Fähigkeit"
    ability["owner"] = str(ability.get("owner") or owner_slot or "").strip()
    ability["description"] = str(ability.get("description", "") or "").strip()
    ability["type"] = str(ability.get("type", "active") or "active").strip() or "active"
    ability["level"] = clamp(int(ability.get("level", 1) or 1), 1, 20)
    ability["next_xp"] = max(1, int(ability.get("next_xp", next_ability_xp_for_level(ability["level"])) or next_ability_xp_for_level(ability["level"])))
    ability["xp"] = clamp(int(ability.get("xp", 0) or 0), 0, ability["next_xp"])
    ability["rank"] = skill_rank_for_level(ability["level"])
    if ability["level"] >= 20:
        ability["mastery"] = 100
    else:
        ability["mastery"] = clamp(int((ability["xp"] / ability["next_xp"]) * 100), 0, 100)
    ability["charges"] = max(0, int(ability.get("charges", 0) or 0))
    ability["max_charges"] = max(ability["charges"], int(ability.get("max_charges", 0) or 0))
    ability["cooldown_turns"] = max(0, int(ability.get("cooldown_turns", 0) or 0))
    raw_cost = ability.get("cost") or {}
    ability["cost"] = {
        str(key): int(val or 0)
        for key, val in raw_cost.items()
        if str(key).strip()
    } if isinstance(raw_cost, dict) else {}
    ability["tags"] = [str(entry).strip() for entry in (ability.get("tags") or []) if str(entry).strip()]
    raw_scaling = ability.get("scaling") or {}
    ability["scaling"] = {
        str(key): str(val).strip()
        for key, val in raw_scaling.items()
        if str(key).strip() and str(val).strip()
    } if isinstance(raw_scaling, dict) else {}
    ability["requirements"] = [deep_copy(entry) for entry in (ability.get("requirements") or []) if entry]
    ability["source"] = str(ability.get("source", "") or "").strip()
    ability["active"] = bool(ability.get("active", True))
    ability["awakened"] = bool(ability.get("awakened", False))
    ability["unlocks"] = [str(entry).strip() for entry in (ability.get("unlocks") or []) if str(entry).strip()]
    ability["notes"] = str(ability.get("notes", "") or "").strip()
    return ability

def normalize_resource_name(value: Any, default: str = "Aether") -> str:
    text = str(value or "").strip()
    if not text:
        return default
    text = re.sub(r"\s+", " ", text)
    if len(text) > 24:
        text = text[:24].strip()
    return text or default

def resource_name_for_character(character: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> str:
    progression = character.get("progression", {}) or {}
    resource_name = normalize_resource_name(progression.get("resource_name", ""))
    if resource_name:
        return resource_name
    world_settings = world_settings or {}
    return normalize_resource_name(world_settings.get("resource_name", ""), "Aether")

def skill_id_from_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", normalized_eval_text(name)).strip("_")
    slug = slug[:48] or make_id("skill")
    if not slug.startswith("skill_"):
        slug = f"skill_{slug}"
    return slug

def display_skill_name_from_id(skill_id: str) -> str:
    base = str(skill_id or "").strip()
    if base.startswith("skill_"):
        base = base[6:]
    base = base.replace("_", " ").strip()
    if not base:
        return "Unbenannte Technik"
    return " ".join(part.capitalize() for part in base.split())

def clean_extracted_skill_name(raw_name: str) -> str:
    name = clean_auto_ability_name(raw_name)
    if not name:
        return ""
    name = re.sub(
        r"\s+(?:sowie|und)\s+(?:die\s+technik|den\s+zauber|das\s+ritual|die\s+kunst|die\s+faehigkeit|die\s+fähigkeit)\b.*$",
        "",
        name,
        flags=re.IGNORECASE,
    )
    name = re.sub(r"\s+(?:sowie|und)\b.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+", " ", name).strip(" -")
    return clean_auto_ability_name(name)

def split_extracted_skill_names(raw_name: str) -> List[str]:
    text = str(raw_name or "").strip()
    if not text:
        return []
    parts = re.split(
        r"\s+(?:sowie|und)\s+(?:die\s+technik\s+|den\s+zauber\s+|das\s+ritual\s+|die\s+kunst\s+|die\s+faehigkeit\s+|die\s+fähigkeit\s+)?",
        text,
        flags=re.IGNORECASE,
    )
    names: List[str] = []
    seen = set()
    for part in parts:
        cleaned = clean_extracted_skill_name(part)
        normalized = normalized_eval_text(cleaned)
        if not cleaned or normalized in seen:
            continue
        seen.add(normalized)
        names.append(cleaned)
    return names

def infer_skill_name_from_description(raw_name: str, description: str) -> str:
    base_name = clean_extracted_skill_name(raw_name) or str(raw_name or "").strip()
    base_norm = normalized_eval_text(base_name)
    if not description.strip():
        return base_name
    candidates: List[str] = []
    direct_magic_match = re.search(r"\b([A-ZÄÖÜa-zäöüß][A-Za-zÄÖÜäöüß\-]{2,40}magie)\b", description, flags=re.IGNORECASE)
    if direct_magic_match:
        candidates.extend(split_extracted_skill_names(direct_magic_match.group(1)))
    for explicit_match in re.findall(
        r"(?:technik|zauber|ritual|kunst|fähigkeit|faehigkeit)\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9\- ]{2,60})",
        description,
        flags=re.IGNORECASE,
    ):
        candidates.extend(split_extracted_skill_names(explicit_match))
    for pattern in ABILITY_UNLOCK_TRIGGER_PATTERNS:
        for match in pattern.findall(description):
            candidates.extend(split_extracted_skill_names(match))
    deduped: List[str] = []
    seen = set()
    for candidate in candidates:
        normalized = normalized_eval_text(candidate)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(candidate)
    if not deduped:
        return base_name
    if base_norm:
        related = [
            candidate
            for candidate in deduped
            if normalized_eval_text(candidate).startswith(base_norm) or base_norm.startswith(normalized_eval_text(candidate))
        ]
        if related:
            return max(related, key=len)
    if len(deduped) == 1 and (not base_norm or len(base_norm) <= 9 or base_name.startswith("skill_")):
        return deduped[0]
    return base_name

def normalize_skill_store(skills: Any, *, resource_name: str) -> Dict[str, Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for raw_key, raw_value in (skills or {}).items():
        guessed_name = ""
        description = ""
        if isinstance(raw_value, dict):
            guessed_name = str(raw_value.get("name") or "").strip()
            description = str(raw_value.get("description") or "").strip()
        raw_key_text = str(raw_key or "").strip()
        if not guessed_name:
            guessed_name = display_skill_name_from_id(raw_key_text)
        if guessed_name.startswith("skill_"):
            guessed_name = display_skill_name_from_id(guessed_name)
        guessed_name = infer_skill_name_from_description(guessed_name, description)
        guessed_name = clean_extracted_skill_name(guessed_name) or guessed_name
        normalized_skill = normalize_dynamic_skill_state(
            raw_value,
            skill_id=skill_id_from_name(guessed_name or raw_key_text),
            skill_name=guessed_name or raw_key_text,
            resource_name=resource_name,
            unlocked_from=(raw_value or {}).get("unlocked_from", "Story") if isinstance(raw_value, dict) else "Story",
        )
        normalized_skill["name"] = infer_skill_name_from_description(
            normalized_skill.get("name", ""),
            str(normalized_skill.get("description", "") or ""),
        )
        normalized_skill["name"] = clean_extracted_skill_name(normalized_skill.get("name", "")) or display_skill_name_from_id(normalized_skill["id"])
        normalized_skill["id"] = skill_id_from_name(normalized_skill["name"])
        existing = merged.get(normalized_skill["id"])
        merged[normalized_skill["id"]] = merge_dynamic_skill(existing, normalized_skill, resource_name=resource_name) if existing else normalized_skill
    consolidated: Dict[str, Dict[str, Any]] = {}
    for skill in sorted(merged.values(), key=lambda entry: len(str(entry.get("name", "") or "")), reverse=True):
        skill_name_norm = normalized_eval_text(skill.get("name", ""))
        matched_id = None
        for existing_id, existing_skill in consolidated.items():
            existing_name_norm = normalized_eval_text(existing_skill.get("name", ""))
            if not skill_name_norm or not existing_name_norm:
                continue
            if (
                skill_name_norm == existing_name_norm
                or skill_name_norm.startswith(existing_name_norm)
                or existing_name_norm.startswith(skill_name_norm)
            ):
                matched_id = existing_id
                break
        if matched_id:
            consolidated[matched_id] = merge_dynamic_skill(consolidated[matched_id], skill, resource_name=resource_name)
            consolidated[matched_id]["id"] = skill_id_from_name(consolidated[matched_id]["name"])
        else:
            consolidated[skill["id"]] = skill
    return consolidated

def dynamic_skill_default(skill_id: str = "", skill_name: str = "", resource_name: str = "Aether") -> Dict[str, Any]:
    clean_id = str(skill_id or skill_id_from_name(skill_name or "technik")).strip()
    clean_name = str(skill_name or display_skill_name_from_id(clean_id)).strip()
    return {
        "id": clean_id,
        "name": clean_name or "Unbenannte Technik",
        "rank": "F",
        "level": 1,
        "level_max": DEFAULT_DYNAMIC_SKILL_LEVEL_MAX,
        "tags": [],
        "description": "",
        "effect_summary": "",
        "power_rating": 5,
        "growth_potential": "mittel",
        "manifestation_source": None,
        "category": None,
        "class_affinity": None,
        "elements": [],
        "element_primary": None,
        "element_synergies": None,
        "cost": None,
        "price": None,
        "cooldown_turns": None,
        "unlocked_from": None,
        "synergy_notes": None,
        "xp": 0,
        "next_xp": next_skill_xp_for_level(1),
        "mastery": 0,
    }

def normalize_skill_rank(value: Any) -> str:
    rank = str(value or "F").strip().upper()
    return rank if rank in SKILL_RANKS else "F"

def normalize_dynamic_skill_state(
    value: Any,
    *,
    skill_id: str = "",
    skill_name: str = "",
    resource_name: str = "Aether",
    unlocked_from: Optional[str] = None,
) -> Dict[str, Any]:
    if isinstance(value, int):
        payload: Dict[str, Any] = {"level": value}
    elif isinstance(value, str):
        payload = {"name": value}
    elif isinstance(value, dict):
        payload = deep_copy(value)
    else:
        payload = {}
    payload_name = str(payload.get("name") or "").strip()
    provided_name = str(skill_name or "").strip()
    fallback_name = str(payload_name or provided_name or display_skill_name_from_id(skill_id) or "Unbenannte Technik").strip()
    if provided_name:
        payload_name_norm = normalized_eval_text(payload_name)
        provided_name_norm = normalized_eval_text(provided_name)
        if (
            not payload_name
            or payload_name.startswith("skill_")
            or (
                payload_name_norm
                and provided_name_norm
                and (
                    provided_name_norm.startswith(payload_name_norm)
                    or payload_name_norm.startswith(provided_name_norm)
                )
                and len(provided_name) > len(payload_name)
            )
        ):
            fallback_name = provided_name
    if fallback_name.startswith("skill_"):
        fallback_name = display_skill_name_from_id(fallback_name)
    fallback_name = clean_extracted_skill_name(fallback_name) or fallback_name
    fallback_id = str(payload.get("id") or skill_id or skill_id_from_name(fallback_name)).strip()
    skill = dynamic_skill_default(fallback_id, fallback_name, resource_name)
    skill.update(payload)
    skill_name_value = str(skill.get("name") or fallback_name).strip() or fallback_name
    fallback_name_norm = normalized_eval_text(fallback_name)
    skill_name_norm = normalized_eval_text(skill_name_value)
    if (
        fallback_name
        and skill_name_value
        and (
            fallback_name_norm.startswith(skill_name_norm)
            or skill_name_norm.startswith(fallback_name_norm)
        )
        and len(fallback_name) > len(skill_name_value)
    ):
        skill_name_value = fallback_name
    if skill_name_value.startswith("skill_") or normalized_eval_text(skill_name_value) == normalized_eval_text(str(skill.get("id") or fallback_id)):
        skill_name_value = display_skill_name_from_id(str(skill.get("id") or fallback_id))
    skill_name_value = clean_extracted_skill_name(skill_name_value) or skill_name_value
    skill["name"] = skill_name_value
    skill["id"] = skill_id_from_name(skill_name_value or fallback_name)
    skill["rank"] = normalize_skill_rank(skill.get("rank"))
    skill["level_max"] = clamp(
        int(skill.get("level_max", DEFAULT_DYNAMIC_SKILL_LEVEL_MAX) or DEFAULT_DYNAMIC_SKILL_LEVEL_MAX),
        1,
        DEFAULT_DYNAMIC_SKILL_LEVEL_MAX,
    )
    skill["level"] = clamp(int(skill.get("level", 1) or 1), 1, skill["level_max"])
    skill["tags"] = [str(tag).strip() for tag in (skill.get("tags") or []) if str(tag).strip()]
    skill["description"] = str(skill.get("description", "") or "").strip() or f"{skill['name']} ist Teil der aktuellen Entwicklung."
    skill["effect_summary"] = str(skill.get("effect_summary", "") or "").strip() or skill["description"][:180]
    skill["growth_potential"] = str(skill.get("growth_potential", "") or "mittel").strip().lower() or "mittel"
    if skill["growth_potential"] not in {"niedrig", "mittel", "hoch", "legendär"}:
        skill["growth_potential"] = "mittel"
    skill["power_rating"] = clamp(
        int(
            skill.get(
                "power_rating",
                max(1, (skill_rank_sort_value(skill["rank"]) + 1) * 5 + int(skill.get("level", 1) or 1)),
            )
            or 1
        ),
        1,
        999,
    )
    manifestation_source = str(skill.get("manifestation_source", "") or "").strip()
    skill["manifestation_source"] = manifestation_source or None
    category = str(skill.get("category", "") or "").strip().lower()
    skill["category"] = category or None
    class_affinity = [str(tag).strip() for tag in (skill.get("class_affinity") or []) if str(tag).strip()]
    skill["class_affinity"] = class_affinity or None
    skill["elements"] = list(dict.fromkeys([str(tag).strip() for tag in (skill.get("elements") or []) if str(tag).strip()]))
    element_primary = str(skill.get("element_primary") or "").strip()
    if element_primary and element_primary not in skill["elements"]:
        skill["elements"].insert(0, element_primary)
    skill["element_primary"] = element_primary or (skill["elements"][0] if skill["elements"] else None)
    element_synergies = [str(tag).strip() for tag in (skill.get("element_synergies") or []) if str(tag).strip()]
    skill["element_synergies"] = list(dict.fromkeys(element_synergies)) or None
    raw_cost = skill.get("cost")
    if isinstance(raw_cost, dict):
        cost_resource = str(raw_cost.get("resource") or resource_name).strip() or resource_name
        amount = max(0, int(raw_cost.get("amount", 0) or 0))
        skill["cost"] = {"resource": cost_resource, "amount": amount}
    else:
        skill["cost"] = None
    skill["price"] = str(skill.get("price", "") or "").strip() or None
    cooldown = skill.get("cooldown_turns")
    skill["cooldown_turns"] = None if cooldown in (None, "", False) else max(0, int(cooldown or 0))
    skill["unlocked_from"] = str(skill.get("unlocked_from") or unlocked_from or "Story").strip() or "Story"
    skill["synergy_notes"] = str(skill.get("synergy_notes", "") or "").strip() or None
    skill["xp"] = max(0, int(skill.get("xp", 0) or 0))
    skill["next_xp"] = max(1, int(skill.get("next_xp", next_skill_xp_for_level(skill["level"])) or next_skill_xp_for_level(skill["level"])))
    if skill["xp"] > skill["next_xp"]:
        skill["xp"] = skill["next_xp"]
    skill["mastery"] = clamp(int(skill.get("mastery", int((skill["xp"] / max(skill["next_xp"], 1)) * 100)) or 0), 0, 100)
    return skill

def merge_dynamic_skill(existing: Dict[str, Any], incoming: Dict[str, Any], *, resource_name: str) -> Dict[str, Any]:
    base = normalize_dynamic_skill_state(existing, resource_name=resource_name)
    new_data = normalize_dynamic_skill_state(
        incoming,
        skill_id=str(incoming.get("id") or base.get("id") or ""),
        skill_name=str(incoming.get("name") or base.get("name") or ""),
        resource_name=resource_name,
        unlocked_from=str(incoming.get("unlocked_from") or base.get("unlocked_from") or "Story"),
    )
    base_name_norm = normalized_eval_text(base.get("name", ""))
    new_name_norm = normalized_eval_text(new_data.get("name", ""))
    if new_data.get("name"):
        if not base.get("name"):
            base["name"] = new_data["name"]
        elif base_name_norm == new_name_norm:
            base["name"] = new_data["name"] if len(new_data["name"]) >= len(base["name"]) else base["name"]
        elif base_name_norm.startswith(new_name_norm) or new_name_norm.startswith(base_name_norm):
            base["name"] = new_data["name"] if len(new_data["name"]) >= len(base["name"]) else base["name"]
        else:
            base["name"] = new_data["name"]
    base["rank"] = new_data["rank"] if new_data["rank"] != "F" or base.get("rank") == "F" else base["rank"]
    base["level"] = max(int(base.get("level", 1) or 1), int(new_data.get("level", 1) or 1))
    base["level_max"] = max(int(base.get("level_max", 10) or 10), int(new_data.get("level_max", 10) or 10))
    base["tags"] = list(dict.fromkeys([*(base.get("tags") or []), *(new_data.get("tags") or [])]))
    if new_data.get("description"):
        base["description"] = new_data["description"]
    if new_data.get("effect_summary"):
        base["effect_summary"] = new_data["effect_summary"]
    if new_data.get("growth_potential"):
        base["growth_potential"] = new_data["growth_potential"]
    if int(new_data.get("power_rating", 0) or 0) > 0:
        base["power_rating"] = max(int(base.get("power_rating", 1) or 1), int(new_data.get("power_rating", 1) or 1))
    if new_data.get("manifestation_source"):
        base["manifestation_source"] = new_data["manifestation_source"]
    if new_data.get("category"):
        base["category"] = new_data["category"]
    if new_data.get("class_affinity"):
        base["class_affinity"] = list(dict.fromkeys([*(base.get("class_affinity") or []), *(new_data.get("class_affinity") or [])]))
    if new_data.get("elements"):
        base["elements"] = list(dict.fromkeys([*(base.get("elements") or []), *(new_data.get("elements") or [])]))
    if new_data.get("element_primary"):
        base["element_primary"] = new_data.get("element_primary")
        if base["element_primary"] and base["element_primary"] not in (base.get("elements") or []):
            base["elements"] = [base["element_primary"], *(base.get("elements") or [])]
    if new_data.get("element_synergies"):
        base["element_synergies"] = list(dict.fromkeys([*(base.get("element_synergies") or []), *(new_data.get("element_synergies") or [])]))
    if new_data.get("cost"):
        base["cost"] = new_data["cost"]
    if new_data.get("price"):
        base["price"] = new_data["price"]
    if new_data.get("cooldown_turns") is not None:
        base["cooldown_turns"] = new_data["cooldown_turns"]
    if new_data.get("synergy_notes"):
        base["synergy_notes"] = new_data["synergy_notes"]
    if new_data.get("unlocked_from"):
        base["unlocked_from"] = new_data["unlocked_from"]
    base["xp"] = max(int(base.get("xp", 0) or 0), int(new_data.get("xp", 0) or 0))
    base["next_xp"] = max(int(base.get("next_xp", 1) or 1), int(new_data.get("next_xp", 1) or 1))
    base["mastery"] = clamp(int(base.get("mastery", 0) or 0), 0, 100)
    return normalize_dynamic_skill_state(base, resource_name=resource_name)

def skill_rank_sort_value(rank: str) -> int:
    return SKILL_RANK_ORDER.get(str(rank or "F").upper(), -1)

def extract_skill_entries_for_character(character: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    resource_name = resource_name_for_character(character, world_settings)
    normalized: Dict[str, Any] = {}
    raw_skills = character.get("skills", {}) or {}
    for raw_key, raw_value in raw_skills.items():
        if raw_key in SKILL_KEYS:
            legacy = normalize_skill_state(raw_key, raw_value)
            if int(legacy.get("level", 0) or 0) <= 0:
                continue
            normalized[skill_id_from_name(LEGACY_SKILL_NAME_MAP.get(raw_key, skill_display_name(raw_key)))] = normalize_dynamic_skill_state(
                {
                    "id": skill_id_from_name(LEGACY_SKILL_NAME_MAP.get(raw_key, skill_display_name(raw_key))),
                    "name": LEGACY_SKILL_NAME_MAP.get(raw_key, skill_display_name(raw_key)),
                    "rank": normalize_skill_rank(legacy.get("rank")),
                    "level": max(1, int(legacy.get("level", 1) or 1)),
                    "level_max": 10,
                    "tags": LEGACY_SKILL_TAGS.get(raw_key, []),
                    "description": f"{LEGACY_SKILL_NAME_MAP.get(raw_key, skill_display_name(raw_key))} stammt aus einem älteren Spielstand.",
                    "cost": None,
                    "price": None,
                    "cooldown_turns": None,
                    "unlocked_from": "Legacy",
                    "synergy_notes": None,
                    "xp": int(legacy.get("xp", 0) or 0),
                    "next_xp": int(legacy.get("next_xp", next_skill_xp_for_level(max(1, int(legacy.get('level', 1) or 1)))) or next_skill_xp_for_level(max(1, int(legacy.get('level', 1) or 1)))),
                    "mastery": int(legacy.get("mastery", 0) or 0),
                },
                resource_name=resource_name,
            )
            continue
        skill = normalize_dynamic_skill_state(raw_value, skill_id=str(raw_key), skill_name=str((raw_value or {}).get("name") or raw_key), resource_name=resource_name)
        normalized[skill["id"]] = skill

    for ability in (character.get("abilities") or []):
        legacy_ability = normalize_ability_state(ability, str(character.get("slot_id", "") or ""))
        skill = normalize_dynamic_skill_state(
            {
                "id": skill_id_from_name(legacy_ability.get("name", legacy_ability.get("id", ""))),
                "name": legacy_ability.get("name"),
                "rank": normalize_skill_rank(legacy_ability.get("rank")),
                "level": max(1, int(legacy_ability.get("level", 1) or 1)),
                "level_max": 10,
                "tags": list(dict.fromkeys([*(legacy_ability.get("tags") or []), legacy_ability.get("type", "")])),
                "description": legacy_ability.get("description") or legacy_ability.get("notes") or f"{legacy_ability.get('name', 'Technik')} wurde aus einer älteren Fähigkeit migriert.",
                "cost": None if not legacy_ability.get("cost") else {"resource": resource_name, "amount": sum(int(v or 0) for v in (legacy_ability.get("cost") or {}).values())},
                "price": None,
                "cooldown_turns": legacy_ability.get("cooldown_turns"),
                "unlocked_from": legacy_ability.get("source") or "Legacy",
                "synergy_notes": None,
                "xp": int(legacy_ability.get("xp", 0) or 0),
                "next_xp": int(legacy_ability.get("next_xp", next_skill_xp_for_level(max(1, int(legacy_ability.get('level', 1) or 1)))) or next_skill_xp_for_level(max(1, int(legacy_ability.get('level', 1) or 1)))),
                "mastery": int(legacy_ability.get("mastery", 0) or 0),
            },
            resource_name=resource_name,
        )
        current = normalized.get(skill["id"])
        normalized[skill["id"]] = merge_dynamic_skill(current, skill, resource_name=resource_name) if current else skill
    return normalized

def build_skill_fusion_hints(skills: Dict[str, Any], *, resource_name: str) -> List[Dict[str, Any]]:
    entries = [
        normalize_dynamic_skill_state(
            value,
            skill_id=skill_id,
            skill_name=(value or {}).get("name", skill_id),
            resource_name=resource_name,
        )
        for skill_id, value in (skills or {}).items()
    ]
    maxed = [entry for entry in entries if int(entry.get("level", 1) or 1) >= int(entry.get("level_max", 10) or 10)]
    hints: List[Dict[str, Any]] = []
    for index, left in enumerate(maxed):
        left_tags = {normalized_eval_text(tag) for tag in (left.get("tags") or []) if normalized_eval_text(tag)}
        for right in maxed[index + 1 :]:
            right_tags = {normalized_eval_text(tag) for tag in (right.get("tags") or []) if normalized_eval_text(tag)}
            overlap = sorted(left_tags & right_tags)
            if not overlap:
                continue
            result_rank = left["rank"] if skill_rank_sort_value(left["rank"]) >= skill_rank_sort_value(right["rank"]) else right["rank"]
            hints.append(
                {
                    "with_id": right["id"],
                    "with_name": right["name"],
                    "tags_overlap": overlap,
                    "result_rank": result_rank,
                    "label": f"Fusion möglich: {left['name']} + {right['name']}",
                }
            )
    return hints

def skill_display_name(skill_name: str) -> str:
    return skill_name.replace("_", " ").title()

def skill_level_value(character: Dict[str, Any], skill_name: str) -> int:
    skills = character.get("skills", {}) or {}
    if skill_name in skills:
        raw_value = skills.get(skill_name)
        if isinstance(raw_value, dict) and "level" in raw_value:
            return int(raw_value.get("level", 0) or 0)
    for entry in skills.values():
        if not isinstance(entry, dict):
            continue
        if normalized_eval_text(entry.get("name", "")) == normalized_eval_text(skill_name):
            return int(entry.get("level", 0) or 0)
    legacy = normalize_skill_state(skill_name, skills.get(skill_name, default_skill_state(skill_name)))
    return int(legacy.get("level", 0) or 0)

def role_key(role_text: str) -> str:
    normalized = normalized_eval_text(role_text)
    if "frontline" in normalized:
        return "frontline"
    if "scout" in normalized or "späher" in normalized or "spaeher" in normalized:
        return "scout"
    if "face" in normalized:
        return "face"
    if "support" in normalized:
        return "support"
    if "occult" in normalized or "flüche" in normalized or "flueche" in normalized:
        return "occult"
    if "tüftler" in normalized or "tueftler" in normalized:
        return "tueftler"
    return ""

def class_rank_sort_value(rank: str) -> int:
    return SKILL_RANK_ORDER.get(str(rank or "F").upper(), -1)

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

def normalize_injury_state(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    injury = default_injury_state()
    injury.update(deep_copy(value))
    injury["id"] = str(injury.get("id") or make_id("inj")).strip()
    injury["title"] = str(injury.get("title") or "").strip()
    if not injury["title"]:
        return None
    injury["severity"] = str(injury.get("severity") or "leicht").strip().lower()
    if injury["severity"] not in INJURY_SEVERITIES:
        injury["severity"] = "leicht"
    injury["effects"] = [str(entry).strip() for entry in (injury.get("effects") or []) if str(entry).strip()]
    injury["healing_stage"] = str(injury.get("healing_stage") or "frisch").strip().lower()
    if injury["healing_stage"] not in INJURY_HEALING_STAGES:
        injury["healing_stage"] = "frisch"
    injury["will_scar"] = bool(injury.get("will_scar", False))
    injury["created_turn"] = max(0, int(injury.get("created_turn", 0) or 0))
    injury["notes"] = str(injury.get("notes") or "").strip()
    return injury

def normalize_scar_state(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    scar = default_scar_state()
    scar.update(deep_copy(value))
    scar["id"] = str(scar.get("id") or make_id("scar")).strip()
    scar["title"] = str(scar.get("title") or scar.get("label") or "").strip()
    if not scar["title"]:
        return None
    scar["origin_injury_id"] = str(scar.get("origin_injury_id") or "").strip() or None
    scar["description"] = str(scar.get("description") or scar.get("source") or scar["title"]).strip()
    scar["created_turn"] = max(0, int(scar.get("created_turn") or scar.get("turn_number") or 0))
    return scar

def migrate_legacy_role_to_class(role_text: str) -> Optional[Dict[str, Any]]:
    template = LEGACY_ROLE_CLASS_MAP.get(role_key(role_text))
    if not template:
        return None
    payload = default_class_current()
    payload.update(deep_copy(template))
    return normalize_class_current(payload)

def class_affinity_match(skill_tags: List[str], class_affinity_tags: List[str]) -> bool:
    skill_set = {normalized_eval_text(tag) for tag in (skill_tags or []) if normalized_eval_text(tag)}
    class_set = {normalized_eval_text(tag) for tag in (class_affinity_tags or []) if normalized_eval_text(tag)}
    return bool(skill_set & class_set)

def sentence_mentions_actor_name(sentence: str, actor_display: str) -> bool:
    normalized_sentence = normalized_eval_text(sentence)
    actor_name = normalized_eval_text(actor_display)
    if not normalized_sentence or not actor_name:
        return False
    if actor_name in normalized_sentence:
        return True
    actor_tokens = [token for token in actor_name.split() if len(token) >= 4]
    sentence_tokens = [token.strip(".,:;!?()[]{}\"'") for token in normalized_sentence.split() if len(token.strip(".,:;!?()[]{}\"'")) >= 4]
    for actor_token in actor_tokens[:2]:
        for sentence_token in sentence_tokens[:4]:
            if sentence_token.startswith(actor_token) or actor_token.startswith(sentence_token):
                return True
            if SequenceMatcher(None, actor_token, sentence_token).ratio() >= 0.72:
                return True
    return False

def effective_skill_progress_multiplier(character: Dict[str, Any], skill: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> float:
    world_settings = world_settings or {}
    current_class = normalize_class_current(character.get("class_current"))
    if not current_class:
        return float(world_settings.get("onclass_xp_multiplier", 1.0) or 1.0)
    if class_affinity_match(skill.get("tags") or [], current_class.get("affinity_tags") or []):
        return float(world_settings.get("onclass_xp_multiplier", 1.0) or 1.0)
    return float(world_settings.get("offclass_xp_multiplier", 0.7) or 0.7)

def setup_question_is_applicable(setup_node: Dict[str, Any], question_id: str) -> bool:
    if question_id not in CHARACTER_QUESTION_MAP:
        return True
    answers = setup_node.get("answers", {}) or {}
    class_start_mode = normalized_eval_text(extract_text_answer(answers.get("class_start_mode")))
    if not class_start_mode:
        return True
    if question_id == "class_seed":
        return "ki" in class_start_mode
    if question_id in {"class_custom_name", "class_custom_description", "class_custom_tags"}:
        return "selbst" in class_start_mode
    return True

def canonical_resource_field_name(raw_name: Any) -> str:
    normalized = normalized_eval_text(raw_name)
    if normalized in {"hp", "health", "leben", "lebenspunkte"}:
        return "hp"
    if normalized in {"sta", "stamina", "ausdauer"}:
        return "stamina"
    if normalized in {"res", "resource", "mana", "aether", "äther", "qi", "ki", "energie"}:
        return "aether"
    if normalized in {"stress"}:
        return "stress"
    if normalized in {"corruption", "verderbnis"}:
        return "corruption"
    if normalized in {"wounds", "wound", "wunde", "wunden"}:
        return "wounds"
    return ""

def ingest_legacy_resources_into_canonical(
    character: Dict[str, Any],
    world_settings: Optional[Dict[str, Any]] = None,
    *,
    source_character: Optional[Dict[str, Any]] = None,
) -> None:
    source = source_character if isinstance(source_character, dict) else character
    resources = source.get("resources", {}) if isinstance(source.get("resources"), dict) else {}
    progression = character.setdefault("progression", {})
    resource_label = normalize_resource_name(
        ((world_settings or {}).get("resource_name")) or progression.get("resource_name") or "Aether",
        "Aether",
    )
    hp_res = resources.get("hp") or {}
    sta_res = resources.get("stamina") or {}
    legacy_res = resources.get("aether") or {}
    if not legacy_res:
        dynamic_key = re.sub(r"[^a-z0-9]+", "_", normalized_eval_text(resource_label)).strip("_")
        if dynamic_key:
            legacy_res = resources.get(dynamic_key) or {}

    if "hp_max" not in source:
        character["hp_max"] = max(1, int(hp_res.get("max", 10) or 10))
    if "hp_current" not in source:
        default_hp_current = hp_res.get("current", character.get("hp_max", 10))
        character["hp_current"] = max(0, int(default_hp_current or 0))
    if "sta_max" not in source:
        character["sta_max"] = max(0, int(sta_res.get("max", 10) or 10))
    if "sta_current" not in source:
        default_sta_current = sta_res.get("current", character.get("sta_max", 10))
        character["sta_current"] = max(0, int(default_sta_current or 0))
    if "res_max" not in source:
        default_res_max = legacy_res.get("max", progression.get("resource_max", 5))
        character["res_max"] = max(0, int(default_res_max or 5))
    if "res_current" not in source:
        default_res_current = legacy_res.get("current", progression.get("resource_current", character.get("res_max", 5)))
        character["res_current"] = max(0, int(default_res_current or 0))
    if "carry_max" not in source:
        carry_limit = int(((character.get("derived") or {}).get("carry_limit", 10)) or 10)
        character["carry_max"] = max(0, carry_limit)
    if "carry_current" not in source:
        carry_weight = int(((character.get("derived") or {}).get("carry_weight", 0)) or 0)
        character["carry_current"] = max(0, carry_weight)
    if "hp" in source and "hp_current" not in source and not isinstance(resources.get("hp"), dict):
        character["hp_current"] = max(0, int(character.get("hp", 0) or 0))
    if "stamina" in source and "sta_current" not in source and not isinstance(resources.get("stamina"), dict):
        character["sta_current"] = max(0, int(character.get("stamina", 0) or 0))
    progression["resource_name"] = resource_label

def reconcile_canonical_resources(character: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> None:
    progression = character.setdefault("progression", {})
    resource_label = normalize_resource_name(
        ((world_settings or {}).get("resource_name")) or progression.get("resource_name") or "Aether",
        "Aether",
    )
    character["hp_max"] = max(1, int(character.get("hp_max", 10) or 10))
    character["hp_current"] = clamp(int(character.get("hp_current", character["hp_max"]) or character["hp_max"]), 0, character["hp_max"])
    character["sta_max"] = max(0, int(character.get("sta_max", 10) or 10))
    character["sta_current"] = clamp(int(character.get("sta_current", character["sta_max"]) or character["sta_max"]), 0, character["sta_max"])
    character["res_max"] = max(0, int(character.get("res_max", 5) or 5))
    character["res_current"] = clamp(int(character.get("res_current", character["res_max"]) or character["res_max"]), 0, character["res_max"])
    character["carry_max"] = max(0, int(character.get("carry_max", 10) or 10))
    character["carry_current"] = clamp(int(character.get("carry_current", 0) or 0), 0, character["carry_max"])
    progression["resource_name"] = resource_label
    progression["resource_current"] = int(character.get("res_current", 0) or 0)
    progression["resource_max"] = int(character.get("res_max", 0) or 0)
    character.setdefault("derived", {})["carry_limit"] = int(character["carry_max"])
    character.setdefault("derived", {})["carry_weight"] = int(character["carry_current"])

def build_compat_resources_view(character: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, int]]:
    resource_label = resource_name_for_character(character, world_settings)
    resource_key = re.sub(r"[^a-z0-9]+", "_", normalized_eval_text(resource_label)).strip("_") or "resource"
    hp_max = max(1, int(character.get("hp_max", 10) or 10))
    sta_max = max(0, int(character.get("sta_max", 10) or 10))
    res_max = max(0, int(character.get("res_max", 5) or 5))
    hp_payload = {"current": clamp(int(character.get("hp_current", hp_max) or hp_max), 0, hp_max), "base_max": hp_max, "bonus_max": 0, "max": hp_max}
    sta_payload = {"current": clamp(int(character.get("sta_current", sta_max) or sta_max), 0, sta_max), "base_max": sta_max, "bonus_max": 0, "max": sta_max}
    res_payload = {"current": clamp(int(character.get("res_current", res_max) or res_max), 0, res_max), "base_max": res_max, "bonus_max": 0, "max": res_max}
    view = {
        "hp": dict(hp_payload),
        "stamina": dict(sta_payload),
        "aether": dict(res_payload),
    }
    view[resource_key] = dict(res_payload)
    for key in ("stress", "corruption", "wounds"):
        raw = ((character.get("resources") or {}).get(key) or {}) if isinstance(character.get("resources"), dict) else {}
        fallback_max = 10 if key != "wounds" else 3
        entry_max = max(0, int(raw.get("max", fallback_max) or fallback_max))
        view[key] = {
            "current": clamp(int(raw.get("current", 0) or 0), 0, entry_max),
            "base_max": max(0, int(raw.get("base_max", entry_max) or entry_max)),
            "bonus_max": int(raw.get("bonus_max", 0) or 0),
            "max": entry_max,
        }
    return view

def strip_legacy_resource_shadows(character: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> None:
    if ENABLE_LEGACY_SHADOW_WRITEBACK:
        return
    resources = character.get("resources")
    if not isinstance(resources, dict):
        return
    resource_label = resource_name_for_character(character, world_settings)
    dynamic_key = re.sub(r"[^a-z0-9]+", "_", normalized_eval_text(resource_label)).strip("_")
    for key in ("hp", "stamina", "aether", dynamic_key):
        if key and key in resources and key not in {"stress", "corruption", "wounds"}:
            resources.pop(key, None)

def strip_legacy_shadow_fields(character: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> None:
    if ENABLE_LEGACY_SHADOW_WRITEBACK:
        return
    strip_legacy_resource_shadows(character, world_settings)
    for field_name in ("hp", "stamina", "equip", "abilities", "potential", "class_state"):
        character.pop(field_name, None)

def legacy_misc_resources_set_from_payload(resources_set_payload: Any) -> Dict[str, Dict[str, int]]:
    out: Dict[str, Dict[str, int]] = {}
    if not isinstance(resources_set_payload, dict):
        return out
    for raw_key, raw_value in resources_set_payload.items():
        mapped = canonical_resource_field_name(raw_key)
        if mapped not in {"stress", "corruption", "wounds"}:
            continue
        if not isinstance(raw_value, dict):
            continue
        entry = {
            "current": max(0, int(raw_value.get("current", 0) or 0)),
            "max": max(0, int(raw_value.get("max", 0) or 0)),
        }
        if entry["max"] > 0:
            entry["current"] = clamp(entry["current"], 0, entry["max"])
        out[mapped] = entry
    return out

def legacy_misc_resource_deltas_from_update(upd: Dict[str, Any]) -> Dict[str, int]:
    out = {"stress": 0, "corruption": 0, "wounds": 0}
    raw_deltas = upd.get("resources_delta") if isinstance(upd.get("resources_delta"), dict) else {}
    for raw_key, raw_value in raw_deltas.items():
        mapped = canonical_resource_field_name(raw_key)
        if mapped in out:
            out[mapped] += int(raw_value or 0)
    return out

def write_legacy_shadow_fields(character: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> None:
    resources_view = build_compat_resources_view(character, world_settings)
    character["resources"] = deep_copy(resources_view)
    character["hp"] = int(character.get("hp_current", 0) or 0)
    character["stamina"] = int(character.get("sta_current", 0) or 0)
    character["equip"] = {
        "weapon": ((character.get("equipment") or {}).get("weapon", "") if isinstance(character.get("equipment"), dict) else ""),
        "armor": ((character.get("equipment") or {}).get("chest", "") if isinstance(character.get("equipment"), dict) else ""),
        "trinket": ((character.get("equipment") or {}).get("trinket", "") if isinstance(character.get("equipment"), dict) else ""),
    }
    character["potential"] = [
        card.get("name", card.get("id", ""))
        for card in (character.get("progression", {}).get("potential_cards") or [])
        if isinstance(card, dict)
    ]

def sync_canonical_resources(character: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> None:
    # Backward-compatible wrapper: canonical-first by default, optional legacy shadow writeback.
    ingest_legacy_resources_into_canonical(character, world_settings)
    reconcile_canonical_resources(character, world_settings)
    if ENABLE_LEGACY_SHADOW_WRITEBACK:
        write_legacy_shadow_fields(character, world_settings)
    else:
        strip_legacy_shadow_fields(character, world_settings)

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

def default_boards(player_id: Optional[str] = None) -> Dict[str, Any]:
    now = utc_now()
    return {
        "plot_essentials": {
            "premise": "",
            "current_goal": "",
            "current_threat": "",
            "active_scene": "",
            "open_loops": [],
            "tone": "",
            "updated_at": now,
            "updated_by": player_id,
        },
        "authors_note": {
            "content": "",
            "updated_at": now,
            "updated_by": player_id,
        },
        "story_cards": [],
        "world_info": [],
        "memory_summary": {
            "content": "Noch keine Zusammenfassung vorhanden.",
            "updated_through_turn": 0,
            "updated_at": now,
        },
        "player_diaries": {},
    }

def resource_delta_payload() -> Dict[str, int]:
    return {key: 0 for key in RESOURCE_KEYS}

def canonical_resources_set_from_payload(
    resources_set_payload: Any,
    character: Dict[str, Any],
    world_settings: Optional[Dict[str, Any]] = None,
) -> Dict[str, int]:
    canonical: Dict[str, int] = {}
    if not isinstance(resources_set_payload, dict):
        return canonical
    for key in ("hp_current", "hp_max", "sta_current", "sta_max", "res_current", "res_max", "carry_current", "carry_max"):
        if key in resources_set_payload:
            canonical[key] = max(0, int(resources_set_payload.get(key, 0) or 0))
    for raw_key, raw_value in resources_set_payload.items():
        mapped = canonical_resource_field_name(raw_key)
        if not mapped:
            continue
        if isinstance(raw_value, dict):
            if mapped == "hp":
                if "current" in raw_value:
                    canonical["hp_current"] = max(0, int(raw_value.get("current", 0) or 0))
                if "max" in raw_value:
                    canonical["hp_max"] = max(1, int(raw_value.get("max", 0) or 0))
            elif mapped == "stamina":
                if "current" in raw_value:
                    canonical["sta_current"] = max(0, int(raw_value.get("current", 0) or 0))
                if "max" in raw_value:
                    canonical["sta_max"] = max(0, int(raw_value.get("max", 0) or 0))
            elif mapped == "aether":
                if "current" in raw_value:
                    canonical["res_current"] = max(0, int(raw_value.get("current", 0) or 0))
                if "max" in raw_value:
                    canonical["res_max"] = max(0, int(raw_value.get("max", 0) or 0))
        else:
            numeric = max(0, int(raw_value or 0))
            if mapped == "hp":
                canonical.setdefault("hp_current", numeric)
            elif mapped == "stamina":
                canonical.setdefault("sta_current", numeric)
            elif mapped == "aether":
                canonical.setdefault("res_current", numeric)
    if "res_max" in canonical and "res_current" in canonical:
        canonical["res_current"] = clamp(canonical["res_current"], 0, canonical["res_max"])
    if "hp_max" in canonical and "hp_current" in canonical:
        canonical["hp_current"] = clamp(canonical["hp_current"], 0, max(1, canonical["hp_max"]))
    if "sta_max" in canonical and "sta_current" in canonical:
        canonical["sta_current"] = clamp(canonical["sta_current"], 0, max(0, canonical["sta_max"]))
    return canonical

def canonical_resource_deltas_from_update(upd: Dict[str, Any]) -> Dict[str, int]:
    deltas = {"hp_current": 0, "sta_current": 0, "res_current": 0, "carry_current": 0}
    deltas["hp_current"] += int(upd.get("hp_delta", 0) or 0)
    deltas["sta_current"] += int(upd.get("stamina_delta", 0) or 0)
    raw_deltas = upd.get("resources_delta") if isinstance(upd.get("resources_delta"), dict) else {}
    for raw_key, raw_value in raw_deltas.items():
        mapped = canonical_resource_field_name(raw_key)
        if mapped == "hp":
            deltas["hp_current"] += int(raw_value or 0)
        elif mapped == "stamina":
            deltas["sta_current"] += int(raw_value or 0)
        elif mapped == "aether":
            deltas["res_current"] += int(raw_value or 0)
        elif str(raw_key or "").strip().lower() == "carry":
            deltas["carry_current"] += int(raw_value or 0)
    return deltas

def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))

def normalize_world_time(meta: Dict[str, Any]) -> Dict[str, Any]:
    world_time = deep_copy(meta.get("world_time") or default_world_time())
    absolute_day = max(1, int(world_time.get("absolute_day", world_time.get("day", 1)) or 1))
    year = ((absolute_day - 1) // 360) + 1
    year_day = (absolute_day - 1) % 360
    month = (year_day // 30) + 1
    day = (year_day % 30) + 1
    world_time["absolute_day"] = absolute_day
    world_time["year"] = max(1, int(world_time.get("year", year) or year))
    world_time["month"] = max(1, min(12, int(world_time.get("month", month) or month)))
    world_time["day"] = max(1, min(30, int(world_time.get("day", day) or day)))
    world_time["year"] = year
    world_time["month"] = month
    world_time["day"] = day
    world_time["time_of_day"] = str(world_time.get("time_of_day", "night") or "night")
    world_time["weather"] = str(world_time.get("weather", "") or "")
    return world_time

def infer_age_years(age_text: str) -> int:
    text = normalized_eval_text(age_text)
    if not text:
        return 22
    explicit = re.search(r"\b(\d{1,3})\b", str(age_text))
    if explicit:
        return max(12, min(90, int(explicit.group(1))))
    if "teen" in text:
        return 18
    if "jung" in text or "young" in text:
        return 22
    if "erwachsen" in text or "adult" in text:
        return 30
    if "alter" in text or "älter" in text or "aelter" in text or "older" in text:
        return 42
    return 22

def derive_age_stage(age_years: int) -> str:
    if age_years <= 19:
        return "teen"
    if age_years <= 29:
        return "young"
    if age_years <= 44:
        return "adult"
    return "older"

def normalize_appearance_state(character: Dict[str, Any]) -> Dict[str, Any]:
    appearance = deep_copy(default_appearance_profile())
    appearance.update(character.get("appearance", {}) or {})
    appearance["eyes"] = {**default_appearance_profile()["eyes"], **(appearance.get("eyes") or {})}
    appearance["hair"] = {**default_appearance_profile()["hair"], **(appearance.get("hair") or {})}
    appearance["skin_marks"] = [str(entry) for entry in (appearance.get("skin_marks") or []) if str(entry).strip()]
    appearance["visual_modifiers"] = [deep_copy(entry) for entry in (appearance.get("visual_modifiers") or []) if isinstance(entry, dict)]
    appearance["scars"] = [deep_copy(entry) for entry in (appearance.get("scars") or []) if isinstance(entry, dict)]
    appearance["height"] = str(appearance.get("height", "average") or "average")
    appearance["build"] = str(appearance.get("build", "neutral") or "neutral")
    appearance["muscle"] = clamp(int(appearance.get("muscle", 0) or 0), 0, 5)
    appearance["fat"] = clamp(int(appearance.get("fat", 0) or 0), 0, 5)
    appearance["aura"] = str(appearance.get("aura", "none") or "none")
    appearance["voice_tone"] = str(appearance.get("voice_tone", "") or "")
    appearance["summary_short"] = str(appearance.get("summary_short", "") or "")
    appearance["summary_full"] = str(appearance.get("summary_full", "") or "")
    return appearance

def normalize_age_fields(character: Dict[str, Any], world_time: Dict[str, Any]) -> None:
    bio = character.setdefault("bio", {})
    aging = character.setdefault(
        "aging",
        {
            "arrival_absolute_day": world_time["absolute_day"],
            "days_since_arrival": 0,
            "last_aged_absolute_day": world_time["absolute_day"],
            "age_effects_applied": [],
        },
    )
    age_years = int(bio.get("age_years", 0) or 0)
    if age_years <= 0:
        age_years = infer_age_years(str(bio.get("age", "") or ""))
    bio["age_years"] = age_years
    bio["age_stage"] = derive_age_stage(age_years)
    aging["arrival_absolute_day"] = max(1, int(aging.get("arrival_absolute_day", world_time["absolute_day"]) or world_time["absolute_day"]))
    aging["last_aged_absolute_day"] = max(aging["arrival_absolute_day"], int(aging.get("last_aged_absolute_day", aging["arrival_absolute_day"]) or aging["arrival_absolute_day"]))
    aging["days_since_arrival"] = max(0, int(world_time["absolute_day"]) - aging["arrival_absolute_day"])
    aging["age_effects_applied"] = [str(entry) for entry in (aging.get("age_effects_applied") or []) if str(entry).strip()]
    if not str(bio.get("age", "")).strip():
        bio["age"] = f"{bio['age_years']} Jahre"

def age_character_if_needed(character: Dict[str, Any], world_time: Dict[str, Any]) -> None:
    bio = character.setdefault("bio", {})
    aging = character.setdefault("aging", {})
    last_aged = max(1, int(aging.get("last_aged_absolute_day", world_time["absolute_day"]) or world_time["absolute_day"]))
    absolute_day = int(world_time["absolute_day"])
    while absolute_day - last_aged >= 360:
        bio["age_years"] = int(bio.get("age_years", 0) or 0) + 1
        last_aged += 360
    aging["last_aged_absolute_day"] = last_aged
    bio["age_stage"] = derive_age_stage(int(bio.get("age_years", 0) or 0))
    bio["age"] = f"{bio['age_years']} Jahre"
    aging["days_since_arrival"] = max(0, absolute_day - int(aging.get("arrival_absolute_day", absolute_day) or absolute_day))

def build_age_modifiers(character: Dict[str, Any]) -> Dict[str, Any]:
    stage = str(((character.get("bio") or {}).get("age_stage", "young")) or "young")
    modifiers = {
        "stage": stage,
        "resource_deltas": {"hp_max": 0, "stamina_max": 0},
        "skill_bonuses": {},
        "notes": [],
    }
    if stage == "teen":
        modifiers["resource_deltas"]["stamina_max"] = 1
        modifiers["notes"].append("Jugendliche Ausdauer")
    elif stage == "adult":
        modifiers["resource_deltas"]["stamina_max"] = -1
        modifiers["skill_bonuses"]["willpower"] = 1
        modifiers["notes"].append("Reifere Entschlossenheit")
    elif stage == "older":
        modifiers["resource_deltas"]["stamina_max"] = -2
        if int((character.get("attributes") or {}).get("con", 0) or 0) < 3:
            modifiers["resource_deltas"]["hp_max"] = -1
        modifiers["skill_bonuses"]["willpower"] = 1
        modifiers["skill_bonuses"]["intimidation"] = 1
        modifiers["notes"].append("Alternde Ausdauer")
        modifiers["notes"].append("Erfahrene Präsenz")
    return modifiers

def item_weight(item: Dict[str, Any]) -> int:
    try:
        return int(item.get("weight", 0) or 0)
    except (TypeError, ValueError):
        return 0

def item_modifier_value(item: Dict[str, Any], *, kind: str, stat: Optional[str] = None) -> int:
    total = 0
    for modifier in item.get("modifiers", []) or []:
        if modifier.get("kind") != kind:
            continue
        if stat is not None and modifier.get("stat") != stat:
            continue
        try:
            total += int(modifier.get("value", 0) or 0)
        except (TypeError, ValueError):
            continue
    return total

def ensure_character_modifier_shape(character: Dict[str, Any]) -> Dict[str, Any]:
    modifiers = character.setdefault("modifiers", {})
    defaults = default_character_modifiers()
    for key, value in defaults.items():
        modifiers.setdefault(key, deep_copy(value))
    return modifiers

def modifier_resource_key(modifier: Dict[str, Any]) -> str:
    return str(modifier.get("resource") or modifier.get("stat") or "").strip().lower()

def calculate_base_resource_maxima(character: Dict[str, Any], age_modifiers: Dict[str, Any]) -> Dict[str, int]:
    attrs = character.get("attributes", {}) or {}
    current_class = normalize_class_current(character.get("class_current")) or {}
    class_tags = {normalized_eval_text(tag) for tag in (current_class.get("affinity_tags") or []) if normalized_eval_text(tag)}
    class_level = max(1, int((current_class.get("level", 1) if current_class else 1) or 1))
    class_rank = str((current_class.get("rank", "F") if current_class else "F") or "F").upper()
    rank_bonus = {"F": 0, "E": 1, "D": 2, "C": 3, "B": 4, "A": 5, "S": 7}.get(class_rank, 0)

    hp_skill_bonus = 0
    sta_skill_bonus = 0
    res_skill_bonus = 0
    for raw_skill in (character.get("skills") or {}).values():
        if not isinstance(raw_skill, dict):
            continue
        level = max(1, int(raw_skill.get("level", 1) or 1))
        tags = {normalized_eval_text(tag) for tag in (raw_skill.get("tags") or []) if normalized_eval_text(tag)}
        if tags & {"körper", "koerper", "vital", "regeneration", "tank", "defense", "schutz"}:
            hp_skill_bonus += max(0, level // 3)
        if tags & {"ausdauer", "bewegung", "kampf", "technik", "athletik", "endurance"}:
            sta_skill_bonus += max(0, level // 4)
        if tags & {"magie", "aether", "mana", "qi", "rune", "arcane", "shadow", "holy", "zauber"}:
            res_skill_bonus += max(0, level // 4)

    class_hp_bonus = rank_bonus + (class_level // 4 if class_tags & {"körper", "koerper", "schutz", "kampf", "tank"} else 0)
    class_sta_bonus = rank_bonus + (class_level // 4 if class_tags & {"bewegung", "kampf", "technik", "ausdauer", "athletik"} else 0)
    class_res_bonus = rank_bonus + (class_level // 4 if class_tags & {"magie", "rune", "arcane", "shadow", "holy", "focus"} else 0)

    return {
        "hp": max(
            1,
            8
            + (int(attrs.get("con", 0) or 0) * 2)
            + int(age_modifiers["resource_deltas"].get("hp_max", 0) or 0)
            + class_hp_bonus
            + hp_skill_bonus,
        ),
        "stamina": max(
            1,
            8
            + int(attrs.get("con", 0) or 0)
            + int(attrs.get("dex", 0) or 0)
            + int(age_modifiers["resource_deltas"].get("stamina_max", 0) or 0)
            + class_sta_bonus
            + sta_skill_bonus,
        ),
        "aether": max(
            1,
            4
            + int(attrs.get("int", 0) or 0)
            + int(round(int(attrs.get("wis", 0) or 0) * 0.5))
            + class_res_bonus
            + res_skill_bonus,
        ),
        "stress": 10,
        "corruption": 100 if int((((character.get("resources") or {}).get("corruption") or {}).get("max", 0)) or 0) > 10 else 10,
        "wounds": 3,
    }

def calculate_bonus_resource_maxima(character: Dict[str, Any], items_db: Dict[str, Any]) -> Dict[str, int]:
    bonuses = {key: 0 for key in RESOURCE_KEYS}
    modifiers = ensure_character_modifier_shape(character)
    for entry in modifiers.get("resource_max", []) or []:
        if not isinstance(entry, dict):
            continue
        resource_key = modifier_resource_key(entry)
        if resource_key not in bonuses:
            continue
        bonuses[resource_key] += int(entry.get("value", 0) or 0)
    for item_id in iter_equipped_item_ids(character):
        item = items_db.get(item_id, {})
        for modifier in item.get("modifiers", []) or []:
            if modifier.get("kind") != "resource_max":
                continue
            resource_key = modifier_resource_key(modifier)
            if resource_key not in bonuses:
                continue
            bonuses[resource_key] += int(modifier.get("value", 0) or 0)
    for effect in character.get("effects", []) or []:
        for modifier in effect.get("modifiers", []) or []:
            if modifier.get("kind") != "resource_max":
                continue
            resource_key = modifier_resource_key(modifier)
            if resource_key not in bonuses:
                continue
            bonuses[resource_key] += int(modifier.get("value", 0) or 0)
    return bonuses

def migrate_legacy_resource_bonus_modifiers(
    character: Dict[str, Any],
    base_maxima: Dict[str, int],
    known_bonus: Dict[str, int],
    layer_presence: Dict[str, Dict[str, bool]],
) -> None:
    modifiers = ensure_character_modifier_shape(character)
    existing_entries = modifiers.setdefault("resource_max", [])
    by_resource = {
        entry.get("resource"): entry
        for entry in existing_entries
        if isinstance(entry, dict) and entry.get("source") == "legacy:max"
    }
    resources = character.get("resources", {}) or {}
    for resource_key in ("hp", "stamina", "aether"):
        resource = resources.get(resource_key, {}) or {}
        presence = layer_presence.get(resource_key, {})
        if presence.get("base_max") or presence.get("bonus_max"):
            continue
        existing_max = int(resource.get("max", 0) or 0)
        inferred_bonus = max(0, existing_max - (int(base_maxima.get(resource_key, 0) or 0) + int(known_bonus.get(resource_key, 0) or 0)))
        if inferred_bonus <= 0:
            continue
        if resource_key in by_resource:
            by_resource[resource_key]["value"] = inferred_bonus
        else:
            existing_entries.append(
                {
                    "resource": resource_key,
                    "value": inferred_bonus,
                    "source": "legacy:max",
                }
            )

def rebuild_resource_maxima(character: Dict[str, Any], items_db: Dict[str, Any], age_modifiers: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    existing_resources = character.get("resources", {}) if isinstance(character.get("resources"), dict) else {}
    layer_presence: Dict[str, Dict[str, bool]] = {}
    for resource_key in RESOURCE_KEYS:
        resource = existing_resources.get(resource_key) if isinstance(existing_resources.get(resource_key), dict) else {}
        layer_presence[resource_key] = {
            "base_max": "base_max" in resource,
            "bonus_max": "bonus_max" in resource,
        }

    base_maxima = calculate_base_resource_maxima(character, age_modifiers)
    known_bonus = calculate_bonus_resource_maxima(character, items_db)
    migrate_legacy_resource_bonus_modifiers(character, base_maxima, known_bonus, layer_presence)
    total_bonus = calculate_bonus_resource_maxima(character, items_db)

    runtime_layers: Dict[str, Dict[str, int]] = {}
    for resource_key in RESOURCE_KEYS:
        existing_layer = existing_resources.get(resource_key) if isinstance(existing_resources.get(resource_key), dict) else {}
        base_max = max(0, int(base_maxima.get(resource_key, existing_layer.get("base_max", existing_layer.get("max", 0))) or 0))
        bonus_max = int(total_bonus.get(resource_key, existing_layer.get("bonus_max", 0)) or 0)
        max_value = max(0, base_max + bonus_max)
        current_seed = int(existing_layer.get("current", 0) or 0)
        runtime_layers[resource_key] = {
            "current": clamp(current_seed, 0, max_value),
            "base_max": base_max,
            "bonus_max": bonus_max,
            "max": max_value,
        }

    hp_layer = runtime_layers.get("hp", {"current": 10, "max": 10})
    sta_layer = runtime_layers.get("stamina", {"current": 10, "max": 10})
    res_layer = runtime_layers.get("aether", {"current": 5, "max": 5})
    character["hp_max"] = max(1, int(hp_layer.get("max", character.get("hp_max", 10)) or character.get("hp_max", 10) or 10))
    character["sta_max"] = max(0, int(sta_layer.get("max", character.get("sta_max", 10)) or character.get("sta_max", 10) or 10))
    character["res_max"] = max(0, int(res_layer.get("max", character.get("res_max", 5)) or character.get("res_max", 5) or 5))
    character["hp_current"] = clamp(int(character.get("hp_current", hp_layer.get("current", character["hp_max"])) or hp_layer.get("current", character["hp_max"]) or character["hp_max"]), 0, character["hp_max"])
    character["sta_current"] = clamp(int(character.get("sta_current", sta_layer.get("current", character["sta_max"])) or sta_layer.get("current", character["sta_max"]) or character["sta_max"]), 0, character["sta_max"])
    character["res_current"] = clamp(int(character.get("res_current", res_layer.get("current", character["res_max"])) or res_layer.get("current", character["res_max"]) or character["res_max"]), 0, character["res_max"])

    if ENABLE_LEGACY_SHADOW_WRITEBACK:
        character.setdefault("resources", {})
        for key in RESOURCE_KEYS:
            character["resources"][key] = deep_copy(runtime_layers[key])
    else:
        resources_shadow = character.setdefault("resources", {})
        if not isinstance(resources_shadow, dict):
            resources_shadow = {}
            character["resources"] = resources_shadow
        for key in ("stress", "corruption", "wounds"):
            resources_shadow[key] = deep_copy(runtime_layers.get(key, {"current": 0, "base_max": 0, "bonus_max": 0, "max": 0}))
        strip_legacy_resource_shadows(character)

    return runtime_layers

def item_by_id(state: Dict[str, Any], item_id: str) -> Dict[str, Any]:
    return deep_copy((state.get("items") or {}).get(item_id) or {})

def list_inventory_items(character: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = character.get("inventory", {}).get("items", [])
    if isinstance(items, list):
        out = []
        for entry in items:
            if isinstance(entry, dict):
                out.append({"item_id": entry.get("item_id", ""), "stack": max(1, int(entry.get("stack", 1) or 1))})
            elif entry:
                out.append({"item_id": str(entry), "stack": 1})
        return out
    return []

def iter_equipped_item_ids(character: Dict[str, Any]) -> List[str]:
    equipment = character.get("equipment", {}) or {}
    return [value for value in equipment.values() if value]

def ensure_item_shape(item_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
    normalized = {
        "id": item_id,
        "name": item.get("name", item_id),
        "rarity": item.get("rarity", "common"),
        "slot": item.get("slot", ""),
        "weight": item_weight(item),
        "stackable": bool(item.get("stackable", False)),
        "max_stack": int(item.get("max_stack", 1) or 1),
        "weapon_profile": item.get("weapon_profile", {}),
        "modifiers": item.get("modifiers", []) or [],
        "effects": item.get("effects", []) or [],
        "durability": item.get("durability", {"current": 100, "max": 100}),
        "cursed": bool(item.get("cursed", False)),
        "curse_text": item.get("curse_text", ""),
        "tags": item.get("tags", []) or [],
    }
    if not normalized["slot"]:
        normalized["slot"] = ""
    return normalized

def normalize_equipment_slot_key(slot_name: Any) -> str:
    normalized = normalized_eval_text(slot_name)
    if not normalized:
        return ""
    return EQUIPMENT_SLOT_ALIASES.get(normalized, normalized if normalized in EQUIPMENT_CANONICAL_SLOTS else "")

def normalize_equipment_update_payload(payload: Any) -> Dict[str, str]:
    if not isinstance(payload, dict):
        return {}
    normalized: Dict[str, str] = {}
    for raw_slot, raw_value in payload.items():
        slot = normalize_equipment_slot_key(raw_slot)
        if not slot:
            continue
        normalized[slot] = str(raw_value or "").strip()
    return normalized

def infer_item_slot_from_definition(item: Dict[str, Any]) -> str:
    slot = normalize_equipment_slot_key(item.get("slot"))
    if slot:
        return slot
    tags = {normalized_eval_text(tag) for tag in (item.get("tags") or []) if normalized_eval_text(tag)}
    name = normalized_eval_text(item.get("name", ""))
    if "weapon" in tags or any(keyword in name for keyword in ITEM_WEAPON_KEYWORDS):
        return "weapon"
    if "offhand" in tags or any(keyword in name for keyword in ITEM_OFFHAND_KEYWORDS):
        return "offhand"
    if "armor" in tags or any(keyword in name for keyword in ITEM_CHEST_KEYWORDS):
        return "chest"
    if "trinket" in tags or any(keyword in name for keyword in ITEM_TRINKET_KEYWORDS):
        return "trinket"
    return ""

def item_matches_equipment_slot(item: Dict[str, Any], equip_slot: str) -> bool:
    slot = normalize_equipment_slot_key(equip_slot)
    if not slot:
        return False
    if slot in {"ring_1", "ring_2"}:
        return infer_item_slot_from_definition(item) in {"ring_1", "ring_2", "trinket", "amulet", ""}
    inferred = infer_item_slot_from_definition(item)
    if not inferred:
        return slot in {"trinket", "amulet"}
    if slot == "amulet":
        return inferred in {"amulet", "trinket"}
    return inferred == slot

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

def calculate_carry_limit(character: Dict[str, Any]) -> int:
    return 10 + (int((character.get("attributes") or {}).get("str", 0) or 0) * 2)

def calculate_carry_weight(character: Dict[str, Any], items_db: Dict[str, Any]) -> int:
    total = 0
    for entry in list_inventory_items(character):
        total += item_weight(items_db.get(entry["item_id"], {})) * entry["stack"]
    for item_id in iter_equipped_item_ids(character):
        total += item_weight(items_db.get(item_id, {}))
    return total

def calculate_resistances(character: Dict[str, Any], items_db: Dict[str, Any]) -> Dict[str, int]:
    res = {key: 0 for key in RESISTANCE_KEYS}
    for item_id in iter_equipped_item_ids(character):
        item = items_db.get(item_id, {})
        for key in RESISTANCE_KEYS:
            res[key] += item_modifier_value(item, kind="resistance", stat=key)
    for effect in character.get("effects", []) or []:
        for modifier in effect.get("modifiers", []) or []:
            if modifier.get("kind") == "resistance" and modifier.get("stat") in res:
                res[modifier["stat"]] += int(modifier.get("value", 0) or 0)
    for modifier in (ensure_character_modifier_shape(character).get("derived") or []):
        if not isinstance(modifier, dict):
            continue
        stat_name = str(modifier.get("stat", "") or "")
        if not stat_name.startswith("resistance:"):
            continue
        resistance_key = stat_name.split(":", 1)[1]
        if resistance_key in res:
            res[resistance_key] += int(modifier.get("value", 0) or 0)
    return res

def calculate_derived_bonus(character: Dict[str, Any], items_db: Dict[str, Any], stat_name: str) -> int:
    total = 0
    modifiers = ensure_character_modifier_shape(character)
    for modifier in modifiers.get("derived", []) or []:
        if not isinstance(modifier, dict):
            continue
        if str(modifier.get("stat", "") or "") != stat_name:
            continue
        total += int(modifier.get("value", 0) or 0)
    for item_id in iter_equipped_item_ids(character):
        item = items_db.get(item_id, {})
        total += item_modifier_value(item, kind=stat_name)
        if stat_name.startswith("attack_rating_"):
            total += item_modifier_value(item, kind="attack", stat=stat_name)
    for effect in character.get("effects", []) or []:
        for modifier in effect.get("modifiers", []) or []:
            kind = str(modifier.get("kind", "") or "")
            if kind == stat_name:
                total += int(modifier.get("value", 0) or 0)
            if stat_name.startswith("attack_rating_") and kind == "attack":
                mod_stat = str(modifier.get("stat", "") or "")
                if mod_stat in ("", stat_name):
                    total += int(modifier.get("value", 0) or 0)
    if stat_name == "initiative":
        for ability in character.get("abilities", []) or []:
            if ability.get("active") and ability.get("type") == "passive":
                total += int((ability.get("initiative_bonus") or 0))
    return total

def calculate_skill_modifier_bonus(character: Dict[str, Any], items_db: Dict[str, Any], skill_name: str) -> int:
    total = 0
    modifiers = ensure_character_modifier_shape(character)
    for modifier in modifiers.get("skill_effective", []) or []:
        if not isinstance(modifier, dict):
            continue
        if str(modifier.get("skill", modifier.get("stat", "")) or "") != skill_name:
            continue
        total += int(modifier.get("value", 0) or 0)
    for item_id in iter_equipped_item_ids(character):
        item = items_db.get(item_id, {})
        total += item_modifier_value(item, kind="skill", stat=skill_name)
        total += item_modifier_value(item, kind="skill_effective", stat=skill_name)
    for effect in character.get("effects", []) or []:
        for modifier in effect.get("modifiers", []) or []:
            kind = str(modifier.get("kind", "") or "")
            stat = str(modifier.get("stat", "") or "")
            if kind in ("skill", "skill_effective") and stat == skill_name:
                total += int(modifier.get("value", 0) or 0)
    total += int((((character.get("derived") or {}).get("age_modifiers") or {}).get("skill_bonuses") or {}).get(skill_name, 0) or 0)
    return total

def build_stat_based_appearance(character: Dict[str, Any], appearance: Dict[str, Any]) -> Dict[str, Any]:
    attrs = character.get("attributes", {}) or {}
    strength = int(attrs.get("str", 0) or 0)
    dexterity = int(attrs.get("dex", 0) or 0)
    constitution = int(attrs.get("con", 0) or 0)
    muscle = 0
    if strength >= 12:
        muscle = 5
    elif strength >= 10:
        muscle = 4
    elif strength >= 8:
        muscle = 3
    elif strength >= 6:
        muscle = 2
    elif strength >= 4:
        muscle = 1
    build = "neutral"
    if constitution >= 4:
        build = "robust"
    if dexterity >= 4 and build == "neutral":
        build = "lean"
    if dexterity >= 8 and strength < 8:
        build = "lean"
    if strength >= 10:
        build = "broad"
    elif strength >= 8 and build == "robust":
        build = "broad"
    return {
        "height": appearance.get("height", "average") or "average",
        "build": build,
        "muscle": muscle,
        "fat": clamp(int(appearance.get("fat", 0) or 0), 0, 5),
    }

def corruption_bucket(corruption_value: int) -> int:
    if corruption_value >= 80:
        return 4
    if corruption_value >= 60:
        return 3
    if corruption_value >= 40:
        return 2
    if corruption_value >= 20:
        return 1
    return 0

def build_corruption_visuals(character: Dict[str, Any], appearance: Dict[str, Any]) -> List[Dict[str, Any]]:
    current = int((((character.get("resources") or {}).get("corruption") or {}).get("current", 0)) or 0)
    bucket = corruption_bucket(current)
    modifiers: List[Dict[str, Any]] = []
    if bucket <= 0:
        return modifiers
    aura_by_bucket = {1: "faint", 2: "dark", 3: "ominous", 4: "abyssal"}
    eyes_by_bucket = {
        1: "mit einem schwachen violetten Schimmer",
        2: "zu dunkel und schattenumrandet",
        3: "unruhig dunkel, als würde Licht darin versinken",
        4: "abgründig schwarz mit kaltem Restglanz",
    }
    skin_by_bucket = {
        2: "feine dunkle Linien unter der Haut",
        3: "deutliche Schattenadern am Hals",
        4: "schwarze Risslinien entlang der Haut",
    }
    voice_by_bucket = {
        2: "rauer",
        3: "hohl",
        4: "unheimlich ruhig",
    }
    modifiers.append(
        {
            "source_type": "corruption",
            "source_id": f"corruption_{bucket}",
            "kind": "aura",
            "value": aura_by_bucket[bucket],
            "active": True,
        }
    )
    modifiers.append(
        {
            "source_type": "corruption",
            "source_id": f"corruption_{bucket}",
            "kind": "eyes",
            "value": eyes_by_bucket[bucket],
            "active": True,
        }
    )
    if bucket in skin_by_bucket:
        modifiers.append(
            {
                "source_type": "corruption",
                "source_id": f"corruption_{bucket}",
                "kind": "skin_mark",
                "value": skin_by_bucket[bucket],
                "active": True,
            }
        )
    if bucket in voice_by_bucket:
        modifiers.append(
            {
                "source_type": "corruption",
                "source_id": f"corruption_{bucket}",
                "kind": "voice_tone",
                "value": voice_by_bucket[bucket],
                "active": True,
            }
        )
    return modifiers

def build_faction_visuals(character: Dict[str, Any]) -> List[Dict[str, Any]]:
    visuals = []
    for membership in character.get("faction_memberships", []) or []:
        if not membership.get("active", True):
            continue
        faction_id = membership.get("faction_id", "")
        for modifier in membership.get("visual_modifiers", []) or []:
            if not isinstance(modifier, dict):
                continue
            visuals.append(
                {
                    "source_type": "faction",
                    "source_id": faction_id,
                    "kind": modifier.get("kind", ""),
                    "value": modifier.get("value", ""),
                    "active": True,
                }
            )
    return visuals

def build_class_visuals(character: Dict[str, Any]) -> List[Dict[str, Any]]:
    class_state = normalize_class_current(character.get("class_current")) or {}
    visuals = []
    class_id = class_state.get("id", "")
    for modifier in class_state.get("visual_modifiers", []) or []:
        if not isinstance(modifier, dict):
            continue
        visuals.append(
            {
                "source_type": "class",
                "source_id": class_id,
                "kind": modifier.get("kind", ""),
                "value": modifier.get("value", ""),
                "active": True,
            }
        )
    return visuals

def build_appearance_summary_short(character: Dict[str, Any]) -> str:
    appearance = character.get("appearance", {}) or {}
    parts = []
    build = appearance.get("build")
    if build == "lean":
        parts.append("drahtig")
    elif build == "robust":
        parts.append("robust")
    elif build == "broad":
        parts.append("breit gebaut")
    elif build == "frail":
        parts.append("schmächtig")
    if int(appearance.get("muscle", 0) or 0) >= 3:
        parts.append("breitere Schultern")
    scars = [entry for entry in (appearance.get("scars") or []) if entry.get("visible", True)]
    if scars:
        parts.append(f"{len(scars)} Narben")
    aura = appearance.get("aura", "none")
    if aura and aura != "none":
        aura_labels = {
            "faint": "schwache Schattenaura",
            "grim": "düstere Aura",
            "dark": "dunkle Aura",
            "ominous": "unheilvolle Aura",
            "abyssal": "abyssale Aura",
        }
        parts.append(aura_labels.get(aura, aura))
    extra_mark = next(
        (
            modifier.get("value", "")
            for modifier in (appearance.get("visual_modifiers") or [])
            if modifier.get("kind") == "skin_mark"
        ),
        "",
    )
    if extra_mark:
        parts.append(extra_mark)
    return ", ".join(part for part in parts if part) or "unauffällig"

def build_appearance_summary_full(character: Dict[str, Any]) -> str:
    appearance = character.get("appearance", {}) or {}
    parts = [build_appearance_summary_short(character)]
    if appearance.get("eyes", {}).get("current"):
        parts.append(f"Augen: {appearance['eyes']['current']}")
    if appearance.get("hair", {}).get("current"):
        parts.append(f"Haare: {appearance['hair']['current']}")
    if appearance.get("voice_tone"):
        parts.append(f"Stimme: {appearance['voice_tone']}")
    skin_marks = [str(entry) for entry in (appearance.get("skin_marks") or []) if str(entry).strip()]
    if skin_marks:
        parts.append(f"Hautzeichen: {', '.join(skin_marks)}")
    return " • ".join(part for part in parts if part)

def rebuild_character_appearance(character: Dict[str, Any], world_time: Dict[str, Any]) -> None:
    appearance = normalize_appearance_state(character)
    stat_layer = build_stat_based_appearance(character, appearance)
    modifiers = build_corruption_visuals(character, appearance) + build_class_visuals(character) + build_faction_visuals(character)
    appearance["height"] = stat_layer["height"]
    appearance["build"] = stat_layer["build"]
    appearance["muscle"] = stat_layer["muscle"]
    appearance["fat"] = stat_layer["fat"]
    appearance["visual_modifiers"] = modifiers
    eye_base = str((appearance.get("eyes") or {}).get("base", "") or "")
    eye_suffix = next((entry.get("value", "") for entry in modifiers if entry.get("kind") == "eyes"), "")
    appearance["eyes"]["current"] = (
        f"{eye_base} {eye_suffix}".strip()
        if eye_base and eye_suffix
        else eye_suffix or eye_base
    )
    hair = appearance.get("hair", {}) or {}
    appearance["hair"]["current"] = ", ".join(part for part in [hair.get("color", ""), hair.get("style", "")] if part).strip(", ")
    appearance["aura"] = next((entry.get("value", "none") for entry in modifiers if entry.get("kind") == "aura"), "none")
    appearance["voice_tone"] = next((entry.get("value", "") for entry in modifiers if entry.get("kind") == "voice_tone"), appearance.get("voice_tone", ""))
    appearance["summary_short"] = build_appearance_summary_short({"appearance": appearance})
    appearance["summary_full"] = build_appearance_summary_full({"appearance": appearance})
    character["appearance"] = appearance

def appearance_event_id(slot_name: str, kind: str, source: str, turn_number: int, absolute_day: int, new_value: str) -> str:
    digest = hashlib.sha256(f"{slot_name}:{kind}:{source}:{turn_number}:{absolute_day}:{new_value}".encode("utf-8")).hexdigest()[:10]
    return f"app_{digest}"

def format_appearance_message(display_name: str, kind: str, source: str, new_value: str) -> str:
    if kind == "aging_stage":
        return f"{display_name} wirkt nun deutlich {new_value}."
    if kind == "corruption_threshold":
        return f"An {display_name} wird die Verderbnis sichtbar: {new_value}."
    if kind == "class_visual":
        return f"{display_name}s neue Klasse hinterlässt sichtbare Spuren: {new_value}."
    if kind == "faction_visual":
        return f"{display_name} trägt nun sichtbare Zeichen einer Fraktion: {new_value}."
    if kind == "scar_added":
        return f"{display_name} trägt nun eine neue Narbe: {new_value}."
    return f"{display_name}s Erscheinung verändert sich: {new_value}."

def record_appearance_change(
    character: Dict[str, Any],
    *,
    slot_name: str,
    turn_number: int,
    absolute_day: int,
    kind: str,
    source: str,
    old_value: str,
    new_value: str,
) -> Optional[Dict[str, Any]]:
    if old_value == new_value:
        return None
    display_name = (character.get("bio") or {}).get("name") or slot_name
    event_id = appearance_event_id(slot_name, kind, source, turn_number, absolute_day, new_value)
    if any(entry.get("event_id") == event_id for entry in (character.get("appearance_history") or [])):
        return None
    event = {
        "event_id": event_id,
        "absolute_day": absolute_day,
        "turn_number": turn_number,
        "kind": kind,
        "source": source,
        "old_value": old_value,
        "new_value": new_value,
        "message": format_appearance_message(display_name, kind, source, new_value),
    }
    character.setdefault("appearance_history", []).append(event)
    return event

def sync_appearance_changes(
    before_character: Dict[str, Any],
    after_character: Dict[str, Any],
    *,
    slot_name: str,
    turn_number: int,
    absolute_day: int,
) -> List[Dict[str, Any]]:
    generated = []
    before_app = normalize_appearance_state(before_character)
    after_app = normalize_appearance_state(after_character)
    before_bio = before_character.get("bio", {}) or {}
    after_bio = after_character.get("bio", {}) or {}
    if before_bio.get("age_stage") != after_bio.get("age_stage"):
        event = record_appearance_change(
            after_character,
            slot_name=slot_name,
            turn_number=turn_number,
            absolute_day=absolute_day,
            kind="aging_stage",
            source="age_stage",
            old_value=str(before_bio.get("age_stage", "")),
            new_value=str(after_bio.get("age_stage", "")),
        )
        if event:
            generated.append(event)
    before_corruption = corruption_bucket(int((((before_character.get("resources") or {}).get("corruption") or {}).get("current", 0)) or 0))
    after_corruption = corruption_bucket(int((((after_character.get("resources") or {}).get("corruption") or {}).get("current", 0)) or 0))
    if before_corruption != after_corruption:
        event = record_appearance_change(
            after_character,
            slot_name=slot_name,
            turn_number=turn_number,
            absolute_day=absolute_day,
            kind="corruption_threshold",
            source="corruption",
            old_value=str(before_app.get("aura", "none")),
            new_value=str(after_app.get("summary_short", "")),
        )
        if event:
            generated.append(event)
    if before_app.get("build") != after_app.get("build") or before_app.get("muscle") != after_app.get("muscle"):
        source = "str"
        if (before_character.get("attributes") or {}).get("dex") != (after_character.get("attributes") or {}).get("dex"):
            source = "dex"
        elif (before_character.get("attributes") or {}).get("con") != (after_character.get("attributes") or {}).get("con"):
            source = "con"
        event = record_appearance_change(
            after_character,
            slot_name=slot_name,
            turn_number=turn_number,
            absolute_day=absolute_day,
            kind="stat_threshold",
            source=source,
            old_value=build_appearance_summary_short({"appearance": before_app}),
            new_value=build_appearance_summary_short({"appearance": after_app}),
        )
        if event:
            generated.append(event)
    before_class = ((normalize_class_current(before_character.get("class_current")) or {}).get("id", ""))
    after_class = ((normalize_class_current(after_character.get("class_current")) or {}).get("id", ""))
    if before_class != after_class and after_class:
        event = record_appearance_change(
            after_character,
            slot_name=slot_name,
            turn_number=turn_number,
            absolute_day=absolute_day,
            kind="class_visual",
            source=after_class,
            old_value=before_class,
            new_value=after_app.get("summary_short", ""),
        )
        if event:
            generated.append(event)
    before_factions = {entry.get("faction_id") for entry in (before_character.get("faction_memberships") or []) if entry.get("active", True)}
    after_factions = {entry.get("faction_id") for entry in (after_character.get("faction_memberships") or []) if entry.get("active", True)}
    if before_factions != after_factions and after_factions:
        event = record_appearance_change(
            after_character,
            slot_name=slot_name,
            turn_number=turn_number,
            absolute_day=absolute_day,
            kind="faction_visual",
            source="faction",
            old_value=", ".join(sorted(before_factions)),
            new_value=after_app.get("summary_short", ""),
        )
        if event:
            generated.append(event)
    before_scars = {entry.get("label") for entry in (before_app.get("scars") or [])}
    after_scars = {entry.get("label") for entry in (after_app.get("scars") or [])}
    for scar_label in sorted(after_scars - before_scars):
        event = record_appearance_change(
            after_character,
            slot_name=slot_name,
            turn_number=turn_number,
            absolute_day=absolute_day,
            kind="scar_added",
            source="scar",
            old_value="",
            new_value=scar_label,
        )
        if event:
            generated.append(event)
    return generated

def append_character_change_events(
    state_before: Dict[str, Any],
    state_after: Dict[str, Any],
    *,
    turn_number: int,
) -> List[str]:
    world_time = normalize_world_time(state_after.get("meta", {}))
    absolute_day = int(world_time["absolute_day"])
    messages = []
    for slot_name, after_character in (state_after.get("characters") or {}).items():
        before_character = (state_before.get("characters") or {}).get(slot_name) or blank_character_state(slot_name)
        events = sync_appearance_changes(
            before_character,
            after_character,
            slot_name=slot_name,
            turn_number=turn_number,
            absolute_day=absolute_day,
        )
        messages.extend(event["message"] for event in events if event.get("message"))
    if messages:
        state_after.setdefault("events", [])
        state_after["events"].extend(messages)
    return messages

def calculate_armor(character: Dict[str, Any], items_db: Dict[str, Any]) -> int:
    armor = 0
    for item_id in iter_equipped_item_ids(character):
        item = items_db.get(item_id, {})
        armor += item_modifier_value(item, kind="armor")
        weapon_profile = item.get("weapon_profile", {}) or {}
        armor += int(weapon_profile.get("armor_bonus", 0) or 0)
    return armor

def calculate_defense(character: Dict[str, Any], items_db: Dict[str, Any]) -> int:
    dex = int((character.get("attributes") or {}).get("dex", 0) or 0)
    defense = 10 + dex + calculate_armor(character, items_db)
    return defense + calculate_derived_bonus(character, items_db, "defense")

def calculate_initiative(character: Dict[str, Any], items_db: Dict[str, Any]) -> int:
    dex = int((character.get("attributes") or {}).get("dex", 0) or 0)
    return dex + calculate_derived_bonus(character, items_db, "initiative")

def calculate_attack_rating(character: Dict[str, Any], hand: str, items_db: Dict[str, Any]) -> int:
    equipment = character.get("equipment", {}) or {}
    item = items_db.get(equipment.get(hand, ""), {})
    weapon_profile = item.get("weapon_profile", {}) or {}
    scaling_stat = weapon_profile.get("scaling_stat")
    if not scaling_stat:
        category = weapon_profile.get("category", "")
        if category in ("finesse", "ranged"):
            scaling_stat = "dex"
        elif category == "focus":
            scaling_stat = "int"
        else:
            scaling_stat = "str"
    base = int((character.get("attributes") or {}).get(scaling_stat, 0) or 0)
    bonus = int(weapon_profile.get("attack_bonus", 0) or 0)
    skill_bonus = 0
    if scaling_stat == "dex":
        skill_bonus = skill_level_value(character, "athletics")
    elif scaling_stat in ("int", "wis"):
        skill_bonus = skill_level_value(character, "lore_occult")
    else:
        skill_bonus = skill_level_value(character, "athletics")
    effect_bonus = calculate_derived_bonus(character, items_db, f"attack_rating_{'mainhand' if hand == 'weapon' else 'offhand'}")
    return base + bonus + skill_bonus + effect_bonus

def calculate_combat_flags(character: Dict[str, Any]) -> Dict[str, Any]:
    hp_current = int(character.get("hp_current", 0) or 0)
    downed = hp_current <= 0
    in_combat = bool(character.get("combat_state", {}).get("in_combat", False))
    can_act = not downed
    for effect in character.get("effects", []) or []:
        effect_tags = set(effect.get("tags", []) or [])
        if "stun" in effect_tags or effect.get("category") == "stun":
            can_act = False
        if effect.get("category") == "combat":
            in_combat = True
    severe_injuries = [
        normalize_injury_state(entry)
        for entry in (character.get("injuries") or [])
        if isinstance(entry, dict)
    ]
    if any(
        injury
        and injury.get("severity") == "schwer"
        and injury.get("healing_stage") in {"frisch", "heilend"}
        for injury in severe_injuries
    ):
        can_act = False
    return {"in_combat": in_combat, "downed": downed, "can_act": can_act}

def skill_effective_bonus(character: Dict[str, Any], skill_name: str, items_db: Optional[Dict[str, Any]] = None) -> int:
    skill_data = normalize_skill_state(skill_name, (character.get("skills") or {}).get(skill_name, default_skill_state(skill_name)))
    skill_rank = int(skill_data.get("level", 1) or 1)
    if skill_rank <= 0:
        return 0
    stat_name = SKILL_ATTRIBUTE_MAP.get(skill_name, "int")
    stat_value = int((character.get("attributes") or {}).get(stat_name, 0) or 0)
    bonus = skill_rank + stat_value
    return bonus + calculate_skill_modifier_bonus(character, items_db or {}, skill_name)

def ensure_progression_shape(character: Dict[str, Any]) -> None:
    progression = character.setdefault("progression", {})
    progression.setdefault("rank", 1)
    progression.setdefault("xp", 0)
    progression.setdefault("next_xp", 100)
    progression.setdefault("system_level", 1)
    progression.setdefault("system_xp", 0)
    progression.setdefault("next_system_xp", 100)
    progression.setdefault("resource_name", "Aether")
    progression.setdefault("resource_current", 5)
    progression.setdefault("resource_max", 5)
    progression.setdefault("system_fragments", 0)
    progression.setdefault("system_cores", 0)
    progression.setdefault("attribute_points", 0)
    progression.setdefault("skill_points", 0)
    progression.setdefault("talent_points", 0)
    progression.setdefault("paths", [])
    progression.setdefault("potential_cards", [])

def ensure_character_progression_core(character: Dict[str, Any]) -> None:
    level = max(1, int(character.get("level", 1) or 1))
    xp_to_next = max(1, int(character.get("xp_to_next", next_character_xp_for_level(level)) or next_character_xp_for_level(level)))
    xp_current = clamp(int(character.get("xp_current", 0) or 0), 0, xp_to_next)
    xp_total = max(xp_current, int(character.get("xp_total", xp_current) or xp_current))
    character["level"] = level
    character["xp_to_next"] = xp_to_next
    character["xp_current"] = xp_current
    character["xp_total"] = xp_total
    recent = character.get("recent_progression_events")
    if not isinstance(recent, list):
        character["recent_progression_events"] = []
    else:
        character["recent_progression_events"] = [deep_copy(entry) for entry in recent if isinstance(entry, dict)][-40:]
    seeds = character.get("class_path_seeds")
    if not isinstance(seeds, list):
        character["class_path_seeds"] = []
    else:
        normalized_seeds: List[Dict[str, Any]] = []
        seen_ids = set()
        for seed in seeds:
            if not isinstance(seed, dict):
                continue
            seed_id = str(seed.get("id") or "").strip()
            if not seed_id or seed_id in seen_ids:
                continue
            seen_ids.add(seed_id)
            normalized_seeds.append(
                {
                    "id": seed_id,
                    "name": str(seed.get("name") or "").strip() or seed_id,
                    "theme_tags": [str(tag).strip() for tag in (seed.get("theme_tags") or []) if str(tag).strip()][:8],
                    "source_turn": max(0, int(seed.get("source_turn", 0) or 0)),
                    "confidence": clamp_float(float(seed.get("confidence", 0.0) or 0.0), 0.0, 1.0),
                    "status": str(seed.get("status") or "latent").strip().lower() if str(seed.get("status") or "").strip().lower() in {"latent", "confirmed", "unlocked"} else "latent",
                    "related_skill_ids": [str(value).strip() for value in (seed.get("related_skill_ids") or []) if str(value).strip()][:6],
                }
            )
        character["class_path_seeds"] = normalized_seeds[-20:]

def progression_speed_multiplier(world_settings: Optional[Dict[str, Any]] = None) -> float:
    speed = str(((world_settings or {}).get("progression_speed") or "normal")).strip().lower()
    if speed == "langsam":
        return 0.82
    if speed == "schnell":
        return 1.22
    return 1.0

def normalize_progression_event_severity(value: Any) -> str:
    severity = str(value or "medium").strip().lower()
    return severity if severity in PROGRESSION_EVENT_SEVERITIES else "medium"

def normalize_progression_event(
    raw_event: Any,
    *,
    actor: str,
    source_turn: int,
    default_type: str = "milestone_progress",
) -> Optional[Dict[str, Any]]:
    if not isinstance(raw_event, dict):
        return None
    event_type = str(raw_event.get("type") or default_type).strip().lower()
    if event_type not in PROGRESSION_EVENT_TYPES:
        return None
    normalized_actor = str(raw_event.get("actor") or actor or "").strip()
    if not normalized_actor:
        return None
    target_skill_id = str(raw_event.get("target_skill_id") or "").strip() or None
    target_class_id = str(raw_event.get("target_class_id") or "").strip() or None
    target_element_id = str(raw_event.get("target_element_id") or "").strip() or None
    reason = str(raw_event.get("reason") or "").strip()
    metadata = deep_copy(raw_event.get("metadata") or {})
    skill_payload = deep_copy(raw_event.get("skill") or {})
    tags = [str(tag).strip() for tag in (raw_event.get("tags") or []) if str(tag).strip()]
    if event_type == "skill_manifestation":
        tags = list(dict.fromkeys(tags + ["manifestation"]))
    return {
        "type": event_type,
        "actor": normalized_actor,
        "target_skill_id": target_skill_id,
        "target_class_id": target_class_id,
        "target_element_id": target_element_id,
        "severity": normalize_progression_event_severity(raw_event.get("severity")),
        "tags": list(dict.fromkeys(tags)),
        "source_turn": max(0, int(raw_event.get("source_turn", source_turn) or source_turn)),
        "reason": reason,
        "metadata": metadata if isinstance(metadata, dict) else {},
        "skill": skill_payload if isinstance(skill_payload, dict) else {},
    }

def is_skill_manifestation_name_plausible(skill_name: str, actor_name: str) -> bool:
    clean = clean_extracted_skill_name(skill_name)
    normalized = normalized_eval_text(clean)
    actor_norm = normalized_eval_text(actor_name)
    if not clean or len(normalized) < 3:
        return False
    if len(clean) > 42:
        return False
    words = [word for word in re.split(r"\s+", clean.strip()) if word]
    if len(words) > 4:
        return False
    if normalized in UNIVERSAL_SKILL_LIKE_NAMES:
        return False
    if normalized in ABILITY_UNLOCK_GENERIC_NAMES:
        return False
    if normalized in SKILL_MANIFESTATION_VERB_BLACKLIST:
        return False
    normalized_words = [normalized_eval_text(word) for word in words]
    if any(word in SKILL_MANIFESTATION_VERB_BLACKLIST for word in normalized_words):
        return False
    if len(words) >= 3 and any(word in SKILL_MANIFESTATION_NAME_STOPWORDS for word in normalized_words):
        return False
    if any(fragment in normalized for fragment in SKILL_MANIFESTATION_NAME_TOKEN_BLACKLIST):
        return False
    if any(char.isdigit() for char in clean):
        return False
    if actor_norm and normalized == actor_norm:
        return False
    return True

def canonicalize_manifested_skill_payload(
    *,
    raw_skill: Dict[str, Any],
    character: Dict[str, Any],
    world: Optional[Dict[str, Any]] = None,
    world_settings: Optional[Dict[str, Any]] = None,
    default_source: str = "Manifestation",
) -> Optional[Dict[str, Any]]:
    resource_name = resource_name_for_character(character, world_settings)
    proposed_name = str(raw_skill.get("name") or raw_skill.get("id") or "").strip()
    raw_power_rating = int(raw_skill.get("power_rating", 0) or 0)
    actor_name = str(((character.get("bio") or {}).get("name") or character.get("slot_id") or "").strip())
    if not is_skill_manifestation_name_plausible(proposed_name, actor_name):
        return None
    skill = normalize_dynamic_skill_state(
        {
            "id": raw_skill.get("id") or skill_id_from_name(proposed_name),
            "name": proposed_name,
            "rank": normalize_skill_rank(raw_skill.get("rank")),
            "level": max(1, int(raw_skill.get("level", 1) or 1)),
            "level_max": max(1, int(raw_skill.get("level_max", DEFAULT_DYNAMIC_SKILL_LEVEL_MAX) or DEFAULT_DYNAMIC_SKILL_LEVEL_MAX)),
            "xp": max(0, int(raw_skill.get("xp", 0) or 0)),
            "next_xp": max(1, int(raw_skill.get("next_xp", next_skill_xp_for_level(1)) or next_skill_xp_for_level(1))),
            "mastery": clamp(int(raw_skill.get("mastery", 0) or 0), 0, 100),
            "tags": [str(tag).strip() for tag in (raw_skill.get("tags") or []) if str(tag).strip()],
            "description": str(raw_skill.get("description") or "").strip(),
            "effect_summary": str(raw_skill.get("effect_summary") or "").strip(),
            "power_rating": int(raw_skill.get("power_rating", 0) or 0),
            "growth_potential": str(raw_skill.get("growth_potential") or "").strip(),
            "cost": raw_skill.get("cost"),
            "price": raw_skill.get("price"),
            "cooldown_turns": raw_skill.get("cooldown_turns"),
            "unlocked_from": str(raw_skill.get("unlocked_from") or default_source),
            "manifestation_source": str(raw_skill.get("manifestation_source") or default_source),
            "category": raw_skill.get("category"),
            "class_affinity": raw_skill.get("class_affinity"),
            "elements": raw_skill.get("elements"),
            "element_primary": raw_skill.get("element_primary"),
            "element_synergies": raw_skill.get("element_synergies"),
        },
        resource_name=resource_name,
        unlocked_from=default_source,
    )
    if not skill.get("description"):
        skill["description"] = f"{skill['name']} wurde unter Druck manifestiert."
    if not skill.get("effect_summary"):
        skill["effect_summary"] = skill["description"][:180]
    if raw_power_rating <= 0:
        skill["power_rating"] = max(1, (skill_rank_sort_value(skill.get("rank")) + 1) * 6 + int(skill.get("level", 1) or 1))
    else:
        skill["power_rating"] = max(1, raw_power_rating)
    if not skill.get("growth_potential"):
        skill["growth_potential"] = "mittel"
    resolved_elements = normalize_element_id_list(skill.get("elements") or [], world or {})
    if not resolved_elements:
        class_element = resolve_class_element_id(character.get("class_current"), world or {})
        if class_element:
            resolved_elements = [class_element]
    skill["elements"] = resolved_elements
    primary_candidates = normalize_element_id_list([skill.get("element_primary")], world or {})
    skill["element_primary"] = primary_candidates[0] if primary_candidates else (resolved_elements[0] if resolved_elements else None)
    if skill.get("element_primary") and skill["element_primary"] not in skill["elements"]:
        skill["elements"].insert(0, skill["element_primary"])
    return skill

def append_recent_progression_event(character: Dict[str, Any], event: Dict[str, Any]) -> None:
    recent = character.setdefault("recent_progression_events", [])
    if not isinstance(recent, list):
        recent = []
        character["recent_progression_events"] = recent
    recent.append(
        {
            "type": str(event.get("type") or ""),
            "severity": str(event.get("severity") or "medium"),
            "source_turn": int(event.get("source_turn", 0) or 0),
            "reason": str(event.get("reason") or "").strip(),
            "target_skill_id": str(event.get("target_skill_id") or "").strip(),
            "target_class_id": str(event.get("target_class_id") or "").strip(),
            "target_element_id": str(event.get("target_element_id") or "").strip(),
        }
    )
    if len(recent) > 40:
        del recent[:-40]

def resolve_skill_id_for_event(character: Dict[str, Any], raw_skill_id: str) -> str:
    skill_store = character.get("skills") or {}
    if raw_skill_id in skill_store:
        return raw_skill_id
    normalized = normalized_eval_text(raw_skill_id)
    if not normalized:
        return ""
    normalized_compact = re.sub(r"[^a-z0-9]+", "", normalized)
    for skill_id, skill_value in skill_store.items():
        skill_name = str((skill_value or {}).get("name") or skill_id)
        candidate_ids = {
            normalized_eval_text(skill_id),
            normalized_eval_text(skill_name),
            normalized_eval_text(skill_id_from_name(skill_name)),
        }
        if normalized in candidate_ids:
            return skill_id
        candidate_compact = {re.sub(r"[^a-z0-9]+", "", entry) for entry in candidate_ids if entry}
        if normalized_compact and normalized_compact in candidate_compact:
            return skill_id
        for candidate in candidate_ids:
            if candidate and normalized and (
                candidate.startswith(normalized)
                or normalized.startswith(candidate)
                or SequenceMatcher(None, candidate, normalized).ratio() >= 0.92
            ):
                return skill_id
        if normalized_eval_text(skill_name) == normalized:
            return skill_id
    return ""

def apply_system_xp(character: Dict[str, Any], amount: int) -> None:
    if amount <= 0:
        return
    ensure_progression_shape(character)
    ensure_character_progression_core(character)
    progression = character["progression"]
    xp_gain = max(0, int(amount or 0))
    character["xp_total"] = int(character.get("xp_total", 0) or 0) + xp_gain
    character["xp_current"] = int(character.get("xp_current", 0) or 0) + xp_gain
    progression["system_xp"] = int(progression.get("system_xp", 0) or 0) + max(1, xp_gain // 3)
    while character["xp_current"] >= int(character.get("xp_to_next", next_character_xp_for_level(character["level"])) or next_character_xp_for_level(character["level"])):
        required = int(character.get("xp_to_next", next_character_xp_for_level(character["level"])) or next_character_xp_for_level(character["level"]))
        character["xp_current"] = max(0, int(character.get("xp_current", 0) or 0) - required)
        character["level"] = int(character.get("level", 1) or 1) + 1
        character["xp_to_next"] = next_character_xp_for_level(character["level"])
        progression["attribute_points"] = int(progression.get("attribute_points", 0) or 0) + 1
        progression["skill_points"] = int(progression.get("skill_points", 0) or 0) + 1
    while progression["system_xp"] >= int(progression.get("next_system_xp", 100) or 100):
        progression["system_xp"] -= int(progression.get("next_system_xp", 100) or 100)
        progression["system_level"] = int(progression.get("system_level", 1) or 1) + 1
        progression["talent_points"] = int(progression.get("talent_points", 0) or 0) + 1
        progression["next_system_xp"] = 100 + ((int(progression["system_level"]) - 1) * 50)
    character["xp_current"] = clamp(int(character.get("xp_current", 0) or 0), 0, int(character.get("xp_to_next", 1) or 1))

def apply_class_xp(character: Dict[str, Any], amount: int, *, event_reason: str = "") -> List[str]:
    out: List[str] = []
    if amount <= 0:
        return out
    current_class = normalize_class_current(character.get("class_current"))
    if not current_class:
        return out
    current_class["xp"] = int(current_class.get("xp", 0) or 0) + int(amount or 0)
    leveled = False
    while (
        current_class["level"] < current_class["level_max"]
        and current_class["xp"] >= int(current_class.get("xp_next", next_class_xp_for_level(current_class["level"])) or next_class_xp_for_level(current_class["level"]))
    ):
        required = int(current_class.get("xp_next", next_class_xp_for_level(current_class["level"])) or next_class_xp_for_level(current_class["level"]))
        current_class["xp"] = max(0, int(current_class.get("xp", 0) or 0) - required)
        current_class["level"] += 1
        current_class["xp_next"] = next_class_xp_for_level(current_class["level"])
        leveled = True
    current_class["xp_next"] = max(1, int(current_class.get("xp_next", next_class_xp_for_level(current_class["level"])) or next_class_xp_for_level(current_class["level"])))
    current_class["xp"] = clamp(int(current_class.get("xp", 0) or 0), 0, current_class["xp_next"])
    current_class["class_mastery"] = clamp(int((current_class["xp"] / max(current_class["xp_next"], 1)) * 100), 0, 100)
    if current_class["level"] >= current_class["level_max"] and current_class.get("ascension", {}).get("status") == "none":
        current_class.setdefault("ascension", {}).update({"status": "available"})
        out.append(f"Klassenaufstieg bereit: {current_class.get('name', 'Klasse')}.")
    if leveled:
        out.append(
            f"Klassenfortschritt: {current_class.get('name', 'Klasse')} erreicht Lv {current_class.get('level')}/{current_class.get('level_max')}."
            + (f" ({event_reason})" if event_reason else "")
        )
    character["class_current"] = normalize_class_current(current_class)
    return out

def build_elemental_core_skill_payload(
    *,
    skill_name: str,
    element_id: str,
    class_name: str,
    resource_name: str,
    unlocked_from: str,
) -> Dict[str, Any]:
    pretty_name = clean_extracted_skill_name(skill_name) or str(skill_name or "").strip() or "Elementtechnik"
    return normalize_dynamic_skill_state(
        {
            "id": skill_id_from_name(pretty_name),
            "name": pretty_name,
            "rank": "F",
            "level": 1,
            "level_max": DEFAULT_DYNAMIC_SKILL_LEVEL_MAX,
            "tags": ["technik", "elementar", normalize_codex_alias_text(class_name)],
            "description": f"{pretty_name} ist Teil des Klassenkerns von {class_name}.",
            "effect_summary": f"{pretty_name} kanalisiert elementare Energie.",
            "power_rating": 8,
            "growth_potential": "mittel",
            "elements": [element_id] if element_id else [],
            "element_primary": element_id or None,
            "cost": {"resource": resource_name, "amount": 1},
            "unlocked_from": unlocked_from,
            "manifestation_source": "class_core",
            "category": "elemental_core",
            "class_affinity": [normalize_codex_alias_text(class_name)] if class_name else None,
            "xp": 0,
            "next_xp": next_skill_xp_for_level(1),
            "mastery": 0,
        },
        resource_name=resource_name,
    )

def ensure_class_rank_core_skills(
    character: Dict[str, Any],
    world: Dict[str, Any],
    world_settings: Optional[Dict[str, Any]] = None,
    *,
    unlock_extra: bool = False,
) -> List[str]:
    messages: List[str] = []
    current_class = normalize_class_current(character.get("class_current"))
    if not current_class:
        return messages
    node_info = resolve_class_path_rank_node(world, current_class)
    if not node_info:
        return messages
    node = node_info["node"]
    current_class["path_id"] = str(node_info.get("path_id") or current_class.get("path_id") or "")
    current_class["path_rank"] = normalize_skill_rank(node_info.get("rank") or current_class.get("rank") or "F")
    current_class["element_id"] = str(node_info.get("element_id") or current_class.get("element_id") or "")
    current_class["element_tags"] = list(
        dict.fromkeys(
            [
                *(current_class.get("element_tags") or []),
                str(current_class.get("element_id") or "").strip(),
            ]
        )
    )
    character["class_current"] = normalize_class_current(current_class)
    skill_store = character.setdefault("skills", {})
    resource_name = resource_name_for_character(character, world_settings or {})
    class_name = str(current_class.get("name") or "")
    required = [str(name).strip() for name in (node.get("core_skills_required") or []) if str(name).strip()]
    unlockable = [str(name).strip() for name in (node.get("core_skills_unlockable") or []) if str(name).strip()]
    signature = [str(name).strip() for name in (node.get("signature_skills") or []) if str(name).strip()]
    guaranteed: List[str] = required[:1] if required else []
    if unlock_extra:
        guaranteed.extend(unlockable[:1])
        if current_class.get("rank") in {"A", "S"}:
            guaranteed.extend(signature[:1])
    for skill_name in guaranteed:
        skill_id = skill_id_from_name(skill_name)
        if skill_id in skill_store:
            existing = normalize_dynamic_skill_state(skill_store[skill_id], resource_name=resource_name)
            if current_class.get("element_id") and current_class["element_id"] not in (existing.get("elements") or []):
                existing["elements"] = [current_class["element_id"], *(existing.get("elements") or [])]
                existing["element_primary"] = existing.get("element_primary") or current_class["element_id"]
                skill_store[skill_id] = normalize_dynamic_skill_state(existing, resource_name=resource_name)
            continue
        new_skill = build_elemental_core_skill_payload(
            skill_name=skill_name,
            element_id=str(current_class.get("element_id") or ""),
            class_name=class_name,
            resource_name=resource_name,
            unlocked_from=f"ClassCore:{current_class.get('rank','F')}",
        )
        skill_store[new_skill["id"]] = new_skill
        char_name = str(((character.get("bio") or {}).get("name") or character.get("slot_id") or "").strip() or "Die Figur")
        messages.append(f"{char_name} schaltet den Klassenkern-Skill {new_skill['name']} frei.")
    return messages

def refresh_skill_progression(character: Dict[str, Any]) -> None:
    ensure_progression_shape(character)
    ensure_character_progression_core(character)
    resource_name = resource_name_for_character(character)
    character["skills"] = {
        skill_id: normalize_dynamic_skill_state(
            skill_value,
            skill_id=skill_id,
            skill_name=(skill_value or {}).get("name", skill_id) if isinstance(skill_value, dict) else skill_id,
            resource_name=resource_name,
            unlocked_from=(skill_value or {}).get("unlocked_from", "Story") if isinstance(skill_value, dict) else "Story",
        )
        for skill_id, skill_value in (character.get("skills") or {}).items()
    }
    if ENABLE_LEGACY_SHADOW_WRITEBACK:
        character["abilities"] = []
    else:
        character.pop("abilities", None)

def grant_skill_xp(
    character: Dict[str, Any],
    skill_name: str,
    outcome: str,
    *,
    world_settings: Optional[Dict[str, Any]] = None,
) -> List[str]:
    skill_store = character.setdefault("skills", {})
    if not skill_store:
        return []
    resolved_skill_id = resolve_skill_id_for_event(character, skill_name) or skill_id_from_name(skill_name)
    if resolved_skill_id not in skill_store:
        return []
    outcome_key = str(outcome or "normal").strip().lower()
    base_xp = {
        "minor": 8,
        "small": 10,
        "normal": 16,
        "major": 28,
        "critical": 40,
    }.get(outcome_key, 16)
    resource_name = resource_name_for_character(character)
    skill = normalize_dynamic_skill_state(skill_store[resolved_skill_id], skill_id=resolved_skill_id, resource_name=resource_name)
    multiplier = effective_skill_progress_multiplier(character, skill, world_settings or {})
    gained = max(1, int(round(base_xp * multiplier)))
    skill["xp"] = int(skill.get("xp", 0) or 0) + gained
    leveled = False
    while skill["level"] < skill["level_max"] and skill["xp"] >= int(skill.get("next_xp", next_skill_xp_for_level(skill["level"])) or next_skill_xp_for_level(skill["level"])):
        required = int(skill.get("next_xp", next_skill_xp_for_level(skill["level"])) or next_skill_xp_for_level(skill["level"]))
        skill["xp"] = max(0, int(skill.get("xp", 0) or 0) - required)
        skill["level"] += 1
        skill["next_xp"] = next_skill_xp_for_level(skill["level"])
        leveled = True
    skill["mastery"] = clamp(int((int(skill.get("xp", 0) or 0) / max(1, int(skill.get("next_xp", 1) or 1))) * 100), 0, 100)
    skill_store[resolved_skill_id] = normalize_dynamic_skill_state(skill, resource_name=resource_name)
    messages: List[str] = []
    if leveled:
        messages.append(f"Skill-Fortschritt: {skill['name']} erreicht Lv {skill['level']}/{skill['level_max']}.")
    return messages

def parse_skill_event(campaign: Dict[str, Any], event_text: str) -> Optional[Dict[str, str]]:
    text = str(event_text or "").strip()
    if not text:
        return None
    marker = re.match(r"SKILL_XP\[(slot_[0-9]+):([^:\]]+):([^:\]]+)\]", text, flags=re.IGNORECASE)
    if marker:
        return {
            "actor": marker.group(1).strip(),
            "skill": marker.group(2).strip(),
            "outcome": marker.group(3).strip().lower(),
        }
    return None

def normalize_progression_event_list(
    events: Any,
    *,
    actor: str,
    source_turn: int,
) -> List[Dict[str, Any]]:
    if not isinstance(events, list):
        return []
    normalized_events: List[Dict[str, Any]] = []
    for raw_event in events:
        normalized_event = normalize_progression_event(raw_event, actor=actor, source_turn=source_turn)
        if normalized_event:
            normalized_events.append(normalized_event)
    return normalized_events

def progression_event_priority(event_type: str) -> int:
    return int(PROGRESSION_EVENT_PRIORITY.get(str(event_type or "").strip().lower(), 10))

def _event_origin(raw_event: Dict[str, Any]) -> str:
    metadata = raw_event.get("metadata") if isinstance(raw_event.get("metadata"), dict) else {}
    origin = str(metadata.get("origin") or "").strip().lower()
    return origin if origin in {"explicit_patch", "inferred_patch"} else "inferred_patch"

def reduce_progression_event_density(
    events: List[Dict[str, Any]],
    *,
    state_after: Dict[str, Any],
    action_type: str,
) -> List[Dict[str, Any]]:
    if action_type == "canon":
        return [deep_copy(entry) for entry in events if isinstance(entry, dict)]
    milestone = milestone_state_for_turn(
        int((state_after.get("meta") or {}).get("turn", 0) or 0),
        active_pacing_profile(state_after),
    )
    caps = PROGRESSION_DENSITY_CAP_MILESTONE if bool(milestone.get("is_milestone")) else PROGRESSION_DENSITY_CAP_NON_MILESTONE
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    actor_order: List[str] = []
    for idx, raw_event in enumerate(events):
        if not isinstance(raw_event, dict):
            continue
        actor = str(raw_event.get("actor") or "").strip()
        if not actor:
            continue
        if actor not in grouped:
            grouped[actor] = []
            actor_order.append(actor)
        entry = deep_copy(raw_event)
        entry["_index"] = idx
        grouped[actor].append(entry)

    reduced: List[Dict[str, Any]] = []
    for actor in actor_order:
        actor_events = grouped.get(actor, [])
        explicit_events: List[Dict[str, Any]] = []
        inferred_events: List[Dict[str, Any]] = []
        seen_keys: set[Tuple[str, str, str, str, str, str]] = set()
        for event in actor_events:
            dedupe_key = progression_event_dedupe_key(event) + (_event_origin(event),)
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            if _event_origin(event) == "explicit_patch":
                explicit_events.append(event)
            else:
                inferred_events.append(event)

        inferred_events = sorted(
            inferred_events,
            key=lambda item: (
                -progression_event_priority(str(item.get("type") or "")),
                -{"low": 1, "medium": 2, "high": 3}.get(str(item.get("severity") or "medium").strip().lower(), 2),
                int(item.get("_index", 0) or 0),
            ),
        )
        selected = explicit_events + inferred_events[: max(0, int(caps["inferred"]))]
        selected = sorted(selected, key=lambda item: int(item.get("_index", 0) or 0))
        if not explicit_events:
            selected = selected[: max(1, int(caps["total"]))]
        for event in selected:
            event.pop("_index", None)
            reduced.append(event)
    return reduced

def patch_has_explicit_skill_progression_for_actor(patch: Dict[str, Any], actor: str) -> bool:
    actor_patch = ((patch.get("characters") or {}).get(actor) or {}) if isinstance((patch.get("characters") or {}), dict) else {}
    if not isinstance(actor_patch, dict):
        return False
    if (
        actor_patch.get("skills_set")
        or actor_patch.get("skills_delta")
        or actor_patch.get("abilities_add")
        or actor_patch.get("class_set")
        or actor_patch.get("class_update")
        or actor_patch.get("progression_set")
    ):
        return True
    explicit_events = normalize_progression_event_list(
        actor_patch.get("progression_events"),
        actor=actor,
        source_turn=0,
    )
    return bool(explicit_events)

def normalize_progression_claim_type(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in PROGRESSION_CLAIM_TYPES:
        return normalized
    return ""

def progression_claim_text_for_actor(story_text: str, actor_display: str) -> str:
    relevant = story_sentences_for_actor(story_text, actor_display)
    if relevant:
        return "\n".join(relevant)
    return str(story_text or "")

def detect_progression_claim_types(story_text: str, actor_display: str) -> List[str]:
    normalized_story = normalized_eval_text(progression_claim_text_for_actor(story_text, actor_display))
    if not normalized_story:
        return []
    detected: List[str] = []
    for claim_type, cues in PROGRESSION_CLAIM_CUES.items():
        if any(cue in normalized_story for cue in cues):
            detected.append(claim_type)
    return list(dict.fromkeys(detected))

def progression_claim_coverage_for_actor_patch(patch: Dict[str, Any], actor: str) -> Set[str]:
    coverage: Set[str] = set()
    actor_patch = ((patch.get("characters") or {}).get(actor) or {}) if isinstance((patch.get("characters") or {}), dict) else {}
    if not isinstance(actor_patch, dict):
        return coverage

    skills_set = actor_patch.get("skills_set") if isinstance(actor_patch.get("skills_set"), dict) else {}
    if skills_set:
        coverage.add("skill_claim")
        for raw_skill in skills_set.values():
            if isinstance(raw_skill, dict):
                if int(raw_skill.get("level", 1) or 1) > 1 or int(raw_skill.get("xp", 0) or 0) > 0:
                    coverage.add("skill_level_claim")
                break

    skills_delta = actor_patch.get("skills_delta") if isinstance(actor_patch.get("skills_delta"), dict) else {}
    if skills_delta:
        coverage.add("skill_level_claim")

    class_set = normalize_class_current(actor_patch.get("class_set"))
    if class_set:
        coverage.add("class_claim")
        if int(class_set.get("level", 1) or 1) > 1:
            coverage.add("class_level_claim")

    class_update = actor_patch.get("class_update") if isinstance(actor_patch.get("class_update"), dict) else {}
    if class_update:
        coverage.add("class_claim")
        if any(key in class_update for key in ("level", "xp", "xp_next", "rank")):
            coverage.add("class_level_claim")

    progression_set = actor_patch.get("progression_set") if isinstance(actor_patch.get("progression_set"), dict) else {}
    if progression_set:
        if any(key in progression_set for key in ("class_level", "class_xp", "class_xp_to_next")):
            coverage.add("class_level_claim")
        if any(key in progression_set for key in ("level", "xp_total", "xp_current", "xp_to_next")):
            coverage.add("skill_level_claim")

    explicit_events = normalize_progression_event_list(
        actor_patch.get("progression_events"),
        actor=actor,
        source_turn=0,
    )
    for event in explicit_events:
        event_type = str(event.get("type") or "").strip().lower()
        if event_type == "skill_manifestation":
            coverage.add("manifestation_claim")
            coverage.add("skill_claim")
        elif event_type in {"skill_mastery_use", "training_success"}:
            coverage.add("skill_level_claim")
        elif event_type == "class_breakthrough":
            coverage.add("class_claim")
            coverage.add("class_level_claim")
    return coverage

def normalized_progression_claims(claim_types: List[str]) -> List[str]:
    normalized = [normalize_progression_claim_type(entry) for entry in (claim_types or [])]
    return [entry for entry in list(dict.fromkeys(normalized)) if entry]

def progression_missing_claim_types(claim_types: List[str], coverage: Set[str]) -> List[str]:
    claims = normalized_progression_claims(claim_types)
    missing = [claim_type for claim_type in claims if claim_type not in (coverage or set())]
    return list(dict.fromkeys(missing))

def normalize_progression_extractor_character_patch(raw_patch: Any) -> Dict[str, Any]:
    patch = raw_patch if isinstance(raw_patch, dict) else {}
    normalized: Dict[str, Any] = {}
    if isinstance(patch.get("skills_set"), dict):
        normalized["skills_set"] = deep_copy(patch.get("skills_set") or {})
    if isinstance(patch.get("skills_delta"), dict):
        normalized["skills_delta"] = deep_copy(patch.get("skills_delta") or {})
    if isinstance(patch.get("progression_events"), list):
        normalized["progression_events"] = deep_copy(patch.get("progression_events") or [])
    class_set = normalize_class_current(patch.get("class_set"))
    if class_set:
        normalized["class_set"] = class_set
    if isinstance(patch.get("class_update"), dict) and patch.get("class_update"):
        normalized["class_update"] = deep_copy(patch.get("class_update") or {})
    if isinstance(patch.get("progression_set"), dict) and patch.get("progression_set"):
        normalized["progression_set"] = deep_copy(patch.get("progression_set") or {})
    return normalized

def progression_event_dedupe_key(event: Dict[str, Any]) -> Tuple[str, str, str, str, str]:
    event_type = str(event.get("type") or "").strip().lower()
    target_skill = str(event.get("target_skill_id") or "").strip().lower()
    target_class = str(event.get("target_class_id") or "").strip().lower()
    reason = normalized_eval_text(str(event.get("reason") or ""))
    skill_name = normalized_eval_text(str(((event.get("skill") or {}) if isinstance(event.get("skill"), dict) else {}).get("name") or ""))
    return (event_type, target_skill, target_class, reason, skill_name)

def merge_progression_patch_additive(
    *,
    base_patch: Dict[str, Any],
    actor: str,
    supplement_character_patch: Dict[str, Any],
    state_after: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    merged = normalize_patch_semantics(base_patch)
    actor_update = merged.setdefault("characters", {}).setdefault(actor, {})
    incoming = normalize_progression_extractor_character_patch(supplement_character_patch)
    merge_meta = {
        "applied_keys": [],
        "conflicts": [],
        "added_events": 0,
    }

    state_character = ((state_after.get("characters") or {}).get(actor) or {})
    state_skill_names = {
        normalized_eval_text((entry or {}).get("name", ""))
        for entry in ((state_character.get("skills") or {}).values())
        if isinstance(entry, dict)
    }

    incoming_skills_set = incoming.get("skills_set") if isinstance(incoming.get("skills_set"), dict) else {}
    if incoming_skills_set:
        target_skills = actor_update.setdefault("skills_set", {})
        target_skill_names = {
            normalized_eval_text((entry or {}).get("name", ""))
            for entry in (target_skills.values())
            if isinstance(entry, dict)
        }
        for skill_id, raw_skill in incoming_skills_set.items():
            normalized_skill = normalize_dynamic_skill_state(
                raw_skill,
                skill_id=str(skill_id),
                skill_name=(raw_skill or {}).get("name", skill_id) if isinstance(raw_skill, dict) else str(skill_id),
                resource_name=resource_name_for_character(state_character, ((state_after.get("world") or {}).get("settings") or {})),
            )
            skill_name_norm = normalized_eval_text(normalized_skill.get("name", ""))
            if str(skill_id) in target_skills or (skill_name_norm and (skill_name_norm in target_skill_names or skill_name_norm in state_skill_names)):
                merge_meta["conflicts"].append({"key": "skills_set", "id": str(skill_id), "name": normalized_skill.get("name", "")})
                continue
            target_skills[str(skill_id)] = normalized_skill
            if skill_name_norm:
                target_skill_names.add(skill_name_norm)
            if "skills_set" not in merge_meta["applied_keys"]:
                merge_meta["applied_keys"].append("skills_set")

    incoming_skills_delta = incoming.get("skills_delta") if isinstance(incoming.get("skills_delta"), dict) else {}
    if incoming_skills_delta:
        target_delta = actor_update.setdefault("skills_delta", {})
        for skill_id, delta_payload in incoming_skills_delta.items():
            sid = str(skill_id or "").strip()
            if not sid:
                continue
            if sid in target_delta:
                merge_meta["conflicts"].append({"key": "skills_delta", "id": sid})
                continue
            target_delta[sid] = deep_copy(delta_payload)
            if "skills_delta" not in merge_meta["applied_keys"]:
                merge_meta["applied_keys"].append("skills_delta")

    incoming_events = normalize_progression_event_list(incoming.get("progression_events"), actor=actor, source_turn=0)
    if incoming_events:
        target_events = actor_update.setdefault("progression_events", [])
        existing_keys = {
            progression_event_dedupe_key(event)
            for event in normalize_progression_event_list(target_events, actor=actor, source_turn=0)
        }
        for event in incoming_events:
            key = progression_event_dedupe_key(event)
            if key in existing_keys:
                merge_meta["conflicts"].append({"key": "progression_events", "type": event.get("type", "")})
                continue
            existing_keys.add(key)
            target_events.append(deep_copy(event))
            merge_meta["added_events"] = int(merge_meta.get("added_events", 0) or 0) + 1
            if "progression_events" not in merge_meta["applied_keys"]:
                merge_meta["applied_keys"].append("progression_events")

    for scalar_key in ("class_set", "class_update", "progression_set"):
        value = incoming.get(scalar_key)
        if not value:
            continue
        if actor_update.get(scalar_key):
            merge_meta["conflicts"].append({"key": scalar_key})
            continue
        actor_update[scalar_key] = deep_copy(value)
        if scalar_key not in merge_meta["applied_keys"]:
            merge_meta["applied_keys"].append(scalar_key)

    return merged, merge_meta

def evaluate_progression_extractor_confidence(
    *,
    actor: str,
    actor_display: str,
    claim_types: List[str],
    model_confidence: str,
    character_patch: Dict[str, Any],
) -> Dict[str, Any]:
    normalized_model_confidence = str(model_confidence or "").strip().lower()
    if normalized_model_confidence not in PROGRESSION_EXTRACTOR_CONFIDENCE_ORDER:
        normalized_model_confidence = "medium"
    model_score = PROGRESSION_EXTRACTOR_CONFIDENCE_SCORE.get(normalized_model_confidence, 0.6)

    heuristic_score = 0.0
    if character_patch.get("skills_set"):
        heuristic_score += 0.35
    if character_patch.get("skills_delta"):
        heuristic_score += 0.2
    if character_patch.get("progression_events"):
        heuristic_score += 0.3
    if character_patch.get("class_set") or character_patch.get("class_update") or character_patch.get("progression_set"):
        heuristic_score += 0.25

    coverage = progression_claim_coverage_for_actor_patch({"characters": {actor: character_patch}}, actor)
    normalized_claims = normalized_progression_claims(claim_types)
    if normalized_claims:
        covered_count = len([claim for claim in normalized_claims if claim in coverage])
        heuristic_score += 0.25 * (covered_count / max(1, len(normalized_claims)))

    for raw_skill in (character_patch.get("skills_set") or {}).values():
        if not isinstance(raw_skill, dict):
            continue
        skill_name = str(raw_skill.get("name") or "").strip()
        if skill_name and not is_skill_manifestation_name_plausible(skill_name, actor_display):
            heuristic_score -= 0.3
            break

    heuristic_score = clamp_float(heuristic_score, 0.0, 1.0)
    combined_score = clamp_float((heuristic_score * 0.65) + (model_score * 0.35), 0.0, 1.0)
    if combined_score >= PROGRESSION_EXTRACTOR_CONFIDENCE_THRESHOLDS["high"]:
        final_confidence = "high"
    elif combined_score >= PROGRESSION_EXTRACTOR_CONFIDENCE_THRESHOLDS["medium"]:
        final_confidence = "medium"
    else:
        final_confidence = "low"
    return {
        "confidence": final_confidence,
        "score": combined_score,
        "model_confidence": normalized_model_confidence,
        "heuristic_score": heuristic_score,
        "coverage": sorted(coverage),
    }

def call_progression_canon_extractor(
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    *,
    actor: str,
    action_type: str,
    claim_types: List[str],
    claim_text: str,
    player_text: str,
    story_text: str,
) -> Dict[str, Any]:
    context_packet = build_extractor_context_packet(
        campaign,
        state,
        actor,
        action_type,
        story_text,
        source="progression_gate",
    )
    user_prompt = (
        "STATE_PACKET(JSON):\n"
        + context_packet
        + "\n\nCLAIM_TYPES(JSON):\n"
        + json.dumps(normalized_progression_claims(claim_types), ensure_ascii=False)
        + "\n\nCLAIM_TEXT:\n"
        + str(claim_text or "")[:2200]
        + "\n\nPLAYER_TEXT:\n"
        + str(player_text or "")[:1200]
        + "\n\nOUTPUT-KONTRAKT:\n"
        + PROGRESSION_EXTRACTOR_JSON_CONTRACT
    )
    payload = call_ollama_schema(
        PROGRESSION_EXTRACTOR_SYSTEM_PROMPT,
        user_prompt,
        PROGRESSION_EXTRACTOR_SCHEMA,
        timeout=90,
        temperature=0.15,
    )
    character_patch = normalize_progression_extractor_character_patch((payload or {}).get("character_patch"))
    confidence_meta = evaluate_progression_extractor_confidence(
        actor=actor,
        actor_display=display_name_for_slot(campaign, actor),
        claim_types=claim_types,
        model_confidence=str((payload or {}).get("confidence") or "medium"),
        character_patch=character_patch,
    )
    return {
        "character_patch": character_patch,
        "confidence": confidence_meta["confidence"],
        "confidence_score": confidence_meta["score"],
        "model_confidence": confidence_meta["model_confidence"],
        "heuristic_score": confidence_meta["heuristic_score"],
        "coverage": confidence_meta["coverage"],
        "reason": str((payload or {}).get("reason") or "").strip(),
    }

def run_canon_gate(
    campaign: Dict[str, Any],
    *,
    state_before: Dict[str, Any],
    state_after: Dict[str, Any],
    patch: Dict[str, Any],
    actor: str,
    action_type: str,
    player_text: str,
    story_text: str,
    trace_ctx: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    merged_patch = normalize_patch_semantics(patch)
    gate_meta: Dict[str, Any] = {
        "domains_supported": list(CANON_GATE_DOMAINS_SUPPORTED),
        "domains_active": sorted(CANON_GATE_ACTIVE_DOMAINS),
        "domains_run": [],
        "claim_types": [],
        "missing_claim_types": [],
        "decision": "skipped",
        "reason_code": "NO_ACTION",
        "extractor_confidence": "low",
        "extractor_confidence_score": 0.0,
        "needs_review": False,
        "warnings": [],
    }
    emit_turn_phase_event(
        trace_ctx,
        phase="canon_gate_started",
        success=True,
        extra={"domains_active": sorted(CANON_GATE_ACTIVE_DOMAINS)},
    )
    if action_type == "canon" or actor not in (state_after.get("characters") or {}):
        gate_meta["reason_code"] = "SKIPPED_MODE_OR_ACTOR"
        emit_turn_phase_event(
            trace_ctx,
            phase="canon_gate_finished",
            success=True,
            extra={"decision": gate_meta["decision"], "reason_code": gate_meta["reason_code"]},
        )
        return {"patch": merged_patch, "state": state_after, "meta": gate_meta}

    if "progression" not in CANON_GATE_ACTIVE_DOMAINS:
        gate_meta["reason_code"] = "DOMAIN_DISABLED"
        emit_turn_phase_event(
            trace_ctx,
            phase="canon_gate_finished",
            success=True,
            extra={"decision": gate_meta["decision"], "reason_code": gate_meta["reason_code"]},
        )
        return {"patch": merged_patch, "state": state_after, "meta": gate_meta}

    actor_display = display_name_for_slot(campaign, actor)
    claim_text = progression_claim_text_for_actor(story_text, actor_display)
    claim_types = detect_progression_claim_types(claim_text, actor_display)
    gate_meta["domains_run"] = ["progression"]
    gate_meta["claim_types"] = claim_types
    if not claim_types:
        gate_meta["reason_code"] = "NO_CLAIMS"
        emit_turn_phase_event(
            trace_ctx,
            phase="canon_gate_finished",
            success=True,
            extra={"decision": gate_meta["decision"], "reason_code": gate_meta["reason_code"]},
        )
        return {"patch": merged_patch, "state": state_after, "meta": gate_meta}

    coverage = progression_claim_coverage_for_actor_patch(merged_patch, actor)
    missing_claims = progression_missing_claim_types(claim_types, coverage)
    gate_meta["missing_claim_types"] = missing_claims
    if not missing_claims:
        gate_meta["reason_code"] = "STRUCTURED_ALREADY_PRESENT"
        emit_turn_phase_event(
            trace_ctx,
            phase="canon_gate_finished",
            success=True,
            extra={"decision": gate_meta["decision"], "reason_code": gate_meta["reason_code"], "claims": claim_types},
        )
        return {"patch": merged_patch, "state": state_after, "meta": gate_meta}

    emit_turn_phase_event(
        trace_ctx,
        phase="progression_extractor_started",
        success=True,
        extra={"claims": missing_claims},
    )
    try:
        extractor_result = call_progression_canon_extractor(
            campaign,
            state_after,
            actor=actor,
            action_type=action_type,
            claim_types=missing_claims,
            claim_text=claim_text,
            player_text=player_text,
            story_text=story_text,
        )
        emit_turn_phase_event(
            trace_ctx,
            phase="progression_extractor_finished",
            success=True,
            extra={
                "claims": missing_claims,
                "confidence": extractor_result.get("confidence"),
                "score": float(extractor_result.get("confidence_score", 0.0) or 0.0),
            },
        )
    except Exception as exc:
        warning = f"progression_extractor_error:{exc.__class__.__name__}"
        gate_meta["warnings"].append(warning)
        gate_meta["reason_code"] = "PROGRESSION_EXTRACTOR_ERROR"
        emit_turn_phase_event(
            trace_ctx,
            phase="progression_extractor_finished",
            success=False,
            error_code=ERROR_CODE_EXTRACTOR,
            error_class=exc.__class__.__name__,
            message=str(exc)[:240],
            extra={"claims": missing_claims},
        )
        emit_turn_phase_event(
            trace_ctx,
            phase="canon_gate_finished",
            success=True,
            extra={"decision": gate_meta["decision"], "reason_code": gate_meta["reason_code"], "warnings": gate_meta["warnings"]},
        )
        return {"patch": merged_patch, "state": state_after, "meta": gate_meta}

    confidence = str(extractor_result.get("confidence") or "low").strip().lower()
    confidence_score = float(extractor_result.get("confidence_score", 0.0) or 0.0)
    gate_meta["extractor_confidence"] = confidence
    gate_meta["extractor_confidence_score"] = confidence_score
    gate_meta["extractor_model_confidence"] = str(extractor_result.get("model_confidence") or "")
    gate_meta["extractor_coverage"] = deep_copy(extractor_result.get("coverage") or [])
    character_patch = normalize_progression_extractor_character_patch(extractor_result.get("character_patch"))

    if confidence == "low" or not character_patch:
        gate_meta["reason_code"] = "LOW_CONFIDENCE_NO_COMMIT" if confidence == "low" else "EMPTY_EXTRACTOR_PATCH"
        gate_meta["decision"] = "skipped"
        emit_turn_phase_event(
            trace_ctx,
            phase="canon_gate_finished",
            success=True,
            extra={
                "decision": gate_meta["decision"],
                "reason_code": gate_meta["reason_code"],
                "confidence": confidence,
                "score": confidence_score,
            },
        )
        return {"patch": merged_patch, "state": state_after, "meta": gate_meta}

    merged_with_gate, merge_meta = merge_progression_patch_additive(
        base_patch=merged_patch,
        actor=actor,
        supplement_character_patch=character_patch,
        state_after=state_after,
    )
    gate_meta["merge"] = merge_meta
    if not (merge_meta.get("applied_keys") or []):
        gate_meta["decision"] = "skipped"
        gate_meta["reason_code"] = "NO_ADDITIVE_CHANGES"
        emit_turn_phase_event(
            trace_ctx,
            phase="canon_gate_finished",
            success=True,
            extra={"decision": gate_meta["decision"], "reason_code": gate_meta["reason_code"]},
        )
        return {"patch": merged_patch, "state": state_after, "meta": gate_meta}

    gate_patch = blank_patch()
    gate_patch["characters"][actor] = deep_copy((merged_with_gate.get("characters") or {}).get(actor) or {})
    try:
        emit_turn_phase_event(trace_ctx, phase="patch_sanitize", success=True, extra={"stage": "canon_gate"})
        gate_patch = sanitize_patch(state_after, gate_patch)
        emit_turn_phase_event(trace_ctx, phase="patch_sanitize", success=True, extra={"stage": "canon_gate", "result": "ok"})
        emit_turn_phase_event(trace_ctx, phase="schema_validation", success=True, extra={"stage": "canon_gate"})
        validate_patch(state_after, gate_patch)
        emit_turn_phase_event(trace_ctx, phase="schema_validation", success=True, extra={"stage": "canon_gate", "result": "ok"})
        emit_turn_phase_event(trace_ctx, phase="patch_apply", success=True, extra={"stage": "canon_gate"})
        state_after = apply_patch(state_after, gate_patch, attribute_cap=attribute_cap_for_campaign(campaign))
        emit_turn_phase_event(trace_ctx, phase="patch_apply", success=True, extra={"stage": "canon_gate", "result": "ok"})
        merged_patch = merge_patch_payloads(merged_patch, gate_patch)
    except Exception as exc:
        gate_meta["decision"] = "skipped"
        gate_meta["reason_code"] = "GATE_PATCH_APPLY_FAILED"
        gate_meta["warnings"].append(f"gate_patch_apply_failed:{exc.__class__.__name__}")
        emit_turn_phase_event(
            trace_ctx,
            phase="patch_apply",
            success=False,
            error_code=ERROR_CODE_PATCH_APPLY,
            error_class=exc.__class__.__name__,
            message=str(exc)[:240],
            extra={"stage": "canon_gate"},
        )
        emit_turn_phase_event(
            trace_ctx,
            phase="canon_gate_finished",
            success=True,
            extra={
                "decision": gate_meta["decision"],
                "reason_code": gate_meta["reason_code"],
                "warnings": gate_meta["warnings"],
            },
        )
        return {"patch": merged_patch, "state": state_after, "meta": gate_meta}

    gate_meta["decision"] = "flagged" if confidence == "medium" else "committed"
    gate_meta["needs_review"] = bool(confidence == "medium")
    gate_meta["reason_code"] = "COMMIT_MEDIUM_CONFIDENCE" if confidence == "medium" else "COMMIT_HIGH_CONFIDENCE"
    emit_turn_phase_event(
        trace_ctx,
        phase="canon_gate_finished",
        success=True,
        extra={
            "decision": gate_meta["decision"],
            "reason_code": gate_meta["reason_code"],
            "confidence": confidence,
            "score": confidence_score,
            "applied_keys": merge_meta.get("applied_keys") or [],
        },
    )
    return {"patch": merged_patch, "state": state_after, "meta": gate_meta}

def manifestation_seed_from_skill(skill_payload: Dict[str, Any], *, source_turn: int, confidence: float) -> Optional[Dict[str, Any]]:
    if not isinstance(skill_payload, dict):
        return None
    skill_name = str(skill_payload.get("name") or "").strip()
    if not skill_name:
        return None
    normalized = normalized_eval_text(skill_name)
    if not normalized:
        return None
    if any(tag in normalized for tag in ("pilz", "spore", "myzel", "wurzel", "ranke", "garten")):
        seed_name = "Myzelpfad"
        seed_tags = ["spore", "nature", "myzel"]
    elif any(tag in normalized for tag in ("licht", "sonne", "glanz")):
        seed_name = "Lichtpfad"
        seed_tags = ["light"]
    elif any(tag in normalized for tag in ("schatten", "nacht", "finster")):
        seed_name = "Schattenpfad"
        seed_tags = ["shadow"]
    else:
        seed_name = f"{skill_name} Pfad"
        seed_tags = [token for token in normalized.split(" ") if token][:2]
    seed_id = f"seed_{re.sub(r'[^a-z0-9]+', '_', normalized_eval_text(seed_name)).strip('_') or 'latent'}"
    return {
        "id": seed_id,
        "name": seed_name,
        "theme_tags": seed_tags[:4],
        "source_turn": max(0, int(source_turn or 0)),
        "confidence": clamp_float(float(confidence or 0.0), 0.0, 1.0),
        "status": "latent",
        "related_skill_ids": [skill_id_from_name(skill_name)],
    }

def upsert_class_path_seed(character: Dict[str, Any], seed: Dict[str, Any]) -> Optional[str]:
    if not isinstance(seed, dict):
        return None
    ensure_character_progression_core(character)
    seed_id = str(seed.get("id") or "").strip()
    if not seed_id:
        return None
    seeds = character.setdefault("class_path_seeds", [])
    existing = next((entry for entry in seeds if isinstance(entry, dict) and str(entry.get("id") or "").strip() == seed_id), None)
    if existing:
        existing["confidence"] = max(
            clamp_float(float(existing.get("confidence", 0.0) or 0.0), 0.0, 1.0),
            clamp_float(float(seed.get("confidence", 0.0) or 0.0), 0.0, 1.0),
        )
        existing["source_turn"] = max(int(existing.get("source_turn", 0) or 0), int(seed.get("source_turn", 0) or 0))
        existing["theme_tags"] = stable_sorted_unique_strings(list(existing.get("theme_tags") or []) + list(seed.get("theme_tags") or []), limit=8)
        existing["related_skill_ids"] = stable_sorted_unique_strings(list(existing.get("related_skill_ids") or []) + list(seed.get("related_skill_ids") or []), limit=8)
        return None
    seeds.append(deep_copy(seed))
    ensure_character_progression_core(character)
    return f"Pfad-Saat entdeckt: {seed.get('name', seed_id)}."

def infer_manifested_skill_name_with_llm(
    *,
    motif: str,
    actor_name: str,
    player_text: str,
    story_text: str,
    existing_names: Set[str],
) -> str:
    motif_key = str(motif or "").strip().lower()
    motif_token_gate: Dict[str, Tuple[str, ...]] = {
        "spore": ("myzel", "spore", "wurzel", "ranke", "pilz", "garten", "moos"),
        "light": ("licht", "strahl", "glanz", "sonnen", "heilig"),
        "shadow": ("schatten", "nacht", "finster", "dunkel"),
        "flame": ("feuer", "flamme", "glut", "asche", "brand"),
        "frost": ("frost", "eis", "reif", "kälte"),
        "storm": ("sturm", "wind", "donner", "blitz"),
        "martial": ("klinge", "stoß", "hieb", "parade", "kampf"),
    }
    required_tokens = motif_token_gate.get(motif_key, ())

    def motif_token_match(name: str) -> bool:
        if not required_tokens:
            return True
        normalized_name = normalized_eval_text(name)
        return any(token in normalized_name for token in required_tokens)

    motif_seed_names: Dict[str, List[str]] = {
        "spore": ["Myzelgriff", "Sporenfessel", "Wurzelstoß", "Gartenklaue"],
        "light": ["Lichtlanze", "Strahlenschnitt", "Sonnenimpuls", "Heiligglanz"],
        "shadow": ["Schattenriss", "Nachtfessel", "Finsterhieb", "Dunkelgriff"],
        "flame": ["Glutstoß", "Flammenriss", "Aschenklinge", "Feuerschwinge"],
        "frost": ["Frostriss", "Eisfessel", "Reifstoß", "Kältehieb"],
        "storm": ["Donnerschnitt", "Sturmimpuls", "Windriss", "Blitzgriff"],
        "martial": ["Klingenfokus", "Stoßtechnik", "Parierhieb", "Kampftakt"],
    }
    motif_label = {
        "spore": "Sporen/Natur",
        "light": "Licht",
        "shadow": "Schatten",
        "flame": "Feuer/Glut",
        "frost": "Frost/Eis",
        "storm": "Sturm/Wind/Donner",
        "martial": "Klingenkampf/Körpertechnik",
    }.get(motif_key, "Mystik")
    user_prompt = (
        f"Akteur: {actor_name}\n"
        f"Motiv: {motif_label}\n"
        f"Spieleraktion: {player_text[:360]}\n"
        f"Story-Kontext: {story_text[:520]}\n"
        f"Vergebene Skillnamen (verboten): {', '.join(sorted([name for name in existing_names if name])) or '-'}\n"
        "Gib einen neuartigen, glaubwürdigen Skillnamen zurück."
    )
    for _ in range(2):
        candidate = ""
        try:
            payload = call_ollama_schema(
                MANIFESTATION_SKILL_NAME_SYSTEM_PROMPT,
                user_prompt,
                MANIFESTATION_SKILL_NAME_SCHEMA,
                timeout=60,
                temperature=max(0.55, OLLAMA_TEMPERATURE),
            )
            candidate = str((payload or {}).get("name") or "").strip()
        except Exception:
            candidate = ""
        candidate = re.sub(r"\s+", " ", candidate).strip(" .,:;!?\"'`")
        normalized_candidate = normalized_eval_text(candidate)
        if (
            candidate
            and normalized_candidate
            and normalized_candidate not in existing_names
            and is_skill_manifestation_name_plausible(candidate, actor_name)
            and motif_token_match(candidate)
        ):
            return candidate
    for fallback_candidate in motif_seed_names.get(motif_key, []):
        normalized_fallback = normalized_eval_text(fallback_candidate)
        if normalized_fallback and normalized_fallback not in existing_names and is_skill_manifestation_name_plausible(fallback_candidate, actor_name):
            return fallback_candidate
    fallback = f"{motif_label} Manifestation".replace("/", " ")
    fallback = re.sub(r"\s+", " ", fallback).strip()
    if normalized_eval_text(fallback) in existing_names or not is_skill_manifestation_name_plausible(fallback, actor_name):
        fallback = f"{motif_label} Impuls".replace("/", " ")
    fallback = re.sub(r"\s+", " ", fallback).strip()
    if not is_skill_manifestation_name_plausible(fallback, actor_name) or normalized_eval_text(fallback) in existing_names:
        return ""
    return fallback

def infer_manifestation_progression_events_from_story(
    *,
    state_before: Dict[str, Any],
    state_after: Dict[str, Any],
    patch: Dict[str, Any],
    actor: str,
    action_type: str,
    player_text: str,
    story_text: str,
) -> List[Dict[str, Any]]:
    if action_type == "canon" or actor not in (state_after.get("characters") or {}):
        return []
    if patch_has_explicit_skill_progression_for_actor(patch, actor):
        return []
    character_before = ((state_before.get("characters") or {}).get(actor) or {})
    character_after = ((state_after.get("characters") or {}).get(actor) or {})

    actor_name = str(((character_after.get("bio") or {}).get("name") or actor).strip() or actor)
    story_norm = normalized_eval_text(story_text)
    player_norm = normalized_eval_text(player_text)
    combined_norm = f"{story_norm} {player_norm}".strip()
    if not combined_norm:
        return []
    first_skill_missing = not bool(character_after.get("skills") or {})
    actor_bound = sentence_mentions_actor_name(story_text, actor_name) or any(player_norm.startswith(prefix) for prefix in ("ich ", "ich,", "ich."))
    first_manifest = any(cue in combined_norm for cue in MANIFESTATION_STRONG_CUES)
    concrete_effect_story = any(cue in story_norm for cue in MANIFESTATION_EFFECT_CUES)
    concrete_effect_player = any(cue in player_norm for cue in MANIFESTATION_EFFECT_CUES)
    concrete_effect = concrete_effect_story or concrete_effect_player
    combat_present = any(cue in combined_norm for cue in COMBAT_NARRATIVE_HINTS)
    force_roll = _hash_unit_interval(
        f"first_skill_force|{int((state_after.get('meta') or {}).get('turn', 0) or 0)}|{actor}|{combined_norm[:160]}"
    )
    force_first_skill = bool(
        first_skill_missing
        and action_type in {"do", "say", "story"}
        and combat_present
        and force_roll <= FIRST_SKILL_FORCE_PROBABILITY
    )
    tactical = any(cue in combined_norm for cue in MANIFESTATION_TACTICAL_CUES)
    world_reaction = any(cue in combined_norm for cue in MANIFESTATION_WORLD_REACTION_CUES)
    cost_signal = any(cue in combined_norm for cue in MANIFESTATION_COST_CUES)
    motif_matches = []
    for motif, tokens in MANIFESTATION_MOTIF_GROUPS.items():
        if any(token in combined_norm for token in tokens):
            motif_matches.append(motif)
    identity = bool(motif_matches)
    story_support = (
        concrete_effect_story
        or any(token in story_norm for token in MANIFESTATION_TACTICAL_CUES)
        or any(token in story_norm for token in MANIFESTATION_WORLD_REACTION_CUES)
        or any(token in story_norm for token in MANIFESTATION_COST_CUES)
        or any(any(token in story_norm for token in tokens) for tokens in MANIFESTATION_MOTIF_GROUPS.values())
    )
    score = sum([1 if actor_bound else 0, 1 if first_manifest else 0, 1 if concrete_effect else 0, 1 if identity else 0, 1 if tactical else 0, 1 if world_reaction else 0, 1 if cost_signal else 0])
    if force_first_skill:
        if not actor_bound or not (concrete_effect or combat_present):
            return []
        if not motif_matches:
            motif_matches = ["martial"]
            identity = True
    else:
        if not (actor_bound and first_manifest and concrete_effect and identity):
            return []
        if not story_support:
            return []
        if score < 5:
            return []

    existing_names = {
        normalized_eval_text((entry or {}).get("name", ""))
        for entry in ((character_after.get("skills") or {}).values())
        if isinstance(entry, dict)
    }
    motif_tags = {
        "spore": ["manifestation", "nature", "spore", "control"],
        "light": ["manifestation", "light", "offense"],
        "shadow": ["manifestation", "shadow", "control"],
        "flame": ["manifestation", "flame", "offense"],
        "frost": ["manifestation", "frost", "control"],
        "storm": ["manifestation", "storm", "offense"],
        "martial": ["manifestation", "martial", "offense"],
    }
    selected_motif = motif_matches[0]
    base_name = infer_manifested_skill_name_with_llm(
        motif=selected_motif,
        actor_name=actor_name,
        player_text=player_text,
        story_text=story_text,
        existing_names=existing_names,
    )
    if not base_name:
        return []
    motif = selected_motif
    tags = motif_tags.get(motif, ["manifestation", "storm", "offense"])
    candidate_skill_id = skill_id_from_name(base_name)
    existing_event_skill_ids = set()
    actor_patch = ((patch.get("characters") or {}).get(actor) or {}) if isinstance((patch.get("characters") or {}), dict) else {}
    for event in normalize_progression_event_list(actor_patch.get("progression_events"), actor=actor, source_turn=0):
        target_skill_id = str(event.get("target_skill_id") or "").strip()
        if target_skill_id:
            existing_event_skill_ids.add(target_skill_id)
    if candidate_skill_id in existing_event_skill_ids:
        return []

    confidence = clamp_float(0.45 + (score * 0.08), 0.0, 0.98)
    return [
        {
            "type": "skill_manifestation",
            "actor": actor,
            "target_skill_id": candidate_skill_id,
            "target_class_id": None,
            "target_element_id": None,
            "severity": "high" if score >= 6 else "medium",
            "tags": tags,
            "source_turn": int((state_after.get("meta") or {}).get("turn", 0) or 0),
            "reason": "Starke narrative Erstmanifestation",
            "metadata": {
                "origin": "inferred_story_manifestation_force" if force_first_skill else "inferred_story_manifestation",
                "manifestation_score": score,
                "manifestation_confidence": confidence,
                "motif": motif,
                "seed_eligible": bool(score >= 6),
                "first_skill_force": bool(force_first_skill),
            },
            "skill": {
                "id": candidate_skill_id,
                "name": base_name,
                "rank": "F",
                "level": 1,
                "xp": 0,
                "next_xp": next_skill_xp_for_level(1),
                "tags": tags,
                "description": first_sentences(story_text or player_text, 2)[:220] or f"{base_name} manifestiert sich erstmals unter starkem Druck.",
                "effect_summary": "Eine neue Kraftmanifestation mit klarer taktischer Wirkung.",
                "power_rating": 10,
                "growth_potential": "hoch" if score >= 6 else "mittel",
                "cost": {"resource": resource_name_for_character(character_after, ((state_after.get("world") or {}).get("settings") or {})), "amount": 2},
                "manifestation_source": "NarrativeInfer",
            },
        }
    ]

def infer_progression_events_from_patch(
    *,
    state_before: Dict[str, Any],
    state_after: Dict[str, Any],
    patch: Dict[str, Any],
    actor: str,
    action_type: str,
    player_text: str = "",
    story_text: str = "",
) -> List[Dict[str, Any]]:
    turn_number = int((state_after.get("meta") or {}).get("turn", 0) or 0)
    inferred: List[Dict[str, Any]] = []
    patch_characters = patch.get("characters") or {}

    for slot_name, upd in patch_characters.items():
        if not isinstance(upd, dict) or slot_name not in (state_after.get("characters") or {}):
            continue
        if upd.get("progression_events"):
            explicit_events = normalize_progression_event_list(
                upd.get("progression_events"),
                actor=slot_name,
                source_turn=turn_number,
            )
            for event in explicit_events:
                metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
                metadata["origin"] = "explicit_patch"
                event["metadata"] = metadata
            inferred.extend(explicit_events)
        hp_delta = int(upd.get("hp_delta", 0) or 0)
        stamina_delta = int(upd.get("stamina_delta", 0) or 0)
        res_delta_raw = 0
        if isinstance(upd.get("resources_delta"), dict):
            res_delta_raw = int(
                (upd.get("resources_delta") or {}).get("res", 0)
                or (upd.get("resources_delta") or {}).get("aether", 0)
                or 0
            )
        if hp_delta < 0 and action_type in {"do", "story", "say"}:
            inferred.append(
                {
                    "type": "combat_survival",
                    "actor": slot_name,
                    "severity": "medium" if hp_delta <= -3 else "low",
                    "reason": "Überstandene Kampffolge",
                    "source_turn": turn_number,
                    "target_skill_id": None,
                    "target_class_id": None,
                    "tags": ["combat"],
                    "metadata": {"hp_delta": hp_delta, "origin": "inferred_patch"},
                    "skill": {},
                }
            )
        if (stamina_delta < 0 or res_delta_raw < 0) and upd.get("skills_delta"):
            for skill_id in (upd.get("skills_delta") or {}).keys():
                    inferred.append(
                        {
                            "type": "skill_mastery_use",
                        "actor": slot_name,
                        "target_skill_id": str(skill_id),
                        "severity": "low",
                        "reason": "Skillnutzung unter Belastung",
                        "source_turn": turn_number,
                        "target_class_id": None,
                        "tags": ["skill_use"],
                            "metadata": {"stamina_delta": stamina_delta, "res_delta": res_delta_raw, "origin": "inferred_patch"},
                            "skill": {},
                        }
                    )
        if upd.get("class_set") or upd.get("class_update"):
            target_class_id = str(
                ((normalize_class_current(upd.get("class_set")) or (upd.get("class_update") or {})).get("id") or "")
            ).strip() or None
            inferred.append(
                {
                    "type": "class_breakthrough",
                    "actor": slot_name,
                    "target_skill_id": None,
                    "target_class_id": target_class_id,
                    "severity": "medium",
                    "reason": "Klassenfortschritt",
                    "source_turn": turn_number,
                    "tags": ["class"],
                    "metadata": {"origin": "inferred_patch"},
                    "skill": {},
                }
            )

    for plot_update in (patch.get("plotpoints_update") or []):
        if not isinstance(plot_update, dict):
            continue
        if str(plot_update.get("status") or "").strip().lower() != "done":
            continue
        inferred.append(
            {
                "type": "milestone_progress",
                "actor": actor,
                "target_skill_id": None,
                "target_class_id": None,
                "severity": "medium",
                "reason": f"Plotpoint abgeschlossen: {plot_update.get('id', '')}",
                "source_turn": turn_number,
                "tags": ["milestone"],
                "metadata": {"plotpoint_id": str(plot_update.get("id") or ""), "origin": "inferred_patch"},
                "skill": {},
            }
        )

    story_events = " ".join(str(entry or "") for entry in (patch.get("events_add") or []))
    story_norm = normalized_eval_text(story_events)
    if any(word in story_norm for word in ("boss", "erzgegner", "endgegner")) and any(
        word in story_norm for word in ("besiegt", "gefallen", "zerstoert", "zerstört")
    ):
        inferred.append(
            {
                "type": "boss_defeated",
                "actor": actor,
                "target_skill_id": None,
                "target_class_id": None,
                "severity": "high",
                "reason": "Boss wurde besiegt",
                "source_turn": turn_number,
                "tags": ["combat", "boss"],
                "metadata": {"origin": "inferred_patch"},
                "skill": {},
            }
        )
    elif any(word in story_norm for word in ("gegner", "kreatur", "feind", "monster")) and any(
        word in story_norm for word in ("besiegt", "fällt", "zerstoert", "zerstört", "ausgeschaltet")
    ):
        inferred.append(
            {
                "type": "combat_victory",
                "actor": actor,
                "target_skill_id": None,
                "target_class_id": None,
                "severity": "medium",
                "reason": "Kampfsieg",
                "source_turn": turn_number,
                "tags": ["combat"],
                "metadata": {"origin": "inferred_patch"},
                "skill": {},
            }
        )
    inferred.extend(
        infer_manifestation_progression_events_from_story(
            state_before=state_before,
            state_after=state_after,
            patch=patch,
            actor=actor,
            action_type=action_type,
            player_text=player_text,
            story_text=story_text,
        )
    )
    return inferred

def apply_progression_event_xp(
    *,
    character: Dict[str, Any],
    event: Dict[str, Any],
    world_settings: Optional[Dict[str, Any]],
    actor_slot: str,
) -> List[str]:
    messages: List[str] = []
    event_type = str(event.get("type") or "").strip().lower()
    if event_type not in PROGRESSION_EVENT_TYPES:
        return messages
    severity = normalize_progression_event_severity(event.get("severity"))
    severity_mult = PROGRESSION_EVENT_SEVERITY_MULTIPLIER.get(severity, 1.0)
    speed_mult = progression_speed_multiplier(world_settings)
    base = PROGRESSION_EVENT_BASE_XP.get(event_type, PROGRESSION_EVENT_BASE_XP["milestone_progress"])

    character_gain = max(1, int(round(base["character"] * severity_mult * speed_mult)))
    class_gain = max(0, int(round(base["class"] * severity_mult * speed_mult)))
    skill_gain = max(0, int(round(base["skill"] * severity_mult * speed_mult)))

    before_level = int(character.get("level", 1) or 1)
    apply_system_xp(character, character_gain)
    after_level = int(character.get("level", 1) or 1)
    if after_level > before_level:
        char_name = str(((character.get("bio") or {}).get("name") or actor_slot).strip())
        messages.append(f"{char_name} steigt auf Lv {after_level} auf.")

    if class_gain > 0:
        messages.extend(apply_class_xp(character, class_gain, event_reason=str(event.get("reason") or "")))

    target_skill_id = str(event.get("target_skill_id") or "").strip()
    if event_type == "skill_manifestation" and not target_skill_id:
        skill_payload = deep_copy(event.get("skill") or {})
        if isinstance(skill_payload, dict) and skill_payload.get("name"):
            target_skill_id = skill_id_from_name(str(skill_payload.get("name") or ""))
            event["target_skill_id"] = target_skill_id
    if skill_gain > 0 and target_skill_id:
        outcomes = {1: "small", 2: "normal", 3: "major"}
        bucket = 1 if severity == "low" else 2 if severity == "medium" else 3
        for _ in range(max(1, int(round(skill_gain / 12.0)))):
            messages.extend(grant_skill_xp(character, target_skill_id, outcomes[bucket], world_settings=world_settings))
    append_recent_progression_event(character, event)
    return messages

def manifest_skill_from_progression_event(
    *,
    character: Dict[str, Any],
    actor_slot: str,
    event: Dict[str, Any],
    world: Optional[Dict[str, Any]],
    world_settings: Optional[Dict[str, Any]],
) -> Optional[str]:
    if str(event.get("type") or "").strip().lower() != "skill_manifestation":
        return None
    skill_store = character.setdefault("skills", {})
    target_skill_id = str(event.get("target_skill_id") or "").strip()
    if target_skill_id and target_skill_id in skill_store:
        return None
    payload = deep_copy(event.get("skill") or {})
    if not isinstance(payload, dict) or not payload.get("name"):
        return None
    skill = canonicalize_manifested_skill_payload(
        raw_skill=payload,
        character=character,
        world=world,
        world_settings=world_settings,
        default_source=f"Progression:{event.get('type', 'skill_manifestation')}",
    )
    if not skill:
        return None
    existing = skill_store.get(skill["id"])
    skill_store[skill["id"]] = (
        merge_dynamic_skill(existing, skill, resource_name=resource_name_for_character(character, world_settings))
        if existing
        else skill
    )
    event["target_skill_id"] = skill["id"]
    char_name = str(((character.get("bio") or {}).get("name") or actor_slot).strip())
    return f"{char_name} manifestiert den neuen Skill {skill['name']} ({skill['rank']})."

def apply_progression_events(
    campaign: Dict[str, Any],
    state_before: Dict[str, Any],
    state_after: Dict[str, Any],
    patch: Dict[str, Any],
    *,
    actor: str,
    action_type: str,
    player_text: str = "",
    story_text: str = "",
) -> Dict[str, Any]:
    world_settings = ((state_after.get("world") or {}).get("settings") or {})
    world_model = state_after.get("world") if isinstance(state_after.get("world"), dict) else {}
    turn_number = int((state_after.get("meta") or {}).get("turn", 0) or 0)
    normalized_events = infer_progression_events_from_patch(
        state_before=state_before,
        state_after=state_after,
        patch=patch,
        actor=actor,
        action_type=action_type,
        player_text=player_text,
        story_text=story_text,
    )
    normalized_events = reduce_progression_event_density(
        normalized_events,
        state_after=state_after,
        action_type=action_type,
    )
    event_messages: List[str] = []
    applied_events: List[Dict[str, Any]] = []
    for raw_event in normalized_events:
        event = normalize_progression_event(raw_event, actor=actor, source_turn=turn_number)
        if not event:
            continue
        slot_name = str(event.get("actor") or "").strip()
        if slot_name not in (state_after.get("characters") or {}):
            continue
        character = (state_after.get("characters") or {}).get(slot_name) or {}
        ensure_progression_shape(character)
        ensure_character_progression_core(character)
        manifestation_msg = manifest_skill_from_progression_event(
            character=character,
            actor_slot=slot_name,
            event=event,
            world=state_after.get("world") if isinstance(state_after.get("world"), dict) else {},
            world_settings=world_settings,
        )
        if manifestation_msg:
            event_messages.append(manifestation_msg)
            metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
            if metadata.get("seed_eligible"):
                seed = manifestation_seed_from_skill(
                    event.get("skill") if isinstance(event.get("skill"), dict) else {},
                    source_turn=int(event.get("source_turn", 0) or 0),
                    confidence=float(metadata.get("manifestation_confidence", 0.0) or 0.0),
                )
                seed_message = upsert_class_path_seed(character, seed) if seed else None
                if seed_message:
                    event_messages.append(seed_message)
        event_messages.extend(
            apply_progression_event_xp(
                character=character,
                event=event,
                world_settings=world_settings,
                actor_slot=slot_name,
            )
        )
        event_type = str(event.get("type") or "").strip().lower()
        event_messages.extend(
            ensure_class_rank_core_skills(
                character,
                world_model,
                world_settings,
                unlock_extra=event_type in {"milestone_progress", "class_breakthrough", "boss_defeated", "skill_manifestation"},
            )
        )
        applied_events.append(event)
        state_after["characters"][slot_name] = character
    if event_messages:
        state_after.setdefault("events", [])
        state_after["events"].extend(event_messages)
    return {"events": applied_events, "messages": event_messages}

def build_skill_system_requests(
    campaign: Dict[str, Any],
    state_before: Dict[str, Any],
    state_after: Dict[str, Any],
) -> List[Dict[str, Any]]:
    requests: List[Dict[str, Any]] = []
    world_settings = (((state_after.get("world") or {}).get("settings") or {}))
    for slot_name, after_character in (state_after.get("characters") or {}).items():
        before_character = ((state_before.get("characters") or {}).get(slot_name) or {})
        before_level = int(before_character.get("level", 1) or 1)
        after_level = int(after_character.get("level", 1) or 1)
        if after_level > before_level:
            requests.append(
                {
                    "type": "clarify",
                    "actor": slot_name,
                    "question": f"Neues Level erreicht ({after_level}). Soll der Fokus als nächstes eher auf Klasse oder Skill-Meisterung liegen?",
                }
            )
        before_class = normalize_class_current(before_character.get("class_current"))
        after_class = normalize_class_current(after_character.get("class_current"))
        if after_class and (not before_class or int(after_class.get("level", 1) or 1) > int((before_class or {}).get("level", 1) or 1)):
            requests.append(
                {
                    "type": "choice",
                    "actor": slot_name,
                    "question": f"Klassenfortschritt für {after_class.get('name', 'Klasse')}: Welche Richtung soll gestärkt werden?",
                    "options": ["Offensive Schärfung", "Defensive Stabilität", "Ressourcenkontrolle", "Eigener Plan"],
                }
            )
        skill_hints = build_skill_fusion_hints(after_character.get("skills") or {}, resource_name=resource_name_for_character(after_character, world_settings))
        if skill_hints:
            top_hint = skill_hints[0]
            requests.append(
                {
                    "type": "choice",
                    "actor": slot_name,
                    "question": f"{top_hint.get('label')} Soll der Erzähler eine Evolution erzählerisch vorbereiten?",
                    "options": ["Ja, vorbereiten", "Nein, vorerst nicht", "Eigener Plan"],
                }
            )
            break
    return requests[:2]

def apply_skill_events(campaign: Dict[str, Any], state: Dict[str, Any], events: List[str]) -> List[str]:
    messages: List[str] = []
    for event_text in (events or []):
        parsed = parse_skill_event(campaign, str(event_text or ""))
        if not parsed:
            continue
        actor = parsed.get("actor", "")
        skill_name = parsed.get("skill", "")
        outcome = parsed.get("outcome", "normal")
        if actor not in (state.get("characters") or {}):
            continue
        character = (state.get("characters") or {}).get(actor) or {}
        messages.extend(grant_skill_xp(character, skill_name, outcome, world_settings=((state.get("world") or {}).get("settings") or {})))
        (state.get("characters") or {})[actor] = character
    return messages

def rebuild_character_derived(character: Dict[str, Any], items_db: Dict[str, Any], world_time: Optional[Dict[str, Any]] = None) -> None:
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

def migrate_effects_from_conditions(character: Dict[str, Any]) -> None:
    effects = character.setdefault("effects", [])
    existing = {effect.get("name") for effect in effects}
    for condition in character.get("conditions", []) or []:
        if condition and condition not in existing:
            effects.append(
                {
                    "id": make_id("effect"),
                    "name": condition,
                    "category": "condition",
                    "tags": [],
                    "description": condition,
                    "duration_turns": 0,
                    "intensity": 1,
                    "modifiers": [],
                    "source": "legacy_condition",
                    "visible": True,
                }
            )

def normalize_character_state(
    character: Dict[str, Any],
    slot_name: str,
    items_db: Dict[str, Any],
    world_time: Optional[Dict[str, Any]] = None,
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
    return merged

def rebuild_all_character_derived(campaign: Dict[str, Any]) -> None:
    items_db = campaign.get("state", {}).get("items", {}) or {}
    world_time = normalize_world_time(campaign.get("state", {}).get("meta", {}))
    for slot_name, character in (campaign.get("state", {}).get("characters") or {}).items():
        campaign["state"]["characters"][slot_name] = normalize_character_state(character, slot_name, items_db, world_time)

def derive_scene_name(campaign: Dict[str, Any], slot_name: str) -> str:
    scene_id = (campaign.get("state", {}).get("characters", {}).get(slot_name) or {}).get("scene_id", "")
    if not scene_id:
        return "Kein Ort"
    scenes = campaign.get("state", {}).get("scenes", {}) or {}
    if scene_id in scenes and scenes[scene_id].get("name"):
        scene_name = str(scenes[scene_id]["name"] or "").strip()
        if is_generic_scene_identifier(scene_id, scene_name):
            return "Ort: ???"
        return scene_name
    nodes = (campaign.get("state", {}).get("map", {}).get("nodes") or {})
    if scene_id in nodes and nodes[scene_id].get("name"):
        scene_name = str(nodes[scene_id]["name"] or "").strip()
        if is_generic_scene_identifier(scene_id, scene_name):
            return "Ort: ???"
        return scene_name
    if is_generic_scene_identifier(scene_id, ""):
        return "Ort: ???"
    return scene_id

def build_world_question_queue() -> List[str]:
    required = [entry["id"] for entry in WORLD_FORM_CATALOG if entry.get("required")]
    optional = [entry["id"] for entry in WORLD_FORM_CATALOG if not entry.get("required")]
    return required + optional

def build_character_question_queue() -> List[str]:
    required = [entry["id"] for entry in CHARACTER_FORM_CATALOG if entry.get("required")]
    optional = [entry["id"] for entry in CHARACTER_FORM_CATALOG if not entry.get("required")]
    return required + optional

def default_setup() -> Dict[str, Any]:
    return {
        "version": 4,
        "engine": {
            "world_catalog_version": CATALOG_VERSION,
            "character_catalog_version": CATALOG_VERSION,
        },
        "world": {
            "completed": False,
            "question_queue": build_world_question_queue(),
            "answers": {},
            "summary": {},
            "raw_transcript": [],
            "question_runtime": {},
        },
        "characters": {},
    }

def normalize_answer_summary_defaults() -> Dict[str, Any]:
    return {
        "premise": "",
        "tone": "",
        "difficulty": "",
        "death_policy": "",
        "death_possible": True,
        "ruleset": "",
        "outcome_model": "",
        "world_structure": "",
        "world_laws": [],
        "central_conflict": "",
        "factions": [],
        "taboos": "",
        "player_count": 0,
        "resource_scarcity": "",
        "healing_frequency": "",
        "monsters_density": "",
        "theme": "",
        "attribute_range_label": "1-10",
        "attribute_range_min": 1,
        "attribute_range_max": 10,
        "resource_name": "Aether",
        "consequence_severity": "hoch",
        "progression_speed": "normal",
        "evolution_cost_policy": "leicht",
        "offclass_xp_multiplier": 0.7,
        "onclass_xp_multiplier": 1.0,
        "campaign_length": "medium",
        "target_turns": deep_copy(TARGET_TURNS_DEFAULTS),
        "pacing_profile": deep_copy(PACING_PROFILE_DEFAULTS),
    }

def default_campaign_length_settings() -> Dict[str, Any]:
    return {
        "campaign_length": "medium",
        "target_turns": deep_copy(TARGET_TURNS_DEFAULTS),
        "pacing_profile": deep_copy(PACING_PROFILE_DEFAULTS),
    }

def default_meta_timing() -> Dict[str, Any]:
    return deep_copy(TIMING_DEFAULTS)

def clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value)))

def default_combat_meta() -> Dict[str, Any]:
    return {
        "active": False,
        "combat_id": "",
        "round": 0,
        "phase": "idle",
        "action_queue": [],
        "participants": [],
        "last_resolution": {},
        "updated_at": utc_now(),
    }

def default_attribute_influence_meta() -> Dict[str, Any]:
    return {
        "last_turn": 0,
        "last_actor": "",
        "last_profile": {
            "primary_attributes": [],
            "influence_tier": "none",
            "narrative_bias": [],
            "mechanical_bias": {
                "damage_taken_mult": 1.0,
                "cost_mult": 1.0,
                "complication_mult": 1.0,
                "outgoing_effect_mult": 1.0,
            },
        },
    }

def default_extraction_quarantine() -> Dict[str, Any]:
    return {
        "entries": [],
        "max_entries": EXTRACTION_QUARANTINE_DEFAULT_MAX,
    }

def normalize_extraction_quarantine_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    raw = meta.get("extraction_quarantine")
    quarantine = deep_copy(raw) if isinstance(raw, dict) else default_extraction_quarantine()
    max_entries = int(quarantine.get("max_entries", EXTRACTION_QUARANTINE_DEFAULT_MAX) or EXTRACTION_QUARANTINE_DEFAULT_MAX)
    max_entries = clamp(max_entries, 1, 1000)
    entries: List[Dict[str, Any]] = []
    for raw_entry in (quarantine.get("entries") or []):
        if not isinstance(raw_entry, dict):
            continue
        status = str(raw_entry.get("status") or "").strip().lower()
        if status not in {"review", "reject"}:
            continue
        normalized_entry = {
            "id": str(raw_entry.get("id") or make_id("xq")).strip(),
            "turn": max(0, int(raw_entry.get("turn", 0) or 0)),
            "actor": str(raw_entry.get("actor") or "").strip(),
            "source": str(raw_entry.get("source") or "unknown").strip(),
            "entity_type": str(raw_entry.get("entity_type") or "unknown").strip(),
            "status": status,
            "reason_code": str(raw_entry.get("reason_code") or EXTRACTION_REASON_LOW_CONFIDENCE).strip(),
            "label": str(raw_entry.get("label") or "").strip(),
            "payload": deep_copy(raw_entry.get("payload") or {}),
            "created_at": str(raw_entry.get("created_at") or utc_now()),
        }
        entries.append(normalized_entry)
    if len(entries) > max_entries:
        entries = entries[-max_entries:]
    normalized = {"entries": entries, "max_entries": max_entries}
    meta["extraction_quarantine"] = normalized
    return normalized

def normalize_meta_migrations(meta: Dict[str, Any]) -> Dict[str, Any]:
    raw = meta.get("migrations")
    migrations = deep_copy(raw) if isinstance(raw, dict) else {}
    migrations["npc_codex_seeded_from_story_cards"] = bool(migrations.get("npc_codex_seeded_from_story_cards", False))
    meta["migrations"] = migrations
    return migrations

def normalize_world_settings(world_settings: Any) -> Dict[str, Any]:
    normalized = deep_copy(world_settings or {})
    defaults = default_campaign_length_settings()
    normalized["resource_name"] = normalize_resource_name(normalized.get("resource_name", "Aether"), "Aether")
    normalized["consequence_severity"] = str(normalized.get("consequence_severity", "mittel") or "mittel")
    if normalized["consequence_severity"] not in {"mittel", "hoch", "brutal"}:
        normalized["consequence_severity"] = "mittel"
    normalized["progression_speed"] = str(normalized.get("progression_speed", "normal") or "normal")
    if normalized["progression_speed"] not in {"langsam", "normal", "schnell"}:
        normalized["progression_speed"] = "normal"
    normalized["evolution_cost_policy"] = str(normalized.get("evolution_cost_policy", "leicht") or "leicht")
    if normalized["evolution_cost_policy"] not in {"gratis", "leicht", "hart"}:
        normalized["evolution_cost_policy"] = "leicht"
    normalized["offclass_xp_multiplier"] = clamp_float(float(normalized.get("offclass_xp_multiplier", 0.7) or 0.7), 0.1, 1.0)
    normalized["onclass_xp_multiplier"] = clamp_float(float(normalized.get("onclass_xp_multiplier", 1.0) or 1.0), 0.5, 2.0)
    campaign_length = str(normalized.get("campaign_length") or defaults["campaign_length"]).strip().lower()
    if campaign_length not in CAMPAIGN_LENGTHS:
        campaign_length = defaults["campaign_length"]
    normalized["campaign_length"] = campaign_length

    target_turns = deep_copy(defaults["target_turns"])
    for key in CAMPAIGN_LENGTHS:
        if key in (normalized.get("target_turns") or {}):
            raw = (normalized.get("target_turns") or {}).get(key)
            target_turns[key] = None if raw is None else max(1, int(raw or target_turns[key] or 1))
    target_turns["open"] = None
    normalized["target_turns"] = target_turns

    pacing = deep_copy(defaults["pacing_profile"])
    existing_pacing = normalized.get("pacing_profile") or {}
    for key in CAMPAIGN_LENGTHS:
        row = pacing[key]
        current = existing_pacing.get(key) if isinstance(existing_pacing, dict) else {}
        if not isinstance(current, dict):
            current = {}
        row["beats_per_turn"] = max(1, int(current.get("beats_per_turn", row["beats_per_turn"]) or row["beats_per_turn"]))
        row["detail_level"] = str(current.get("detail_level", row["detail_level"]) or row["detail_level"])
        row["plot_density"] = str(current.get("plot_density", row["plot_density"]) or row["plot_density"])
        sideplot_raw = current.get("sideplot_limit", row["sideplot_limit"])
        row["sideplot_limit"] = None if sideplot_raw is None else max(0, int(sideplot_raw or 0))
        row["milestone_every_n_turns"] = max(1, int(current.get("milestone_every_n_turns", row["milestone_every_n_turns"]) or row["milestone_every_n_turns"]))
        row["min_story_chars"] = max(300, int(current.get("min_story_chars", row["min_story_chars"]) or row["min_story_chars"]))
        row["max_story_chars"] = max(row["min_story_chars"], int(current.get("max_story_chars", row["max_story_chars"]) or row["max_story_chars"]))
    normalized["pacing_profile"] = pacing
    return normalized

def normalize_meta_timing(meta: Dict[str, Any]) -> Dict[str, Any]:
    timing = deep_copy(meta.get("timing") or default_meta_timing())
    defaults = default_meta_timing()
    for key in ("ai_latency_ema_sec", "player_latency_ema_sec", "cycle_ema_sec"):
        timing[key] = float(timing.get(key, defaults[key]) or defaults[key])
    for key in ("turns_target_est", "turns_left_est"):
        raw = timing.get(key, defaults[key])
        timing[key] = None if raw is None else max(0, int(raw))
    raw_last = timing.get("last_response_ready_ts", defaults["last_response_ready_ts"])
    timing["last_response_ready_ts"] = None if raw_last in (None, "") else float(raw_last)
    meta["timing"] = timing
    return timing

def normalize_combat_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    combat = deep_copy(meta.get("combat") or default_combat_meta())
    defaults = default_combat_meta()
    combat["active"] = bool(combat.get("active", defaults["active"]))
    combat["combat_id"] = str(combat.get("combat_id") or "").strip()
    combat["round"] = max(0, int(combat.get("round", defaults["round"]) or defaults["round"]))
    phase = str(combat.get("phase") or defaults["phase"]).strip().lower()
    combat["phase"] = phase if phase in {"idle", "collecting", "resolving", "ended"} else defaults["phase"]
    combat["participants"] = [str(entry).strip() for entry in (combat.get("participants") or []) if str(entry).strip()]
    queue_entries: List[Dict[str, Any]] = []
    for raw in (combat.get("action_queue") or []):
        if not isinstance(raw, dict):
            continue
        actor = str(raw.get("actor") or "").strip()
        action_type = str(raw.get("action_type") or "").strip().lower()
        if not actor or action_type not in ACTION_TYPES:
            continue
        queue_entries.append(
            {
                "turn": max(0, int(raw.get("turn", 0) or 0)),
                "actor": actor,
                "action_type": action_type,
                "summary": str(raw.get("summary") or "").strip(),
                "created_at": str(raw.get("created_at") or utc_now()),
            }
        )
    combat["action_queue"] = queue_entries[-20:]
    combat["last_resolution"] = deep_copy(combat.get("last_resolution") or {})
    combat["updated_at"] = str(combat.get("updated_at") or utc_now())
    meta["combat"] = combat
    return combat

def normalize_attribute_influence_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    influence = deep_copy(meta.get("attribute_influence") or default_attribute_influence_meta())
    defaults = default_attribute_influence_meta()
    influence["last_turn"] = max(0, int(influence.get("last_turn", defaults["last_turn"]) or defaults["last_turn"]))
    influence["last_actor"] = str(influence.get("last_actor") or defaults["last_actor"]).strip()
    profile = deep_copy(influence.get("last_profile") or defaults["last_profile"])
    tier = str(profile.get("influence_tier") or "none").strip().lower()
    if tier not in {"none", "low", "medium", "high"}:
        tier = "none"
    profile["influence_tier"] = tier
    profile["primary_attributes"] = [
        str(entry).strip().lower()
        for entry in (profile.get("primary_attributes") or [])
        if str(entry).strip().lower() in ATTRIBUTE_KEYS
    ]
    profile["narrative_bias"] = [str(entry).strip() for entry in (profile.get("narrative_bias") or []) if str(entry).strip()]
    raw_mechanical = profile.get("mechanical_bias") if isinstance(profile.get("mechanical_bias"), dict) else {}
    profile["mechanical_bias"] = {
        "damage_taken_mult": clamp_float(float(raw_mechanical.get("damage_taken_mult", 1.0) or 1.0), 0.65, 1.35),
        "cost_mult": clamp_float(float(raw_mechanical.get("cost_mult", 1.0) or 1.0), 0.65, 1.35),
        "complication_mult": clamp_float(float(raw_mechanical.get("complication_mult", 1.0) or 1.0), 0.65, 1.35),
        "outgoing_effect_mult": clamp_float(float(raw_mechanical.get("outgoing_effect_mult", 1.0) or 1.0), 0.65, 1.35),
    }
    influence["last_profile"] = profile
    meta["attribute_influence"] = influence
    return influence

def active_pacing_profile(state: Dict[str, Any]) -> Dict[str, Any]:
    settings = normalize_world_settings(((state.get("world") or {}).get("settings") or {}))
    selected = str(settings.get("campaign_length") or "medium").lower()
    if selected not in CAMPAIGN_LENGTHS:
        selected = "medium"
    profile = deep_copy((settings.get("pacing_profile") or {}).get(selected) or PACING_PROFILE_DEFAULTS[selected])
    profile["campaign_length"] = selected
    profile["target_turn"] = (settings.get("target_turns") or {}).get(selected)
    return profile

def compute_turn_budget_estimates(state: Dict[str, Any]) -> Dict[str, Any]:
    meta = state.setdefault("meta", {})
    timing = normalize_meta_timing(meta)
    settings = normalize_world_settings(((state.get("world") or {}).get("settings") or {}))
    selected = str(settings.get("campaign_length") or "medium").lower()
    target_lookup = settings.get("target_turns") or {}
    target_turns = target_lookup.get(selected)
    if selected == "open":
        timing["turns_target_est"] = None
        timing["turns_left_est"] = None
    else:
        fallback_target = TARGET_TURNS_DEFAULTS["short"] if selected == "short" else TARGET_TURNS_DEFAULTS["medium"]
        target = max(1, int(target_turns or fallback_target))
        current_turn = int(meta.get("turn", 0) or 0)
        timing["turns_target_est"] = target
        timing["turns_left_est"] = max(0, target - current_turn)
    timing["cycle_ema_sec"] = float(timing.get("ai_latency_ema_sec", TIMING_DEFAULTS["ai_latency_ema_sec"])) + float(
        timing.get("player_latency_ema_sec", TIMING_DEFAULTS["player_latency_ema_sec"])
    )
    return timing

def update_turn_timing_ema(state: Dict[str, Any], request_ts: float, response_ts: float) -> Dict[str, Any]:
    timing = normalize_meta_timing(state.setdefault("meta", {}))
    ai_latency = clamp_float(float(response_ts - request_ts), AI_LATENCY_CLAMP[0], AI_LATENCY_CLAMP[1])
    timing["ai_latency_ema_sec"] = (
        (1.0 - TIMING_EMA_ALPHA) * float(timing.get("ai_latency_ema_sec", TIMING_DEFAULTS["ai_latency_ema_sec"]))
        + TIMING_EMA_ALPHA * ai_latency
    )

    last_response = timing.get("last_response_ready_ts")
    if last_response is not None:
        player_latency = clamp_float(float(request_ts - float(last_response)), PLAYER_LATENCY_CLAMP[0], PLAYER_LATENCY_CLAMP[1])
        timing["player_latency_ema_sec"] = (
            (1.0 - TIMING_EMA_ALPHA) * float(timing.get("player_latency_ema_sec", TIMING_DEFAULTS["player_latency_ema_sec"]))
            + TIMING_EMA_ALPHA * player_latency
        )
    timing["last_response_ready_ts"] = float(response_ts)
    timing["cycle_ema_sec"] = float(timing.get("ai_latency_ema_sec", 0.0)) + float(timing.get("player_latency_ema_sec", 0.0))
    return timing

def milestone_state_for_turn(turn_number: int, profile: Dict[str, Any]) -> Dict[str, int | bool]:
    every = max(1, int(profile.get("milestone_every_n_turns", 18) or 18))
    current_turn = max(0, int(turn_number or 0))
    if current_turn <= 0:
        return {"is_milestone": False, "last": 0, "next": every}
    is_milestone = current_turn % every == 0
    last = current_turn if is_milestone else (current_turn // every) * every
    next_turn = current_turn + every if is_milestone else last + every
    return {"is_milestone": is_milestone, "last": last, "next": max(next_turn, every)}

def build_pacing_instruction_block(state: Dict[str, Any]) -> Dict[str, Any]:
    profile = active_pacing_profile(state)
    milestone = milestone_state_for_turn(int((state.get("meta") or {}).get("turn", 0) or 0), profile)
    lines = [
        "PACING INSTRUCTIONS:",
        f"- campaign_length={profile.get('campaign_length')}",
        f"- beats_per_turn={int(profile.get('beats_per_turn', 2) or 2)}",
        f"- detail_level={profile.get('detail_level', 'medium')}",
        f"- plot_density={profile.get('plot_density', 'medium')}",
        f"- sideplot_limit={profile.get('sideplot_limit', 'null')}",
        f"- milestone_every_n_turns={int(profile.get('milestone_every_n_turns', 18) or 18)}",
        f"- min_story_chars={int(profile.get('min_story_chars', 800) or 800)}",
        f"- max_story_chars={int(profile.get('max_story_chars', 2200) or 2200)}",
        f"- is_milestone_turn={'yes' if milestone['is_milestone'] else 'no'}",
    ]
    if profile.get("campaign_length") == "short":
        lines.extend(
            [
                "- Für SHORT: 3 Beats zwingend (Setup -> Konsequenz -> Eskalation) plus klarer Entscheidungspunkt.",
                "- Antworte mit 2-4 konkreten Optionen und zusätzlich 'eigener Plan'.",
                "- Weniger Kulissenbeschreibung, mehr sichtbarer Plot-Fortschritt pro Turn.",
            ]
        )
    lines.extend(
        [
            "- Die story muss mindestens min_story_chars Zeichen haben.",
            "- Wiederhole keine vorherigen Absätze.",
            "- Große Progressionssprünge (Ascension, Rank-Sprung, neue A/S-Skills) sind nur auf Milestone-Turns erlaubt.",
        ]
    )
    return {
        "profile": profile,
        "milestone": milestone,
        "text": "\n".join(lines),
    }

def _hash_unit_interval(seed_text: str) -> float:
    digest = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:12]
    value = int(digest, 16)
    return (value % 10_000) / 10_000.0

def derive_attribute_relevance(
    state: Dict[str, Any],
    actor: str,
    action_type: str,
    text: str,
    combat_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    character = ((state.get("characters") or {}).get(actor) or {})
    attrs = character.get("attributes", {}) or {}
    normalized_text = normalized_eval_text(text)
    combat_active = bool((combat_context or {}).get("active") or (combat_context or {}).get("hinted"))

    keyword_map = {
        "str": ("schlag", "drücken", "kraft", "klinge", "hieb", "werfen", "reißen"),
        "dex": ("ausweichen", "springen", "schnell", "präzise", "treffer", "klettern", "balanc"),
        "con": ("aushalten", "einstecken", "standhaft", "zäh", "widerstand", "durchhalten"),
        "int": ("analys", "plan", "taktik", "berechnen", "runen", "technik", "formel"),
        "wis": ("spüren", "ahnung", "instinkt", "warnung", "wahrnehmen", "ruhe"),
        "cha": ("überzeugen", "drohen", "verhandeln", "reden", "bluff", "anführen"),
        "luck": ("zufall", "glück", "fund", "zufällig", "knapp", "unerwartet", "gerade noch"),
    }

    scored: List[tuple[float, str]] = []
    for key in ATTRIBUTE_KEYS:
        base = float(int(attrs.get(key, 0) or 0))
        score = base
        if combat_active and key in {"str", "dex", "con", "luck"}:
            score += 2.0
        if action_type == "say" and key in {"cha", "wis", "luck"}:
            score += 2.5
        if action_type == "story" and key in {"int", "wis", "luck"}:
            score += 1.5
        for keyword in keyword_map.get(key, ()):
            if keyword in normalized_text:
                score += 2.2
        scored.append((score, key))

    scored.sort(key=lambda entry: (entry[0], int(attrs.get(entry[1], 0) or 0)), reverse=True)
    primary_attributes = [entry[1] for entry in scored[:2] if entry[0] > 0]
    if not primary_attributes:
        primary_attributes = ["luck"]

    roll = _hash_unit_interval(f"{int((state.get('meta') or {}).get('turn', 0) or 0)}|{actor}|{action_type}|{normalized_text[:180]}")
    cursor = 0.0
    tier = "none"
    for label, probability in ATTRIBUTE_INFLUENCE_DISTRIBUTION:
        cursor += probability
        if roll <= cursor:
            tier = label
            break

    narrative_bias: List[str] = []
    if "luck" in primary_attributes:
        narrative_bias.append("fortunate_timing" if int(attrs.get("luck", 0) or 0) >= 5 else "ill_timing")
    if "dex" in primary_attributes:
        narrative_bias.append("tempo_shift")
    if "con" in primary_attributes:
        narrative_bias.append("pain_tolerance")
    if "cha" in primary_attributes:
        narrative_bias.append("social_pressure")
    if "int" in primary_attributes:
        narrative_bias.append("tactical_read")
    if "wis" in primary_attributes:
        narrative_bias.append("hazard_sense")
    if "str" in primary_attributes:
        narrative_bias.append("force_spike")

    return {
        "primary_attributes": primary_attributes,
        "influence_tier": tier,
        "narrative_bias": narrative_bias[:3],
        "combat_active": combat_active,
    }

def compute_attribute_bias(profile: Dict[str, Any], character: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
    attrs = (character or {}).get("attributes", {}) or {}
    tier = str((profile or {}).get("influence_tier") or "none").lower()
    strength = ATTRIBUTE_INFLUENCE_STRENGTH.get(tier, 0.0)
    attr_cap = max(10, max((int(attrs.get(key, 0) or 0) for key in ATTRIBUTE_KEYS), default=10))
    primary = [key for key in ((profile or {}).get("primary_attributes") or []) if key in ATTRIBUTE_KEYS]

    bias = {
        "damage_taken_mult": 1.0,
        "cost_mult": 1.0,
        "complication_mult": 1.0,
        "outgoing_effect_mult": 1.0,
    }
    if strength <= 0 or not primary:
        return bias

    for key in primary:
        value = clamp(int(attrs.get(key, 0) or 0), 0, attr_cap)
        normalized = value / float(attr_cap)
        if key == "luck":
            bias["damage_taken_mult"] -= (0.18 * strength * normalized)
            bias["cost_mult"] -= (0.14 * strength * normalized)
            bias["complication_mult"] -= (0.30 * strength * normalized)
            bias["outgoing_effect_mult"] += (0.10 * strength * normalized)
            if value <= max(1, int(attr_cap * 0.25)) and tier in {"medium", "high"}:
                bias["complication_mult"] += (0.22 * strength)
        elif key == "con":
            bias["damage_taken_mult"] -= (0.26 * strength * normalized)
            bias["cost_mult"] -= (0.08 * strength * normalized)
        elif key == "dex":
            bias["damage_taken_mult"] -= (0.14 * strength * normalized)
            bias["complication_mult"] -= (0.16 * strength * normalized)
            bias["outgoing_effect_mult"] += (0.08 * strength * normalized)
        elif key == "str":
            bias["outgoing_effect_mult"] += (0.20 * strength * normalized)
            bias["cost_mult"] += (0.04 * strength * (1.0 - normalized))
        elif key == "int":
            bias["outgoing_effect_mult"] += (0.18 * strength * normalized)
            bias["cost_mult"] -= (0.10 * strength * normalized)
        elif key == "wis":
            bias["complication_mult"] -= (0.14 * strength * normalized)
            bias["cost_mult"] -= (0.08 * strength * normalized)
            bias["outgoing_effect_mult"] += (0.06 * strength * normalized)
        elif key == "cha":
            bias["complication_mult"] -= (0.08 * strength * normalized)
            bias["outgoing_effect_mult"] += (0.10 * strength * normalized)

    for key in tuple(bias.keys()):
        bias[key] = clamp_float(float(bias[key]), 0.65, 1.35)
    return bias

def compose_attribute_prompt_hints(profile: Dict[str, Any], bias: Dict[str, float]) -> str:
    attrs = ", ".join(str(entry).upper() for entry in (profile.get("primary_attributes") or [])) or "LUCK"
    narrative = ", ".join(profile.get("narrative_bias") or []) or "keine"
    tier = str(profile.get("influence_tier") or "none")
    return (
        "ATTRIBUTE INFLUENCE:\n"
        f"- primary_attributes={attrs}\n"
        f"- influence_tier={tier}\n"
        f"- narrative_bias={narrative}\n"
        f"- mechanical_bias.damage_taken_mult={bias.get('damage_taken_mult', 1.0):.2f}\n"
        f"- mechanical_bias.cost_mult={bias.get('cost_mult', 1.0):.2f}\n"
        f"- mechanical_bias.complication_mult={bias.get('complication_mult', 1.0):.2f}\n"
        f"- mechanical_bias.outgoing_effect_mult={bias.get('outgoing_effect_mult', 1.0):.2f}\n"
        "- Attributwirkung muss im story-Text konkret sichtbar sein (kein abstraktes Meta-Gerede)."
    )

def apply_attribute_bias_to_resolution(resolution: Dict[str, Any], numeric_bias: Dict[str, float]) -> Dict[str, Any]:
    adjusted = deep_copy(resolution or {})
    if "damage_taken" in adjusted:
        adjusted["damage_taken"] = int(round(float(adjusted.get("damage_taken", 0) or 0) * float(numeric_bias.get("damage_taken_mult", 1.0))))
    if "cost" in adjusted:
        adjusted["cost"] = int(round(float(adjusted.get("cost", 0) or 0) * float(numeric_bias.get("cost_mult", 1.0))))
    if "complication" in adjusted:
        adjusted["complication"] = int(round(float(adjusted.get("complication", 0) or 0) * float(numeric_bias.get("complication_mult", 1.0))))
    if "outgoing_effect" in adjusted:
        adjusted["outgoing_effect"] = int(round(float(adjusted.get("outgoing_effect", 0) or 0) * float(numeric_bias.get("outgoing_effect_mult", 1.0))))
    return adjusted

def _scale_negative_delta(value: int, multiplier: float) -> int:
    number = int(value or 0)
    if number >= 0:
        return number
    scaled = int(round(number * float(multiplier)))
    if scaled == 0:
        return -1
    return scaled

def apply_attribute_bias_to_patch(
    patch: Dict[str, Any],
    actor: str,
    numeric_bias: Dict[str, float],
) -> tuple[Dict[str, Any], Dict[str, int]]:
    adjusted = deep_copy(patch or blank_patch())
    per_actor = (adjusted.get("characters") or {}).get(actor)
    if not isinstance(per_actor, dict):
        return adjusted, {}

    applied: Dict[str, int] = {"hp_delta": 0, "stamina_delta": 0, "res_delta": 0}
    damage_mult = float(numeric_bias.get("damage_taken_mult", 1.0))
    cost_mult = float(numeric_bias.get("cost_mult", 1.0))

    if "hp_delta" in per_actor:
        before = int(per_actor.get("hp_delta", 0) or 0)
        after = _scale_negative_delta(before, damage_mult)
        per_actor["hp_delta"] = after
        applied["hp_delta"] += after - before
    if "stamina_delta" in per_actor:
        before = int(per_actor.get("stamina_delta", 0) or 0)
        after = _scale_negative_delta(before, cost_mult)
        per_actor["stamina_delta"] = after
        applied["stamina_delta"] += after - before

    resources_delta = per_actor.get("resources_delta") if isinstance(per_actor.get("resources_delta"), dict) else {}
    if resources_delta:
        for key in tuple(resources_delta.keys()):
            raw = int(resources_delta.get(key, 0) or 0)
            if key in {"hp"}:
                scaled = _scale_negative_delta(raw, damage_mult)
                applied["hp_delta"] += scaled - raw
                resources_delta[key] = scaled
            elif key in {"stamina", "sta", "aether", "res"}:
                scaled = _scale_negative_delta(raw, cost_mult)
                if key in {"stamina", "sta"}:
                    applied["stamina_delta"] += scaled - raw
                else:
                    applied["res_delta"] += scaled - raw
                resources_delta[key] = scaled
        per_actor["resources_delta"] = resources_delta
    adjusted["characters"][actor] = per_actor
    applied = {key: value for key, value in applied.items() if value}
    return adjusted, applied

def infer_skill_cost_deltas_from_text(
    state: Dict[str, Any],
    actor: str,
    action_type: str,
    source_text: str,
    *,
    combat_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if action_type == "canon":
        return {"deltas": {}, "skills": []}
    if not source_text or not ((combat_context or {}).get("active") or (combat_context or {}).get("hinted")):
        return {"deltas": {}, "skills": []}
    character = ((state.get("characters") or {}).get(actor) or {})
    world_settings = ((state.get("world") or {}).get("settings") or {})
    resource_name = resource_name_for_character(character, world_settings)
    normalized_text = normalized_eval_text(source_text)
    deltas = {"sta": 0, "res": 0}
    matched_skills: List[str] = []
    usage_hints = {"nutzt", "setzt", "wirkt", "aktiviert", "entfesselt", "kanalisiert", "schlägt", "attackiert"}
    if not any(hint in normalized_text for hint in usage_hints):
        return {"deltas": {}, "skills": []}

    for raw_skill in (character.get("skills") or {}).values():
        if not isinstance(raw_skill, dict):
            continue
        skill = normalize_dynamic_skill_state(raw_skill, resource_name=resource_name)
        cost = skill.get("cost")
        if not isinstance(cost, dict):
            continue
        amount = max(0, int(cost.get("amount", 0) or 0))
        if amount <= 0:
            continue
        name_norm = normalized_eval_text(skill.get("name", ""))
        if not name_norm:
            continue
        name_tokens = [token for token in name_norm.split() if len(token) >= 4]
        used = name_norm in normalized_text or (name_tokens and all(token in normalized_text for token in name_tokens[:2]))
        if not used:
            continue
        cost_resource = normalized_eval_text(cost.get("resource", resource_name))
        if cost_resource in {"stamina", "ausdauer", "sta"}:
            deltas["sta"] -= amount
        else:
            deltas["res"] -= amount
        matched_skills.append(str(skill.get("name") or skill.get("id")))
        if len(matched_skills) >= 2:
            break
    return {"deltas": {key: value for key, value in deltas.items() if value}, "skills": matched_skills}

def apply_skill_cost_deltas_to_patch(patch: Dict[str, Any], actor: str, delta_payload: Dict[str, Any]) -> Dict[str, Any]:
    deltas = delta_payload.get("deltas") if isinstance(delta_payload, dict) else {}
    if not isinstance(deltas, dict) or not deltas:
        return patch
    adjusted = deep_copy(patch or blank_patch())
    slot_patch = adjusted.setdefault("characters", {}).setdefault(actor, {})
    resources_delta = slot_patch.setdefault("resources_delta", {})
    for key, value in deltas.items():
        resources_delta[key] = int(resources_delta.get(key, 0) or 0) + int(value or 0)
    return adjusted

def skill_rank_power_weight(rank: str) -> int:
    return {"F": 1, "E": 2, "D": 3, "C": 4, "B": 5, "A": 7, "S": 9}.get(normalize_skill_rank(rank), 1)

def entity_element_profile_for_character(character: Dict[str, Any], world: Dict[str, Any]) -> Dict[str, List[str]]:
    class_current = normalize_class_current(character.get("class_current")) or {}
    class_element = resolve_class_element_id(class_current, world)
    affinities = normalize_element_id_list(
        [*(character.get("element_affinities") or []), *(class_current.get("element_tags") or []), class_element],
        world,
    )
    resistances = normalize_element_id_list(character.get("element_resistances") or [], world)
    weaknesses = normalize_element_id_list(character.get("element_weaknesses") or [], world)
    return {"affinities": affinities, "resistances": resistances, "weaknesses": weaknesses}

def entity_element_profile_for_npc(npc_entry: Dict[str, Any], world: Dict[str, Any]) -> Dict[str, List[str]]:
    class_current = normalize_class_current(npc_entry.get("class_current")) or {}
    class_element = resolve_class_element_id(class_current, world)
    affinities = normalize_element_id_list(
        [*(npc_entry.get("element_affinities") or []), *(class_current.get("element_tags") or []), class_element],
        world,
    )
    resistances = normalize_element_id_list(npc_entry.get("element_resistances") or [], world)
    weaknesses = normalize_element_id_list(npc_entry.get("element_weaknesses") or [], world)
    return {"affinities": affinities, "resistances": resistances, "weaknesses": weaknesses}

def element_matchup_multiplier(world: Dict[str, Any], attacker_profile: Dict[str, List[str]], defender_profile: Dict[str, List[str]]) -> float:
    attacker = attacker_profile.get("affinities") or []
    defender_affinities = defender_profile.get("affinities") or []
    defender_resistances = set(defender_profile.get("resistances") or [])
    defender_weaknesses = set(defender_profile.get("weaknesses") or [])
    if not attacker:
        return 1.0
    multipliers: List[float] = []
    for source in attacker:
        # relation to defender affinities
        for target in defender_affinities:
            relation = resolve_element_relation(world, source, target)
            multipliers.append(ELEMENT_RELATION_SCORE.get(relation, 1.0))
        # explicit defender resistance/weakness tags
        if source in defender_resistances:
            multipliers.append(0.85)
        if source in defender_weaknesses:
            multipliers.append(1.15)
    if not multipliers:
        return 1.0
    avg = sum(multipliers) / max(1, len(multipliers))
    return max(0.72, min(1.35, avg))

def compute_character_combat_score(character: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> int:
    attrs = character.get("attributes") or {}
    level = max(1, int(character.get("level", 1) or 1))
    class_current = normalize_class_current(character.get("class_current")) or {}
    class_level = max(1, int(class_current.get("level", 1) or 1))
    class_weight = skill_rank_power_weight(class_current.get("rank", "F"))
    hp_ratio = int(round((int(character.get("hp_current", 0) or 0) / max(1, int(character.get("hp_max", 1) or 1))) * 100))
    sta_ratio = int(round((int(character.get("sta_current", 0) or 0) / max(1, int(character.get("sta_max", 1) or 1))) * 100))
    res_ratio = int(round((int(character.get("res_current", 0) or 0) / max(1, int(character.get("res_max", 1) or 1))) * 100))
    base_stats = (
        int(attrs.get("str", 0) or 0)
        + int(attrs.get("dex", 0) or 0)
        + int(attrs.get("con", 0) or 0)
        + int(attrs.get("int", 0) or 0)
        + int(attrs.get("wis", 0) or 0)
        + int(attrs.get("luck", 0) or 0)
    )
    skill_power = 0
    for raw_skill in (character.get("skills") or {}).values():
        if not isinstance(raw_skill, dict):
            continue
        skill = normalize_dynamic_skill_state(raw_skill, resource_name=resource_name_for_character(character, world_settings))
        skill_power += max(1, int(skill.get("level", 1) or 1)) * skill_rank_power_weight(skill.get("rank", "F"))
    injury_penalty = 0
    for raw_injury in (character.get("injuries") or []):
        injury = normalize_injury_state(raw_injury)
        if not injury:
            continue
        if injury.get("severity") == "schwer":
            injury_penalty += 14
        elif injury.get("severity") == "mittel":
            injury_penalty += 7
        else:
            injury_penalty += 3
    condition_penalty = max(0, len(character.get("conditions") or []) * 2)
    resource_factor = int(round((hp_ratio * 0.45) + (sta_ratio * 0.3) + (res_ratio * 0.25)))
    score = (
        (level * 9)
        + (class_level * (2 + class_weight))
        + base_stats
        + int(skill_power * 0.65)
        + int(resource_factor * 0.35)
        - injury_penalty
        - condition_penalty
    )
    return max(1, score)

def compute_npc_combat_score(npc_entry: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> int:
    level = max(1, int(npc_entry.get("level", 1) or 1))
    class_current = normalize_class_current(npc_entry.get("class_current")) or {}
    class_level = max(1, int(class_current.get("level", level) or level))
    class_weight = skill_rank_power_weight(class_current.get("rank", "F"))
    hp_ratio = int(round((int(npc_entry.get("hp_current", 0) or 0) / max(1, int(npc_entry.get("hp_max", 1) or 1))) * 100))
    sta_ratio = int(round((int(npc_entry.get("sta_current", 0) or 0) / max(1, int(npc_entry.get("sta_max", 1) or 1))) * 100))
    res_ratio = int(round((int(npc_entry.get("res_current", 0) or 0) / max(1, int(npc_entry.get("res_max", 1) or 1))) * 100))
    skill_power = 0
    for raw_skill in (npc_entry.get("skills") or {}).values():
        if not isinstance(raw_skill, dict):
            continue
        skill = normalize_dynamic_skill_state(raw_skill, resource_name=normalize_resource_name((((npc_entry.get("progression") or {}).get("resource_name")) or "Aether"), "Aether"))
        skill_power += max(1, int(skill.get("level", 1) or 1)) * skill_rank_power_weight(skill.get("rank", "F"))
    score = (
        (level * 9)
        + (class_level * (2 + class_weight))
        + int(skill_power * 0.65)
        + int(((hp_ratio * 0.45) + (sta_ratio * 0.3) + (res_ratio * 0.25)) * 0.35)
    )
    return max(1, score)

def build_combat_scaling_context(state: Dict[str, Any], actor: str) -> Dict[str, Any]:
    world_settings = ((state.get("world") or {}).get("settings") or {})
    world_model = state.get("world") if isinstance(state.get("world"), dict) else {}
    actor_character = ((state.get("characters") or {}).get(actor) or {})
    actor_scene = str(actor_character.get("scene_id") or "").strip()
    actor_score = compute_character_combat_score(actor_character, world_settings)
    actor_element_profile = entity_element_profile_for_character(actor_character, world_model)
    threat_scores: List[int] = []
    element_matchups: List[float] = []

    for slot_name, character in (state.get("characters") or {}).items():
        if slot_name == actor:
            continue
        if actor_scene and str(character.get("scene_id") or "").strip() != actor_scene:
            continue
        threat_scores.append(compute_character_combat_score(character, world_settings))
        enemy_profile = entity_element_profile_for_character(character, world_model)
        forward = element_matchup_multiplier(world_model, actor_element_profile, enemy_profile)
        reverse = element_matchup_multiplier(world_model, enemy_profile, actor_element_profile)
        element_matchups.append(max(0.72, min(1.35, (forward / max(0.72, reverse)))))

    for raw_npc in sorted_npc_codex_entries(state):
        npc_scene = str(raw_npc.get("last_seen_scene_id") or "").strip()
        if actor_scene and npc_scene and npc_scene != actor_scene:
            continue
        if str(raw_npc.get("status") or "active").strip().lower() == "gone":
            continue
        threat_scores.append(compute_npc_combat_score(raw_npc, world_settings))
        enemy_profile = entity_element_profile_for_npc(raw_npc, world_model)
        forward = element_matchup_multiplier(world_model, actor_element_profile, enemy_profile)
        reverse = element_matchup_multiplier(world_model, enemy_profile, actor_element_profile)
        element_matchups.append(max(0.72, min(1.35, (forward / max(0.72, reverse)))))

    threat_score = max(1, int(round(sum(threat_scores) / max(1, len(threat_scores))))) if threat_scores else actor_score
    ratio = float(actor_score) / float(max(1, threat_score))
    element_factor = max(0.8, min(1.2, (sum(element_matchups) / max(1, len(element_matchups))))) if element_matchups else 1.0
    weighted_ratio = ratio * element_factor
    pressure = "high" if weighted_ratio <= 0.78 else "medium" if weighted_ratio <= 1.24 else "low"
    return {
        "actor_score": actor_score,
        "threat_score": threat_score,
        "ratio": round(ratio, 3),
        "weighted_ratio": round(weighted_ratio, 3),
        "pressure": pressure,
        "threat_count": len(threat_scores),
        "element_factor": round(element_factor, 3),
        "element_affinities": actor_element_profile.get("affinities") or [],
    }

def apply_combat_scaling_to_patch(
    patch: Dict[str, Any],
    *,
    actor: str,
    combat_context: Dict[str, Any],
    scaling_context: Dict[str, Any],
    action_type: str,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    if action_type == "canon":
        return patch, {"applied": False, "multiplier": 1.0}
    if not bool(combat_context.get("active") or combat_context.get("hinted")):
        return patch, {"applied": False, "multiplier": 1.0}
    pressure = str(scaling_context.get("pressure") or "medium").lower()
    if pressure == "high":
        multiplier = 1.28
    elif pressure == "low":
        multiplier = 0.82
    else:
        multiplier = 1.0
    element_factor = float(scaling_context.get("element_factor", 1.0) or 1.0)
    element_adjusted = max(0.72, min(1.35, (multiplier * (1.0 / element_factor))))
    updated = deep_copy(patch or blank_patch())
    actor_patch = (updated.get("characters") or {}).get(actor)
    if not isinstance(actor_patch, dict):
        return updated, {"applied": False, "multiplier": multiplier, "element_factor": round(element_factor, 3), "effective_multiplier": round(element_adjusted, 3)}
    applied = False
    for key in ("hp_delta", "stamina_delta"):
        if key in actor_patch and int(actor_patch.get(key, 0) or 0) < 0:
            scaled = int(round(int(actor_patch.get(key, 0) or 0) * element_adjusted))
            if scaled == 0:
                scaled = -1
            actor_patch[key] = scaled
            applied = True
    resources_delta = actor_patch.get("resources_delta") if isinstance(actor_patch.get("resources_delta"), dict) else {}
    if resources_delta:
        for key in ("hp", "stamina", "sta", "res", "aether"):
            raw = int(resources_delta.get(key, 0) or 0)
            if raw < 0:
                scaled = int(round(raw * element_adjusted))
                if scaled == 0:
                    scaled = -1
                resources_delta[key] = scaled
                applied = True
        actor_patch["resources_delta"] = resources_delta
    updated.setdefault("characters", {})[actor] = actor_patch
    return updated, {"applied": applied, "multiplier": multiplier, "element_factor": round(element_factor, 3), "effective_multiplier": round(element_adjusted, 3)}

def infer_combat_context(
    state: Dict[str, Any],
    actor: str,
    action_type: str,
    text: str,
) -> Dict[str, Any]:
    normalized_text = normalized_eval_text(text)
    meta_combat = normalize_combat_meta(state.setdefault("meta", {}))
    actor_char = ((state.get("characters") or {}).get(actor) or {})
    actor_in_combat = bool((((actor_char.get("derived") or {}).get("combat_flags") or {}).get("in_combat", False)))
    hinted = any(keyword in normalized_text for keyword in COMBAT_NARRATIVE_HINTS)
    return {
        "active": bool(meta_combat.get("active") or actor_in_combat),
        "hinted": hinted,
        "actor_in_combat": actor_in_combat,
        "phase": meta_combat.get("phase", "idle"),
        "action_type": action_type,
    }

def patch_has_combat_signal(patch: Dict[str, Any]) -> bool:
    for upd in (patch.get("characters") or {}).values():
        if not isinstance(upd, dict):
            continue
        if int(upd.get("hp_delta", 0) or 0) < 0:
            return True
        if int(upd.get("stamina_delta", 0) or 0) < 0:
            return True
        resources_delta = upd.get("resources_delta") if isinstance(upd.get("resources_delta"), dict) else {}
        if any(int(resources_delta.get(key, 0) or 0) < 0 for key in ("hp", "stamina", "sta", "res", "aether")):
            return True
        for effect in (upd.get("effects_add") or []):
            if isinstance(effect, dict) and str(effect.get("category") or "").strip().lower() == "combat":
                return True
    return False

def update_combat_meta_after_turn(
    state: Dict[str, Any],
    *,
    actor: str,
    action_type: str,
    input_text: str,
    story_text: str,
    patch: Dict[str, Any],
    combat_context: Dict[str, Any],
    resolution_summary: Dict[str, Any],
) -> Dict[str, Any]:
    meta = state.setdefault("meta", {})
    combat = normalize_combat_meta(meta)
    turn_number = int(meta.get("turn", 0) or 0)
    now = utc_now()

    story_norm = normalized_eval_text(story_text)
    hinted = bool(combat_context.get("hinted")) or patch_has_combat_signal(patch) or any(
        keyword in story_norm for keyword in COMBAT_NARRATIVE_HINTS
    )
    ended = any(keyword in story_norm for keyword in COMBAT_END_HINTS)
    participants = [
        slot_name
        for slot_name, character in (state.get("characters") or {}).items()
        if bool((((character.get("derived") or {}).get("combat_flags") or {}).get("in_combat", False)))
    ]

    if not combat.get("active") and hinted:
        combat["active"] = True
        combat["combat_id"] = combat.get("combat_id") or make_id("cmb")
        combat["round"] = max(1, int(combat.get("round", 0) or 0) + 1)
        combat["phase"] = "resolving"
    elif combat.get("active"):
        combat["phase"] = "resolving"
        combat["round"] = max(1, int(combat.get("round", 0) or 0) + 1)

    if combat.get("active"):
        summary = str(first_sentences(story_text, 1) or "").strip()
        combat.setdefault("action_queue", []).append(
            {
                "turn": turn_number,
                "actor": actor,
                "action_type": action_type,
                "summary": summary[:220],
                "created_at": now,
            }
        )
        combat["action_queue"] = (combat.get("action_queue") or [])[-20:]
        combat["participants"] = participants or [actor]
        combat["last_resolution"] = deep_copy(resolution_summary or {})
        if ended and not patch_has_combat_signal(patch):
            combat["active"] = False
            combat["phase"] = "ended"
            combat["participants"] = []
        else:
            combat["phase"] = "collecting"
    else:
        combat["phase"] = "idle"
        combat["participants"] = []

    combat["updated_at"] = now
    meta["combat"] = combat
    return combat

def normalize_ruleset_choice(raw_value: Any) -> str:
    text = str(extract_text_answer(raw_value) or raw_value or "").strip()
    mapping = {
        "1W20": "Konsequent",
        "2W6": "Dramatisch",
        "Ohne Würfel (nur Entscheidungen)": "Konsequent",
    }
    return mapping.get(text, text)

def normalize_campaign_length_choice(raw_value: Any) -> str:
    text = str(extract_text_answer(raw_value) or raw_value or "").strip().lower()
    if not text:
        return "medium"
    mapping = {
        "short": "short",
        "kurz": "short",
        "mittel": "medium",
        "medium": "medium",
        "open": "open",
        "unbestimmt": "open",
        "offen": "open",
    }
    normalized = mapping.get(text, text)
    if normalized not in CAMPAIGN_LENGTHS:
        return "medium"
    return normalized

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

def generate_character_attribute_weights(campaign: Dict[str, Any], slot_name: str, summary: Dict[str, Any]) -> Dict[str, Any]:
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

def default_character_setup_node() -> Dict[str, Any]:
    return {
        "completed": False,
        "question_queue": build_character_question_queue(),
        "answers": {},
        "summary": {},
        "raw_transcript": [],
        "question_runtime": {},
    }

def save_json(path: str, payload: Dict[str, Any]) -> None:
    ensure_data_dirs()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def campaign_path(campaign_id: str) -> str:
    return os.path.join(CAMPAIGNS_DIR, f"{campaign_id}.json")

def list_campaign_ids() -> List[str]:
    ensure_data_dirs()
    ids = []
    for name in os.listdir(CAMPAIGNS_DIR):
        if name.endswith(".json"):
            ids.append(name[:-5])
    return sorted(ids)

def extract_text_answer(answer: Any) -> str:
    if answer is None:
        return ""
    if isinstance(answer, bool):
        return "Ja" if answer else "Nein"
    if isinstance(answer, str):
        return answer.strip()
    if isinstance(answer, list):
        return ", ".join(str(entry).strip() for entry in answer if str(entry).strip())
    if isinstance(answer, dict):
        if "selected" in answer:
            selected = answer.get("selected")
            if isinstance(selected, list):
                values = [str(entry).strip() for entry in selected if str(entry).strip()]
                values.extend(str(entry).strip() for entry in answer.get("other_values", []) if str(entry).strip())
                return ", ".join(values)
            text = str(selected or "").strip()
            if answer.get("other_text"):
                extra = str(answer["other_text"]).strip()
                return ", ".join(part for part in [text, extra] if part)
            return text
        if "value" in answer:
            return extract_text_answer(answer["value"])
    return str(answer).strip()

def parse_lines(value: str) -> List[str]:
    if not value:
        return []
    chunks = []
    for raw in value.replace("\r", "\n").split("\n"):
        for part in raw.split(";"):
            text = part.strip(" ,-")
            if text:
                chunks.append(text)
    return chunks

def split_creator_item_blocks(value: str) -> List[str]:
    text = str(value or "").replace("\r", "\n").strip()
    if not text:
        return []
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    blocks: List[str] = []
    current = ""
    bullet_pattern = re.compile(r"^\s*(?:\d+[\.\)]|[-*•])\s+")
    for line in lines:
        if bullet_pattern.match(line):
            if current:
                blocks.append(current.strip())
            current = bullet_pattern.sub("", line).strip()
            continue
        if current:
            current = f"{current} {line}".strip()
        else:
            current = line
    if current:
        blocks.append(current.strip())
    if len(blocks) > 1:
        return blocks

    parts: List[str] = []
    buffer = ""
    depth = 0
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")" and depth > 0:
            depth -= 1
        if char == ";" and depth == 0:
            if buffer.strip():
                parts.append(buffer.strip())
            buffer = ""
            continue
        if char == "," and depth == 0:
            lookback = buffer.rstrip()
            if re.search(r"\b(?:und|oder)$", lookback, flags=re.IGNORECASE):
                buffer += char
                continue
            if buffer.strip():
                parts.append(buffer.strip())
            buffer = ""
            continue
        buffer += char
    if buffer.strip():
        parts.append(buffer.strip())
    return parts if len(parts) > 1 else [text]

def summarize_creator_item_name(raw_name: str) -> str:
    text = str(raw_name or "").replace("\n", " ").strip()
    text = re.sub(r"^\s*(?:\d+[\.\)]|[-*•])\s+", "", text)
    text = re.sub(r"\s+", " ", text).strip(" ,-")
    text = re.sub(r"\((.*?)\)", "", text).strip(" ,-")
    text = re.sub(r"\s+(?:der|die|das)\s+in\s+dieser\s+welt\b.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+(?:welche|welcher|welches)\b.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+(?:für|fuer)\s+.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" ,-.")
    text = re.sub(r"^(?:ein|eine|einen|einem|einer)\s+", "", text, flags=re.IGNORECASE)
    text = text[:72].strip(" ,-.'\"")
    return text

def parse_earth_items(value: str) -> List[str]:
    items = []
    for chunk in split_creator_item_blocks(value):
        text = summarize_creator_item_name(chunk)
        if text:
            items.append(text)
    return items[:6]

def parse_factions(value: str) -> List[Dict[str, str]]:
    factions = []
    for chunk in parse_lines(value):
        cleaned = re.sub(r"^\d+\.\s*", "", chunk).strip()
        if not cleaned:
            continue
        markdown_match = re.match(r"^\*{0,2}([^:*]+?)\*{0,2}\s*:\s*(.+)$", cleaned)
        if markdown_match:
            name = markdown_match.group(1).strip()
            detail = markdown_match.group(2).strip()
            goal_match = re.search(r"Ziel:\s*(.+?)(?:\s+Methoden:\s*(.+))?$", detail, flags=re.IGNORECASE)
            if goal_match:
                factions.append(
                    {
                        "name": name,
                        "goal": goal_match.group(1).strip(),
                        "methods": (goal_match.group(2) or "").strip(),
                    }
                )
                continue
            factions.append({"name": name, "goal": detail, "methods": ""})
            continue
        parts = [part.strip() for part in re.split(r"\s+\|\s+|\s+-\s+", cleaned, maxsplit=2) if part.strip()]
        if not parts:
            parts = [part.strip() for part in cleaned.split(":", 1) if part.strip()]
        if not parts:
            continue
        factions.append(
            {
                "name": parts[0],
                "goal": parts[1] if len(parts) > 1 else cleaned,
                "methods": parts[2] if len(parts) > 2 else "",
            }
        )
    return factions[:6]

def legacy_select_answer_payload(question: Dict[str, Any], raw_value: Any) -> Dict[str, Any]:
    raw_text = extract_text_answer(raw_value)
    allow_other = bool(question.get("allow_other"))
    if not raw_text:
        return {"selected": "", "other_text": ""}

    options = [str(option).strip() for option in question.get("options", [])]
    normalized_options = {normalized_eval_text(option): option for option in options if option}
    normalized_raw = normalized_eval_text(raw_text)
    aliases = LEGACY_SELECT_ALIASES.get(question["id"], {})

    if raw_text in options:
        return {"selected": raw_text, "other_text": ""}
    if normalized_raw in normalized_options:
        return {"selected": normalized_options[normalized_raw], "other_text": ""}
    if normalized_raw in aliases:
        return {"selected": aliases[normalized_raw], "other_text": ""}

    if question["id"] == "char_age":
        inferred_age = infer_age_years(raw_text)
        if 16 <= inferred_age <= 19:
            return {"selected": "Teen (16-19)", "other_text": ""}
        if 20 <= inferred_age <= 25:
            return {"selected": "Jung (20-25)", "other_text": ""}
        if 26 <= inferred_age <= 35:
            return {"selected": "Erwachsen (26-35)", "other_text": ""}
        if inferred_age >= 36:
            return {"selected": "Älter (36+)", "other_text": ""}

    if normalized_options:
        closest_key, closest_value = max(
            normalized_options.items(),
            key=lambda item: SequenceMatcher(None, normalized_raw, item[0]).ratio(),
        )
        if closest_key and SequenceMatcher(None, normalized_raw, closest_key).ratio() >= 0.72:
            return {"selected": closest_value, "other_text": ""}

    if allow_other:
        return {"selected": "Sonstiges", "other_text": raw_text}
    return {"selected": "", "other_text": ""}

def load_setup_catalog() -> Dict[str, Any]:
    return SETUP_CATALOG

def build_rules_profile(campaign: Dict[str, Any]) -> Dict[str, Any]:
    summary = campaign.get("setup", {}).get("world", {}).get("summary", {})
    world_settings = (((campaign.get("state") or {}).get("world") or {}).get("settings") or {})
    attribute_scale = world_attribute_scale(campaign)
    return {
        "theme": summary.get("theme", ""),
        "tone": summary.get("tone", ""),
        "difficulty": summary.get("difficulty", ""),
        "death_possible": bool(summary.get("death_possible", True)),
        "death_policy": summary.get("death_policy", ""),
        "ruleset": summary.get("ruleset", ""),
        "outcome_model": summary.get("outcome_model", ""),
        "resource_scarcity": summary.get("resource_scarcity", ""),
        "healing_frequency": summary.get("healing_frequency", ""),
        "monsters_density": summary.get("monsters_density", ""),
        "world_laws": summary.get("world_laws", []),
        "attribute_range_label": attribute_scale["label"],
        "attribute_range_min": attribute_scale["min"],
        "attribute_range_max": attribute_scale["max"],
        "resource_name": world_settings.get("resource_name", summary.get("resource_name", "Aether")),
        "consequence_severity": world_settings.get("consequence_severity", summary.get("consequence_severity", "mittel")),
        "progression_speed": world_settings.get("progression_speed", summary.get("progression_speed", "normal")),
        "evolution_cost_policy": world_settings.get("evolution_cost_policy", summary.get("evolution_cost_policy", "leicht")),
        "element_count": len((((campaign.get("state") or {}).get("world") or {}).get("elements") or {})),
        "core_elements": list(ELEMENT_CORE_NAMES),
    }

def attribute_cap_for_campaign(campaign: Dict[str, Any]) -> int:
    return max(1, int(world_attribute_scale(campaign)["max"] or 10))

def campaign_slots(campaign: Dict[str, Any]) -> List[str]:
    keys = list((campaign.get("state", {}).get("characters") or {}).keys())
    if not keys:
        keys = list((campaign.get("claims") or {}).keys())
    if not keys:
        keys = list((campaign.get("setup", {}).get("characters") or {}).keys())
    return ordered_slots([key for key in keys if is_slot_id(key)])

def player_claim(campaign: Dict[str, Any], player_id: Optional[str]) -> Optional[str]:
    if not player_id:
        return None
    for slot_name, claimed_player_id in (campaign.get("claims") or {}).items():
        if claimed_player_id == player_id:
            return slot_name
    return None

def display_name_for_slot(campaign: Dict[str, Any], slot_name: str) -> str:
    bio = (campaign.get("state", {}).get("characters", {}).get(slot_name) or {}).get("bio", {})
    return bio.get("name") or f"Slot {slot_index(slot_name)}"

def active_party(campaign: Dict[str, Any]) -> List[str]:
    slots = []
    setup_chars = campaign.get("setup", {}).get("characters", {})
    for slot_name in campaign_slots(campaign):
        if campaign.get("claims", {}).get(slot_name) and setup_chars.get(slot_name, {}).get("completed"):
            slots.append(slot_name)
    return slots

def expected_setup_slots(campaign: Dict[str, Any]) -> List[str]:
    summary = ((campaign.get("setup") or {}).get("world") or {}).get("summary") or {}
    count = int(summary.get("player_count") or 1)
    count = max(1, min(MAX_PLAYERS, count))
    slots = campaign_slots(campaign)
    if len(slots) >= count:
        return slots[:count]
    return [slot_id(index) for index in range(1, count + 1)]

def setup_slot_statuses(campaign: Dict[str, Any]) -> List[Dict[str, Any]]:
    setup_chars = ((campaign.get("setup") or {}).get("characters") or {})
    statuses: List[Dict[str, Any]] = []
    for slot_name in expected_setup_slots(campaign):
        owner = (campaign.get("claims") or {}).get(slot_name)
        node = setup_chars.get(slot_name) or {}
        if not owner:
            status = "unclaimed"
        elif node.get("completed"):
            status = "ready"
        else:
            status = "in_progress"
        statuses.append(
            {
                "slot_id": slot_name,
                "display_name": display_name_for_slot(campaign, slot_name),
                "claimed_by": owner,
                "status": status,
                "completed": bool(node.get("completed")),
            }
        )
    return statuses

def public_player(player_id: str, player: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "player_id": player_id,
        "display_name": player.get("display_name", ""),
        "joined_at": player.get("joined_at"),
        "last_seen_at": player.get("last_seen_at"),
    }

def default_player_diary_entry(player_id: str, display_name: str) -> Dict[str, Any]:
    now = utc_now()
    return {
        "player_id": player_id,
        "display_name": display_name,
        "content": "",
        "updated_at": now,
        "updated_by": player_id,
    }

def available_slots(campaign: Dict[str, Any]) -> List[Dict[str, Any]]:
    players = campaign.get("players", {})
    out = []
    for slot_name in campaign_slots(campaign):
        owner = campaign.get("claims", {}).get(slot_name)
        owner_name = players.get(owner, {}).get("display_name") if owner else None
        setup_node = campaign.get("setup", {}).get("characters", {}).get(slot_name, {})
        character = (campaign.get("state", {}).get("characters", {}) or {}).get(slot_name) or blank_character_state(slot_name)
        character = normalize_character_state(character, slot_name, campaign.get("state", {}).get("items", {}) or {})
        current_class = normalize_class_current(character.get("class_current"))
        out.append(
            {
                "slot_id": slot_name,
                "claimed_by": owner,
                "claimed_by_name": owner_name,
                "completed": bool(setup_node.get("completed")),
                "display_name": display_name_for_slot(campaign, slot_name),
                "summary": setup_node.get("summary", {}),
                "class_name": (current_class or {}).get("name", ""),
                "class_rank": (current_class or {}).get("rank", ""),
                "class_level": (current_class or {}).get("level", 0),
                "class_level_max": (current_class or {}).get("level_max", 10),
            }
        )
    return out

def compact_conditions(character: Dict[str, Any]) -> List[str]:
    names = []
    for effect in character.get("effects", []) or []:
        if effect.get("visible", True) and effect.get("name"):
            names.append(effect["name"])
    if not names:
        names = [entry for entry in character.get("conditions", []) or [] if entry]
    return names[:3]

def build_party_overview(campaign: Dict[str, Any]) -> List[Dict[str, Any]]:
    overview = []
    world_settings = (((campaign.get("state") or {}).get("world") or {}).get("settings") or {})
    for slot_name in campaign_slots(campaign):
        character = (campaign.get("state", {}).get("characters", {}) or {}).get(slot_name) or blank_character_state(slot_name)
        character = normalize_character_state(character, slot_name, campaign.get("state", {}).get("items", {}) or {})
        current_class = normalize_class_current(character.get("class_current"))
        overview.append(
            {
                "slot_id": slot_name,
                "display_name": display_name_for_slot(campaign, slot_name),
                "claimed_by": campaign.get("claims", {}).get(slot_name),
                "claimed_by_name": campaign.get("players", {}).get(campaign.get("claims", {}).get(slot_name), {}).get("display_name"),
                "scene_id": character.get("scene_id", ""),
                "scene_name": derive_scene_name(campaign, slot_name),
                "class_name": (current_class or {}).get("name", ""),
                "class_rank": (current_class or {}).get("rank", ""),
                "class_level": (current_class or {}).get("level"),
                "class_level_max": (current_class or {}).get("level_max"),
                "level": int(character.get("level", 1) or 1),
                "xp_current": int(character.get("xp_current", 0) or 0),
                "xp_to_next": int(character.get("xp_to_next", next_character_xp_for_level(int(character.get("level", 1) or 1))) or next_character_xp_for_level(int(character.get("level", 1) or 1))),
                "hp_current": int(character.get("hp_current", 0) or 0),
                "hp_max": int(character.get("hp_max", 0) or 0),
                "sta_current": int(character.get("sta_current", 0) or 0),
                "sta_max": int(character.get("sta_max", 0) or 0),
                "res_current": int(character.get("res_current", 0) or 0),
                "res_max": int(character.get("res_max", 0) or 0),
                "resource_name": resource_name_for_character(character, world_settings),
                "carry_current": int(character.get("carry_current", 0) or 0),
                "carry_max": int(character.get("carry_max", 0) or 0),
                "hp_pct": clamp(
                    int(
                        round(
                            (int(character.get("hp_current", 0) or 0) / max(1, int(character.get("hp_max", 1) or 1))) * 100
                        )
                    ),
                    0,
                    100,
                ),
                "sta_pct": clamp(
                    int(
                        round(
                            (int(character.get("sta_current", 0) or 0) / max(1, int(character.get("sta_max", 1) or 1))) * 100
                        )
                    ),
                    0,
                    100,
                ),
                "res_pct": clamp(
                    int(
                        round(
                            (int(character.get("res_current", 0) or 0) / max(1, int(character.get("res_max", 1) or 1))) * 100
                        )
                    ),
                    0,
                    100,
                ),
                "injury_count": len(character.get("injuries", []) or []),
                "scar_count": len(character.get("scars", []) or []),
                "conditions": compact_conditions(character),
                "in_combat": bool(((character.get("derived") or {}).get("combat_flags") or {}).get("in_combat", False)),
                "appearance_short": ((character.get("appearance") or {}).get("summary_short") or ""),
                "age": int(((character.get("bio") or {}).get("age_years", 0) or 0)),
                "age_stage": str(((character.get("bio") or {}).get("age_stage", "")) or ""),
            }
        )
    return overview

def build_character_sheet_view(campaign: Dict[str, Any], slot_name: str) -> Dict[str, Any]:
    character = (campaign.get("state", {}).get("characters", {}) or {}).get(slot_name)
    if not character:
        raise HTTPException(status_code=404, detail="Charakter nicht gefunden.")
    character = normalize_character_state(character, slot_name, campaign.get("state", {}).get("items", {}) or {})
    world_settings = (((campaign.get("state") or {}).get("world") or {}).get("settings") or {})
    reconcile_canonical_resources(character, world_settings)
    bio = character.get("bio", {})
    resources = build_compat_resources_view(character, world_settings)
    derived = character.get("derived", {})
    skills = character.get("skills", {})
    equipment = character.get("equipment", {})
    inventory_items = list_inventory_items(character)
    items_db = campaign.get("state", {}).get("items", {}) or {}
    item_views = []
    for entry in inventory_items:
        item = ensure_item_shape(entry["item_id"], items_db.get(entry["item_id"], {}))
        item_views.append(
            {
                "item_id": entry["item_id"],
                "name": item.get("name", entry["item_id"]),
                "stack": entry["stack"],
                "rarity": item.get("rarity", "common"),
                "weight": item.get("weight", 0),
                "slot": item.get("slot", ""),
                "cursed": item.get("cursed", False),
            }
        )
    equipment_view = {}
    for equip_slot, item_id in equipment.items():
        item = ensure_item_shape(item_id, items_db.get(item_id, {})) if item_id else {}
        equipment_view[equip_slot] = {
            "item_id": item_id,
            "name": item.get("name", "Leer") if item_id else "Leer",
            "rarity": item.get("rarity", "") if item_id else "",
            "weight": item.get("weight", 0) if item_id else 0,
        }
    resource_name = resource_name_for_character(character, world_settings)
    current_class = normalize_class_current(character.get("class_current"))
    ascension_plotpoint = None
    current_quest_id = (((current_class or {}).get("ascension") or {}).get("quest_id"))
    if current_quest_id:
        ascension_plotpoint = next((entry for entry in (campaign.get("state", {}).get("plotpoints") or []) if entry.get("id") == current_quest_id), None)
    skill_views = []
    for skill_id, skill_value in (skills or {}).items():
        skill_state = normalize_dynamic_skill_state(
            skill_value,
            skill_id=skill_id,
            skill_name=(skill_value or {}).get("name", skill_id) if isinstance(skill_value, dict) else skill_id,
            resource_name=resource_name,
            unlocked_from=(skill_value or {}).get("unlocked_from", "Story") if isinstance(skill_value, dict) else "Story",
        )
        skill_views.append(
            {
                "id": skill_state.get("id"),
                "name": skill_state.get("name"),
                "level": skill_state.get("level", 1),
                "level_max": skill_state.get("level_max", 10),
                "xp": skill_state.get("xp", 0),
                "next_xp": skill_state.get("next_xp", 100),
                "rank": skill_state.get("rank", "F"),
                "mastery": skill_state.get("mastery", 0),
                "tags": skill_state.get("tags", []),
                "description": skill_state.get("description", ""),
                "cost": skill_state.get("cost"),
                "price": skill_state.get("price"),
                "cooldown_turns": skill_state.get("cooldown_turns"),
                "unlocked_from": skill_state.get("unlocked_from"),
                "synergy_notes": skill_state.get("synergy_notes"),
                "class_match": class_affinity_match(skill_state.get("tags") or [], (current_class or {}).get("affinity_tags") or []),
                "effective_progress_multiplier": effective_skill_progress_multiplier(character, skill_state, world_settings),
            }
        )
    skill_views.sort(key=lambda entry: (skill_rank_sort_value(entry.get("rank")), entry.get("level", 1), entry.get("name", "")), reverse=True)
    fusion_hints = build_skill_fusion_hints(skills, resource_name=resource_name)
    modifier_summary = {
        "defense": calculate_derived_bonus(character, items_db, "defense"),
        "initiative": calculate_derived_bonus(character, items_db, "initiative"),
        "attack_rating_mainhand": calculate_derived_bonus(character, items_db, "attack_rating_mainhand"),
        "attack_rating_offhand": calculate_derived_bonus(character, items_db, "attack_rating_offhand"),
    }
    attribute_scale = world_attribute_scale(campaign)
    return {
        "slot_id": slot_name,
        "display_name": display_name_for_slot(campaign, slot_name),
        "scene_id": character.get("scene_id", ""),
        "scene_name": derive_scene_name(campaign, slot_name),
        "claimed_by_name": campaign.get("players", {}).get(campaign.get("claims", {}).get(slot_name), {}).get("display_name"),
        "sheet": {
            "overview": {
                "bio": bio,
                "resources": resources,
                "resource_label": resource_name,
                "class_current": current_class,
                "character_progression": {
                    "level": int(character.get("level", 1) or 1),
                    "xp_current": int(character.get("xp_current", 0) or 0),
                    "xp_to_next": int(character.get("xp_to_next", next_character_xp_for_level(int(character.get("level", 1) or 1))) or next_character_xp_for_level(int(character.get("level", 1) or 1))),
                    "xp_total": int(character.get("xp_total", 0) or 0),
                },
                "injury_count": len(character.get("injuries", []) or []),
                "scar_count": len(character.get("scars", []) or []),
                "location": {"scene_id": character.get("scene_id", ""), "scene_name": derive_scene_name(campaign, slot_name)},
                "claim_status": "geclaimt" if campaign.get("claims", {}).get(slot_name) else "frei",
                "appearance": character.get("appearance", {}),
                "ageing": character.get("aging", {}),
            },
            "stats": {
                "attributes": character.get("attributes", {}),
                "attribute_scale": {
                    "label": attribute_scale["label"],
                    "min": attribute_scale["min"],
                    "max": attribute_scale["max"],
                },
                "derived": derived,
                "resistances": derived.get("resistances", {}),
                "age_modifiers": derived.get("age_modifiers", {}),
                "modifier_summary": modifier_summary,
            },
            "skills": skill_views,
            "class": {
                "current": current_class,
                "ascension_plotpoint": ascension_plotpoint,
            },
            "injuries_scars": {
                "injuries": character.get("injuries", []),
                "scars": character.get("scars", []),
            },
            "gear_inventory": {
                "equipment": equipment_view,
                "quick_slots": character.get("inventory", {}).get("quick_slots", {}),
                "inventory_items": item_views,
                "carry_weight": character.get("carry_current", derived.get("carry_weight", 0)),
                "carry_limit": character.get("carry_max", derived.get("carry_limit", 0)),
                "encumbrance_state": derived.get("encumbrance_state", "normal"),
            },
            "effects": character.get("effects", []),
            "journal": {
                **(character.get("journal", {}) or {}),
                "appearance_history": character.get("appearance_history", []),
            },
            "progression": character.get("progression", {}),
            "skill_meta": {
                "fusion_possible": bool(fusion_hints),
                "fusion_hints": fusion_hints,
                "resource_name": resource_name,
            },
            "meta": {
                "faction_memberships": character.get("faction_memberships", []),
            },
        },
        "derived_explainer": {
            "defense": "10 + DEX + Armor + Effekte",
            "carry_limit": "10 + STR * 2",
            "initiative": "DEX + passive Boni + Effekte",
        },
        "timeline_refs": [],
    }

def build_npc_sheet_view(campaign: Dict[str, Any], npc_id: str) -> Dict[str, Any]:
    state = campaign.get("state") or {}
    npc_entry = normalize_npc_entry((state.get("npc_codex") or {}).get(npc_id), fallback_npc_id=npc_id)
    if not npc_entry:
        raise HTTPException(status_code=404, detail="NPC nicht gefunden.")
    scene_id = str(npc_entry.get("last_seen_scene_id") or "").strip()
    scene_name = scene_name_from_state(state, scene_id) if scene_id else ""
    history_notes = [str(note).strip() for note in (npc_entry.get("history_notes") or []) if str(note).strip()]
    npc_class = normalize_class_current(npc_entry.get("class_current"))
    npc_resource_name = normalize_resource_name((((npc_entry.get("progression") or {}).get("resource_name")) or (((state.get("world") or {}).get("settings") or {}).get("resource_name")) or "Aether"), "Aether")
    npc_skills = [
        normalize_dynamic_skill_state(
            skill_value,
            skill_id=skill_id,
            skill_name=(skill_value or {}).get("name", skill_id) if isinstance(skill_value, dict) else skill_id,
            resource_name=npc_resource_name,
        )
        for skill_id, skill_value in ((npc_entry.get("skills") or {}).items())
    ]
    npc_skills.sort(key=lambda entry: (skill_rank_sort_value(entry.get("rank")), entry.get("level", 1), entry.get("name", "")), reverse=True)
    return {
        "npc_id": npc_entry.get("npc_id"),
        "name": npc_entry.get("name"),
        "race": npc_entry.get("race"),
        "age": npc_entry.get("age"),
        "goal": npc_entry.get("goal"),
        "level": npc_entry.get("level"),
        "xp_total": int(npc_entry.get("xp_total", 0) or 0),
        "xp_current": int(npc_entry.get("xp_current", 0) or 0),
        "xp_to_next": int(npc_entry.get("xp_to_next", next_character_xp_for_level(int(npc_entry.get("level", 1) or 1))) or next_character_xp_for_level(int(npc_entry.get("level", 1) or 1))),
        "backstory_short": npc_entry.get("backstory_short"),
        "role_hint": npc_entry.get("role_hint"),
        "faction": npc_entry.get("faction"),
        "status": npc_entry.get("status"),
        "last_seen_scene_id": scene_id,
        "last_seen_scene_name": scene_name or "Unbekannt",
        "first_seen_turn": npc_entry.get("first_seen_turn"),
        "last_seen_turn": npc_entry.get("last_seen_turn"),
        "mention_count": npc_entry.get("mention_count"),
        "relevance_score": npc_entry.get("relevance_score"),
        "history_notes": history_notes,
        "tags": npc_entry.get("tags", []),
        "class_current": npc_class,
        "skills": npc_skills,
        "resources": {
            "hp_current": int(npc_entry.get("hp_current", 0) or 0),
            "hp_max": int(npc_entry.get("hp_max", 0) or 0),
            "sta_current": int(npc_entry.get("sta_current", 0) or 0),
            "sta_max": int(npc_entry.get("sta_max", 0) or 0),
            "res_current": int(npc_entry.get("res_current", 0) or 0),
            "res_max": int(npc_entry.get("res_max", 0) or 0),
            "resource_name": npc_resource_name,
        },
        "conditions": npc_entry.get("conditions", []),
        "injuries": npc_entry.get("injuries", []),
        "scars": npc_entry.get("scars", []),
    }

def current_question_id(setup_node: Dict[str, Any]) -> Optional[str]:
    answers = setup_node.get("answers", {})
    for qid in setup_node.get("question_queue", []):
        if not setup_question_is_applicable(setup_node, qid):
            continue
        if qid not in answers:
            return qid
    return None

def answered_count(setup_node: Dict[str, Any]) -> int:
    answers = setup_node.get("answers", {})
    return sum(
        1
        for qid in setup_node.get("question_queue", [])
        if setup_question_is_applicable(setup_node, qid) and qid in answers
    )

def progress_payload(setup_node: Dict[str, Any]) -> Dict[str, int]:
    total = sum(1 for qid in setup_node.get("question_queue", []) if setup_question_is_applicable(setup_node, qid))
    return {
        "answered": answered_count(setup_node),
        "total": total,
        "step": min(answered_count(setup_node) + 1, total) if total else 0,
    }

def setup_chapter_config(setup_type: str) -> Dict[str, Dict[str, Any]]:
    return WORLD_SETUP_CHAPTERS if setup_type == "world" else CHAR_SETUP_CHAPTERS

def setup_question_chapter_key(setup_type: str, question_id: str) -> str:
    for chapter_key, config in setup_chapter_config(setup_type).items():
        if question_id in (config.get("questions") or set()):
            return chapter_key
    return "general"

def setup_chapter_progress(setup_node: Dict[str, Any], setup_type: str, chapter_key: str) -> Dict[str, int]:
    config = setup_chapter_config(setup_type).get(chapter_key) or {}
    questions = [qid for qid in setup_node.get("question_queue", []) if qid in (config.get("questions") or set())]
    total = 0
    answered = 0
    for qid in questions:
        if not setup_question_is_applicable(setup_node, qid):
            continue
        total += 1
        if qid in (setup_node.get("answers") or {}):
            answered += 1
    return {"answered": answered, "total": total}

def setup_global_progress(setup_node: Dict[str, Any]) -> Dict[str, int]:
    payload = progress_payload(setup_node)
    return {"answered": int(payload.get("answered", 0) or 0), "total": int(payload.get("total", 0) or 0)}

def setup_phase_display(phase: str) -> str:
    phase = str(phase or "").strip().lower()
    if phase == "world_setup":
        return "Weltaufbau"
    if phase == "character_setup_open":
        return "Charakterwerdung"
    if phase == "ready_to_start":
        return "Bereit zum Start"
    if phase == "active":
        return "Aktive Spielphase"
    return "Kampagne"

def setup_summary_preview(campaign: Dict[str, Any], setup_type: str, slot_name: Optional[str] = None) -> Dict[str, Any]:
    if setup_type == "world":
        summary = ((campaign.get("setup") or {}).get("world") or {}).get("summary") or {}
        if not summary:
            answers = (((campaign.get("setup") or {}).get("world") or {}).get("answers") or {})
            summary = {
                "theme": extract_text_answer(answers.get("theme")),
                "tone": extract_text_answer(answers.get("tone")),
                "resource_name": extract_text_answer(answers.get("resource_name")),
                "central_conflict": extract_text_answer(answers.get("central_conflict")),
            }
        return {
            "theme": summary.get("theme", ""),
            "tone": summary.get("tone", ""),
            "resource_name": summary.get("resource_name", ""),
            "campaign_length": summary.get("campaign_length", ""),
            "central_conflict": summary.get("central_conflict", ""),
            "world_structure": summary.get("world_structure", ""),
        }
    setup_node = (((campaign.get("setup") or {}).get("characters") or {}).get(slot_name or "")) or {}
    summary = setup_node.get("summary") or {}
    answers = setup_node.get("answers") or {}
    return {
        "display_name": summary.get("display_name") or extract_text_answer(answers.get("char_name")),
        "focus": summary.get("current_focus") or extract_text_answer(answers.get("current_focus")),
        "class_start_mode": summary.get("class_start_mode") or extract_text_answer(answers.get("class_start_mode")),
        "first_goal": summary.get("first_goal") or extract_text_answer(answers.get("first_goal")),
        "strength": summary.get("strength") or extract_text_answer(answers.get("strength")),
        "weakness": summary.get("weakness") or extract_text_answer(answers.get("weakness")),
    }

def ollama_request_seed() -> Optional[int]:
    if OLLAMA_SEED is not None:
        return int(OLLAMA_SEED)
    return int.from_bytes(secrets.token_bytes(4), "big")

def call_ollama_text(system: str, user: str) -> str:
    options = {
        "temperature": 0.35,
        "num_ctx": 4096,
    }
    seed = ollama_request_seed()
    if seed is not None:
        options["seed"] = seed
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": options,
    }
    response = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=max(30, OLLAMA_TIMEOUT_SEC))
    if response.status_code != 200:
        raise RuntimeError(f"Ollama error {response.status_code}: {response.text[:500]}")
    return (response.json().get("message", {}) or {}).get("content", "").strip()

def ollama_format_fallback_needed(message: str) -> bool:
    lowered = str(message or "").lower()
    return (
        "failed to load model vocabulary required for format" in lowered
        or ("does not support" in lowered and "format" in lowered)
        or "failed to parse grammar" in lowered
        or "grammar_init" in lowered
        or "failed to initialize grammar" in lowered
        or "unexpected end of input" in lowered
        or "expecting ')'" in lowered
    )

def is_turn_response_schema(schema: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(schema, dict):
        return False
    required = schema.get("required") or []
    return all(key in required for key in ("story", "patch", "requests"))

def schema_fallback_instruction(schema: Optional[Dict[str, Any]]) -> str:
    if is_turn_response_schema(schema):
        return TURN_RESPONSE_JSON_CONTRACT
    if not isinstance(schema, dict):
        return "Antworte ausschließlich mit gültigem JSON ohne Markdown."
    return (
        "Antworte ausschließlich mit gültigem JSON ohne Markdown. "
        "Halte dich an dieses Schema:\n"
        + json.dumps(schema, ensure_ascii=False)
    )

def strip_json_fences(text: str) -> str:
    content = str(text or "").strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", content, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    return content

def first_balanced_json_object(text: str) -> Optional[str]:
    content = str(text or "")
    start = content.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(content)):
        char = content[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return content[start : index + 1]
    return None

def extract_json_payload(text: str) -> Dict[str, Any]:
    content = strip_json_fences(text)
    if not content:
        raise RuntimeError("Model returned empty content.")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    snippet = first_balanced_json_object(content)
    if snippet:
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            pass
    repaired = repair_truncated_json_object(content)
    if repaired is not None:
        return repaired
    raise RuntimeError(f"Model returned non-JSON content. First 500 chars:\n{content[:500]}")

def repair_truncated_json_object(text: str) -> Optional[Dict[str, Any]]:
    content = strip_json_fences(text)
    start = content.find("{")
    if start < 0:
        return None
    in_string = False
    escape = False
    stack: List[str] = []
    safe_points: List[Tuple[int, str, Tuple[str, ...]]] = []
    for index in range(start, len(content)):
        char = content[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char in "{[":
            stack.append(char)
            continue
        if char in "}]":
            if not stack:
                break
            opener = stack.pop()
            if (opener == "{" and char != "}") or (opener == "[" and char != "]"):
                break
            safe_points.append((index, char, tuple(stack)))
            continue
        if char == ",":
            safe_points.append((index, char, tuple(stack)))
    for index, char, stack_snapshot in reversed(safe_points):
        prefix = content[start:index] if char == "," else content[start : index + 1]
        prefix = prefix.rstrip().rstrip(",").rstrip()
        if not prefix:
            continue
        closing = "".join("}" if opener == "{" else "]" for opener in reversed(stack_snapshot))
        attempt = prefix + closing
        try:
            parsed = json.loads(attempt)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None

def normalize_plotpoint_entry(raw: Any) -> Optional[Dict[str, Any]]:
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        return {
            "id": make_id("pp"),
            "type": "story",
            "title": text[:120],
            "status": "active",
            "owner": None,
            "notes": text,
            "requirements": [],
        }
    if not isinstance(raw, dict):
        return None
    plotpoint = deep_copy(raw)
    pid = str(plotpoint.get("id") or plotpoint.get("point_id") or plotpoint.get("entry_id") or make_id("pp")).strip()
    title = str(plotpoint.get("title") or plotpoint.get("name") or plotpoint.get("description") or pid).strip()
    notes = str(plotpoint.get("notes") or plotpoint.get("description") or plotpoint.get("content") or "").strip()
    status = str(plotpoint.get("status") or "active").strip().lower()
    if status not in {"active", "done", "failed"}:
        status = "active"
    owner = str(plotpoint.get("owner") or "").strip() or None
    requirements = [str(entry).strip() for entry in (plotpoint.get("requirements") or []) if str(entry).strip()]
    normalized = {
        **plotpoint,
        "id": pid,
        "type": str(plotpoint.get("type") or "story").strip() or "story",
        "title": title or pid,
        "status": status,
        "owner": owner,
        "notes": notes,
        "requirements": requirements,
    }
    return normalized

def normalize_plotpoint_update_entry(raw: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    pid = str(raw.get("id") or raw.get("point_id") or raw.get("entry_id") or "").strip()
    if not pid:
        return None
    normalized: Dict[str, Any] = {"id": pid}
    if raw.get("status"):
        status = str(raw.get("status") or "").strip().lower()
        if status in {"active", "done", "failed"}:
            normalized["status"] = status
    notes = str(raw.get("notes") or raw.get("description") or raw.get("content") or "").strip()
    if notes:
        normalized["notes"] = notes
    return normalized

def normalize_event_entry(raw: Any) -> Optional[str]:
    if isinstance(raw, str):
        text = raw.strip()
        return text or None
    if isinstance(raw, dict):
        for key in ("text", "detail", "description", "content", "title", "name", "event"):
            text = str(raw.get(key) or "").strip()
            if text:
                return text
        return json.dumps(raw, ensure_ascii=False)[:300]
    text = str(raw or "").strip()
    return text or None

def repair_json_payload_with_model(
    system: str,
    broken_content: str,
    *,
    schema: Dict[str, Any],
    timeout: int = 90,
) -> Dict[str, Any]:
    repair_user = (
        "Die folgende Modellantwort sollte JSON sein, ist aber kaputt oder unvollständig.\n"
        "Repariere sie zu einem einzelnen gültigen JSON-Objekt gemäß Schema.\n"
        "Regeln:\n"
        "- Keine Markdown-Fences\n"
        "- Keine Erklärung\n"
        "- Fehlende optionale Felder mit leeren Standardwerten füllen\n"
        "- Wenn ein Feld im Schema ein Objekt erwartet, gib kein Array zurück\n"
        "- Halte vorhandene Inhalte so gut wie möglich inhaltlich stabil\n\n"
        "SCHEMA:\n"
        + json.dumps(schema, ensure_ascii=False)
        + "\n\nKAPUTTE_ANTWORT:\n"
        + str(broken_content or "")[:6000]
    )
    repaired = call_ollama_chat(
        system,
        repair_user,
        format_schema=schema,
        timeout=timeout,
        temperature=0.05,
        repeat_penalty=1.05,
    )
    return extract_json_payload(repaired)

def normalize_patch_payload(payload: Any) -> Dict[str, Any]:
    patch = payload if isinstance(payload, dict) else {}
    normalized = blank_patch()

    meta = patch.get("meta")
    if isinstance(meta, dict):
        normalized_meta: Dict[str, Any] = {}
        if meta.get("phase"):
            normalized_meta["phase"] = meta.get("phase")
        time_advance = meta.get("time_advance")
        if isinstance(time_advance, dict):
            normalized_meta["time_advance"] = {
                "days": int(time_advance.get("days", 0) or 0),
                "time_of_day": str(time_advance.get("time_of_day", "") or ""),
                "reason": str(time_advance.get("reason", "") or ""),
            }
        normalized["meta"] = normalized_meta

    for key in ("characters", "items_new"):
        value = patch.get(key)
        normalized[key] = value if isinstance(value, dict) else {}

    for key in ("plotpoints_add", "plotpoints_update", "map_add_nodes", "map_add_edges", "events_add"):
        value = patch.get(key)
        normalized[key] = value if isinstance(value, list) else []

    return normalized

def normalize_patch_semantics(patch: Any) -> Dict[str, Any]:
    normalized = normalize_patch_payload(patch)
    characters = normalized.get("characters") or {}
    for slot_name, upd in characters.items():
        if not isinstance(upd, dict):
            characters[slot_name] = {}
            continue
        scene_set = str(upd.get("scene_set") or "").strip()
        if scene_set and not str(upd.get("scene_id") or "").strip():
            upd["scene_id"] = scene_set
        upd.pop("scene_set", None)
    normalized["characters"] = characters
    return normalized

def merge_character_patch_update(base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    merged = deep_copy(base)
    for key, value in incoming.items():
        if key in {"bio_set", "resources_set", "resources_delta", "attributes_set", "attributes_delta", "skills_set", "skills_delta", "equip_set", "equipment_set", "inventory_set", "progression_set", "class_set", "class_update", "journal_add"}:
            target = merged.setdefault(key, {})
            if isinstance(target, dict) and isinstance(value, dict):
                target.update(deep_copy(value))
            else:
                merged[key] = deep_copy(value)
        elif key in {"conditions_add", "conditions_remove", "inventory_add", "inventory_remove", "abilities_add", "abilities_update", "potential_add", "factions_add", "factions_update", "injuries_add", "injuries_update", "injuries_heal", "scars_add", "appearance_flags_add", "effects_add", "effects_remove", "progression_events"}:
            merged.setdefault(key, [])
            if isinstance(value, list):
                merged[key].extend(deep_copy(value))
        else:
            merged[key] = deep_copy(value)
    return merged

def merge_patch_payloads(*patches: Dict[str, Any]) -> Dict[str, Any]:
    combined = blank_patch()
    for patch in patches:
        current = normalize_patch_semantics(patch)
        meta = current.get("meta") or {}
        if meta:
            combined_meta = combined.setdefault("meta", {})
            if "phase" in meta and meta.get("phase"):
                combined_meta["phase"] = meta.get("phase")
            if meta.get("time_advance"):
                combined_meta["time_advance"] = deep_copy(meta["time_advance"])
        for slot_name, upd in (current.get("characters") or {}).items():
            combined["characters"][slot_name] = merge_character_patch_update(combined["characters"].get(slot_name, {}), upd)
        combined["items_new"].update(deep_copy(current.get("items_new") or {}))
        for key in ("plotpoints_add", "plotpoints_update", "map_add_nodes", "map_add_edges", "events_add"):
            combined[key].extend(deep_copy(current.get(key) or []))
    return combined

def canonical_scene_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", normalized_eval_text(name)).strip("-")
    slug = slug[:40] or make_id("scene")
    return f"scene_{slug}"

def clean_scene_name(raw_name: str) -> str:
    name = str(raw_name or "").strip(" .,:;!?\"“”„'()[]{}")
    name = re.sub(r"\s+", " ", name).strip()
    stop_suffixes = (
        " und",
        " oder",
        " als",
        " wobei",
        " während",
        " doch",
        " dann",
        " dort",
        " wieder",
        " jetzt",
    )
    lowered = normalized_eval_text(name)
    for suffix in stop_suffixes:
        if lowered.endswith(suffix):
            cut = len(name) - len(suffix)
            name = name[:cut].strip(" .,:;!?\"“”„'")
            lowered = normalized_eval_text(name)
    return name

def is_plausible_scene_name(name: str) -> bool:
    normalized = normalized_eval_text(name)
    if not normalized or len(normalized) < 3:
        return False
    generic = {
        "welt",
        "nacht",
        "tag",
        "morgen",
        "abend",
        "dunkelheit",
        "schatten",
        "regen",
        "wind",
        "ferne",
        "stille",
        "chaos",
        "richtung",
        "bezug",
        "ort",
        "gebiet",
        "pfad",
        "weg",
        "gang",
        "unterholz",
        "vegetation",
        "schlucht",
        "wand",
        "nische",
        "raum",
        "kammer",
    }
    if normalized in generic:
        return False
    if normalized.startswith(("scene_", "node_", "plotpoint_")):
        return False
    return True

def is_generic_scene_identifier(scene_id: str, scene_name: str) -> bool:
    normalized_id = normalized_eval_text(scene_id)
    normalized_name = normalized_eval_text(scene_name)
    generic_tokens = {
        "richtung",
        "ort",
        "gebiet",
        "pfad",
        "weg",
        "gang",
        "nische",
        "kammer",
        "raum",
        "unterholz",
        "vegetation",
        "schlucht",
        "wand",
    }
    if normalized_id in {"", "scene"}:
        return True
    if normalized_id.startswith(("scene_richtung", "scene_ort", "scene_gebiet", "scene_pfad", "scene_weg")):
        return True
    if normalized_name in generic_tokens:
        return True
    return False

def extract_scene_candidates(text: str, actor_display: str) -> List[Dict[str, str]]:
    content = str(text or "")
    if not content.strip():
        return []
    name_pattern = r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9'’\-]+(?:\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9'’\-]+){0,5})"
    article_prefix = r"(?:den|die|das|dem|der|ein|eine|einen|einem|einer)\s+"
    arrival_patterns = (
        (rf"\bDie Gruppe (?:ist jetzt in|erreicht|betritt|gelangt nach|geht nach|zieht nach|kommt in|kommt nach)\s+(?:{article_prefix})?{name_pattern}", "group"),
        (rf"\bIhr (?:erreicht|betretet|gelangt nach|geht nach|kommt in|kommt nach|zieht nach)\s+(?:{article_prefix})?{name_pattern}", "group"),
        (rf"\bDie Gruppe [^.!?\n]*?\b(?:steht|steht jetzt|befindet sich|lagert|ruht|kämpft)\s+(?:in|an|auf|unter)\s+(?:{article_prefix})?{name_pattern}", "group"),
        (rf"\bIhr [^.!?\n]*?\b(?:steht|steht jetzt|befindet euch|seid|lagert|ruht|kämpft)\s+(?:in|an|auf|unter)\s+(?:{article_prefix})?{name_pattern}", "group"),
        (rf"\bDie Gruppe [^.!?\n]*?\bin den Ruinen von\s+(?:{article_prefix})?{name_pattern}", "group"),
        (rf"\bIhr [^.!?\n]*?\bin den Ruinen von\s+(?:{article_prefix})?{name_pattern}", "group"),
        (rf"\b{re.escape(actor_display)} (?:ist jetzt in|erreicht|betritt|gelangt nach|geht nach|zieht nach|kommt in|kommt nach)\s+(?:{article_prefix})?{name_pattern}", "actor"),
        (rf"\b{re.escape(actor_display)} [^.!?\n]*?\b(?:steht|steht jetzt|befindet sich|lagert|ruht|kämpft)\s+(?:in|an|auf|unter)\s+(?:{article_prefix})?{name_pattern}", "actor"),
        (rf"\b{re.escape(actor_display)} [^.!?\n]*?\bin den Ruinen von\s+(?:{article_prefix})?{name_pattern}", "actor"),
        (rf"\b(?:er|sie) (?:ist jetzt in|erreicht|betritt|gelangt nach|geht nach|zieht nach|kommt in|kommt nach)\s+(?:{article_prefix})?{name_pattern}", "actor"),
        (rf"\b(?:er|sie) [^.!?\n]*?\b(?:steht|steht jetzt|befindet sich|lagert|ruht|kämpft)\s+(?:in|an|auf|unter)\s+(?:{article_prefix})?{name_pattern}", "actor"),
        (rf"\b(?:er|sie) [^.!?\n]*?\bin den Ruinen von\s+(?:{article_prefix})?{name_pattern}", "actor"),
    )
    mention_patterns = (
        (rf"\bin den Ruinen von\s+{name_pattern}", "mention"),
        (rf"\bin der Nähe von\s+{name_pattern}", "mention"),
        (rf"\bnahe\s+{name_pattern}", "mention"),
        (rf"\bam\s+{name_pattern}", "mention"),
        (rf"\bauf dem\s+{name_pattern}", "mention"),
        (rf"\bauf der\s+{name_pattern}", "mention"),
        (rf"\bentlang der\s+{name_pattern}", "mention"),
        (rf"\bvor euch liegt\s+{name_pattern}", "mention"),
        (rf"\bvor ihnen liegt\s+{name_pattern}", "mention"),
        (rf"\bdie Stadt\s+{name_pattern}", "mention"),
        (rf"\bdas Dorf\s+{name_pattern}", "mention"),
        (rf"\bdie Festung\s+{name_pattern}", "mention"),
        (rf"\bdie Ruinen von\s+{name_pattern}", "mention"),
        (rf"\bdas Gebiet\s+{name_pattern}", "mention"),
        (rf"\bam Ort\s+{name_pattern}", "mention"),
    )
    found: List[Dict[str, str]] = []
    seen = set()
    for pattern, scope in (*arrival_patterns, *mention_patterns):
        for match in re.finditer(pattern, content):
            raw_name = clean_scene_name(match.group(1) or "")
            normalized_name = normalized_eval_text(raw_name)
            if not raw_name or len(normalized_name) < 3 or not is_plausible_scene_name(raw_name):
                continue
            key = (scope, normalized_name)
            if key in seen:
                continue
            seen.add(key)
            found.append({"scope": scope, "name": raw_name})
    return found

def extract_descriptive_scene_name(text: str) -> Optional[str]:
    content = str(text or "")
    descriptor_patterns = (
        r"\bin (?:einer|einem|der|dem|eine|ein)\s+([a-zäöüß][a-zäöüß\-\s]{2,48}?(?:nische|kammer|gang|krypta|ruine|tempel|lichtung|schlucht))\b",
        r"\bam (?:rand|eingang) (?:von|der)\s+([a-zäöüß][a-zäöüß\-\s]{2,48}?(?:ruine|krypta|lichtung|schlucht|festung|tempel))\b",
    )
    for pattern in descriptor_patterns:
        match = re.search(pattern, content, flags=re.IGNORECASE)
        if not match:
            continue
        candidate = clean_scene_name(match.group(1) or "")
        if not candidate:
            continue
        normalized = normalized_eval_text(candidate)
        if not normalized or not is_plausible_scene_name(candidate):
            continue
        return candidate[:80].strip()
    return None

def build_scene_patch_from_text(campaign: Dict[str, Any], state: Dict[str, Any], actor: str, text: str) -> Dict[str, Any]:
    actor_display = display_name_for_slot(campaign, actor)
    candidates = extract_scene_candidates(text, actor_display)
    if not candidates:
        return blank_patch()
    patch = blank_patch()
    known_scene_ids = set((state.get("scenes") or {}).keys()) | set(((state.get("map") or {}).get("nodes") or {}).keys())
    scene_was_set = False
    for candidate in candidates:
        if candidate["scope"] == "mention":
            continue
        scene_name = candidate["name"]
        scene_id = canonical_scene_id(scene_name)
        if scene_id not in known_scene_ids and not any(node.get("id") == scene_id for node in patch["map_add_nodes"]):
            patch["map_add_nodes"].append(
                {
                    "id": scene_id,
                    "name": scene_name,
                    "type": "location",
                    "danger": 1,
                    "discovered": True,
                }
            )
        targets = active_party(campaign) if candidate["scope"] == "group" and active_party(campaign) else [actor]
        for slot_name in targets:
            patch["characters"].setdefault(slot_name, {})["scene_id"] = scene_id
            scene_was_set = True
        patch["events_add"].append(f"{'Die Gruppe' if candidate['scope'] == 'group' else actor_display} erreicht {scene_name}.")
    if not scene_was_set:
        current_scene = str((((state.get("characters") or {}).get(actor) or {}).get("scene_id") or "")).strip()
        if not current_scene:
            descriptor_scene = extract_descriptive_scene_name(text)
            if descriptor_scene and re.search(r"\b(?:erreicht|betritt|gelangt|kommt|geht|zieht|befindet sich|steht jetzt|ist jetzt in)\b", normalized_eval_text(text)):
                scene_id = canonical_scene_id(descriptor_scene)
                patch["map_add_nodes"].append(
                    {
                        "id": scene_id,
                        "name": descriptor_scene,
                        "type": "location",
                        "danger": 1,
                        "discovered": True,
                    }
                )
                patch["characters"].setdefault(actor, {})["scene_id"] = scene_id
                patch["events_add"].append(f"{actor_display} befindet sich nun bei {descriptor_scene}.")
    return patch

def infer_scene_name_from_recent_story(campaign: Dict[str, Any], slot_name: str) -> Optional[str]:
    actor_display = display_name_for_slot(campaign, slot_name)
    turns = list(reversed(campaign.get("turns") or []))
    for turn in turns:
        if turn.get("status") != "active":
            continue
        if turn.get("actor") != slot_name:
            continue
        story_text = str(turn.get("gm_text_display") or "")
        if not story_text.strip():
            continue
        candidates = extract_scene_candidates(story_text, actor_display)
        for candidate in candidates:
            if candidate["scope"] in {"actor", "group"}:
                if not is_generic_scene_identifier(canonical_scene_id(candidate["name"]), candidate["name"]):
                    return candidate["name"]
        fallback = extract_descriptive_scene_name(story_text)
        if fallback and re.search(r"\b(?:erreicht|betritt|gelangt|kommt|geht|zieht|befindet sich|steht jetzt|ist jetzt in)\b", normalized_eval_text(story_text)):
            return fallback
    return None

def reconcile_scene_ids_with_story(campaign: Dict[str, Any]) -> None:
    state = campaign.get("state") or {}
    characters = state.get("characters") or {}
    scenes = state.setdefault("scenes", {})
    map_nodes = (state.setdefault("map", {})).setdefault("nodes", {})
    for slot_name, character in characters.items():
        current_scene_id = str((character or {}).get("scene_id") or "").strip()
        current_scene_name = derive_scene_name(campaign, slot_name)
        if current_scene_id and not is_generic_scene_identifier(current_scene_id, current_scene_name):
            continue
        inferred_name = infer_scene_name_from_recent_story(campaign, slot_name)
        if not inferred_name:
            continue
        inferred_scene_id = canonical_scene_id(inferred_name)
        if is_generic_scene_identifier(inferred_scene_id, inferred_name):
            continue
        character["scene_id"] = inferred_scene_id
        scenes.setdefault(
            inferred_scene_id,
            {"name": inferred_name, "tone": "", "danger": 1, "notes": ""},
        )
        map_nodes.setdefault(
            inferred_scene_id,
            {"id": inferred_scene_id, "name": inferred_name, "type": "location", "danger": 1, "discovered": True},
        )

def infer_injury_severity(sentence: str, title: str) -> str:
    lowered = normalized_eval_text(f"{sentence} {title}")
    if any(marker in lowered for marker in ("gebrochen", "klaffend", "offen", "tiefer", "schwere", "schwerer", "schweren")):
        return "schwer"
    if any(marker in lowered for marker in ("blut", "brand", "biss", "schnitt", "stich", "prell", "verstauch")):
        return "mittel"
    return "leicht"

def infer_injury_effects(title: str, severity: str) -> List[str]:
    normalized_title = normalized_eval_text(title)
    effects: List[str] = []
    if any(marker in normalized_title for marker in ("arm", "hand", "schulter")):
        effects.append("Schmerz bei Kraft")
    if any(marker in normalized_title for marker in ("bein", "knie", "fuss", "fuß", "huefte", "hüfte")):
        effects.append("Schmerz bei Bewegung")
    if any(marker in normalized_title for marker in ("brust", "rippe", "bauch")):
        effects.append("Atemnot unter Belastung")
    if severity == "schwer":
        effects.append("Erschwert konzentrierte Aktionen")
    elif severity == "mittel":
        effects.append("Belastung verschlimmert den Schmerz")
    return list(dict.fromkeys([entry for entry in effects if entry])) or ["Schmerz bei Belastung"]

def clean_auto_injury_title(raw_title: str) -> str:
    title = clean_scene_name(raw_title)
    title = re.sub(
        r"\s+(zwingt|laesst|lässt|macht|verursacht|hindert|bringt|treibt|wirft)\b.*$",
        "",
        title,
        flags=re.IGNORECASE,
    ).strip()
    return title

def extract_auto_story_injuries(story_text: str, actor_display: str) -> List[Dict[str, Any]]:
    actor_name = normalized_eval_text(actor_display)
    story_mentions_actor = actor_name in normalized_eval_text(story_text)
    candidates: List[Dict[str, Any]] = []
    seen = set()
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", str(story_text or "")):
        sentence = sentence.strip()
        if not sentence:
            continue
        normalized_sentence = normalized_eval_text(sentence)
        if actor_name and not sentence_mentions_actor_name(sentence, actor_display) and not normalized_sentence.startswith(("er ", "sie ", "es ")) and not story_mentions_actor:
            continue
        for pattern in AUTO_INJURY_PATTERNS:
            for match in pattern.findall(sentence):
                raw_match = " ".join(part for part in match) if isinstance(match, tuple) else str(match or "")
                title = clean_auto_injury_title(raw_match)
                normalized_title = normalized_eval_text(title)
                if not title or normalized_title in seen:
                    continue
                seen.add(normalized_title)
                severity = infer_injury_severity(sentence, title)
                candidates.append(
                    {
                        "id": make_id("inj"),
                        "title": title[:80],
                        "severity": severity,
                        "effects": infer_injury_effects(title, severity),
                        "healing_stage": "frisch",
                        "will_scar": severity != "leicht" or any(marker in normalized_title for marker in ("schnitt", "stich", "biss", "brand", "gebrochen")),
                        "created_turn": 0,
                        "notes": sentence[:220].strip(),
                    }
                )
                if len(candidates) >= 2:
                    return candidates
    return candidates

def sorted_npc_codex_entries(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    codex = (state.get("npc_codex") or {})
    entries = [entry for entry in codex.values() if isinstance(entry, dict) and entry.get("name")]
    entries.sort(
        key=lambda entry: (
            int(entry.get("relevance_score", 0) or 0),
            int(entry.get("last_seen_turn", 0) or 0),
            int(entry.get("mention_count", 0) or 0),
            str(entry.get("name", "")),
        ),
        reverse=True,
    )
    return entries

def build_npc_codex_summary(state: Dict[str, Any], *, limit: int = 16) -> List[Dict[str, Any]]:
    summary: List[Dict[str, Any]] = []
    for entry in sorted_npc_codex_entries(state)[: max(1, int(limit or 1))]:
        summary.append(
            {
                "npc_id": entry.get("npc_id"),
                "name": entry.get("name"),
                "race": entry.get("race"),
                "goal": entry.get("goal"),
                "level": entry.get("level"),
                "class_name": ((normalize_class_current(entry.get("class_current")) or {}).get("name") or ""),
                "class_rank": ((normalize_class_current(entry.get("class_current")) or {}).get("rank") or ""),
                "faction": entry.get("faction"),
                "role_hint": entry.get("role_hint"),
                "status": entry.get("status"),
                "scene_id": entry.get("last_seen_scene_id"),
                "last_seen_turn": entry.get("last_seen_turn"),
                "mention_count": entry.get("mention_count"),
                "relevance_score": entry.get("relevance_score"),
            }
        )
    return summary

def sorted_world_profiles(state: Dict[str, Any], *, kind: str) -> List[Tuple[str, Dict[str, Any]]]:
    world = state.get("world") or {}
    source = world.get("races") if kind == CODEX_KIND_RACE else world.get("beast_types")
    if not isinstance(source, dict):
        return []
    rows = [(str(entity_id), profile) for entity_id, profile in source.items() if isinstance(profile, dict)]
    rows.sort(key=lambda row: (normalize_codex_alias_text((row[1] or {}).get("name", "")), row[0]))
    return rows

def build_race_codex_summary(state: Dict[str, Any], *, limit: int = 32) -> List[Dict[str, Any]]:
    codex_races = (((state.get("codex") or {}).get("races") or {})
                   if isinstance(((state.get("codex") or {}).get("races") or {}), dict) else {})
    summary: List[Dict[str, Any]] = []
    for race_id, profile in sorted_world_profiles(state, kind=CODEX_KIND_RACE)[: max(1, int(limit or 1))]:
        entry = normalize_codex_entry_stable(codex_races.get(race_id), kind=CODEX_KIND_RACE)
        summary.append(
            {
                "race_id": race_id,
                "name": str((profile or {}).get("name") or race_id),
                "knowledge_level": int(entry.get("knowledge_level", 0) or 0),
                "discovered": bool(entry.get("discovered")),
                "known_blocks": deep_copy(entry.get("known_blocks") or []),
                "known_facts": deep_copy(entry.get("known_facts") or []),
                "encounter_count": int(entry.get("encounter_count", 0) or 0),
            }
        )
    return summary

def build_beast_codex_summary(state: Dict[str, Any], *, limit: int = 40) -> List[Dict[str, Any]]:
    codex_beasts = (((state.get("codex") or {}).get("beasts") or {})
                    if isinstance(((state.get("codex") or {}).get("beasts") or {}), dict) else {})
    summary: List[Dict[str, Any]] = []
    for beast_id, profile in sorted_world_profiles(state, kind=CODEX_KIND_BEAST)[: max(1, int(limit or 1))]:
        entry = normalize_codex_entry_stable(codex_beasts.get(beast_id), kind=CODEX_KIND_BEAST)
        summary.append(
            {
                "beast_id": beast_id,
                "name": str((profile or {}).get("name") or beast_id),
                "knowledge_level": int(entry.get("knowledge_level", 0) or 0),
                "discovered": bool(entry.get("discovered")),
                "known_blocks": deep_copy(entry.get("known_blocks") or []),
                "known_facts": deep_copy(entry.get("known_facts") or []),
                "encounter_count": int(entry.get("encounter_count", 0) or 0),
                "defeated_count": int(entry.get("defeated_count", 0) or 0),
            }
        )
    return summary

def build_world_element_summary(state: Dict[str, Any], *, limit: int = 16) -> List[Dict[str, Any]]:
    world = state.get("world") if isinstance(state.get("world"), dict) else {}
    rows = []
    for element_id, profile in ((world.get("elements") or {}).items()):
        if not isinstance(profile, dict):
            continue
        rows.append(
            {
                "id": element_id,
                "name": str(profile.get("name") or element_id),
                "origin": str(profile.get("origin") or "generated"),
                "theme": str(profile.get("theme") or ""),
                "status_effect_tags": deep_copy(profile.get("status_effect_tags") or []),
                "class_affinities": deep_copy(profile.get("class_affinities") or []),
                "skill_affinities": deep_copy(profile.get("skill_affinities") or []),
            }
        )
    rows.sort(key=lambda entry: (normalize_codex_alias_text(entry.get("name", "")), entry.get("id", "")))
    return rows[: max(1, int(limit or 1))]

def build_extractor_context_packet(
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    actor: str,
    action_type: str,
    source_text: str,
    *,
    source: str,
) -> str:
    world_settings = ((state.get("world") or {}).get("settings") or {})
    payload = {
        "source": source,
        "action_type": action_type,
        "actor": actor,
        "actor_display": display_name_for_slot(campaign, actor) if is_slot_id(actor) else actor,
        "active_party": active_party(campaign),
        "display_party": [
            {"slot_id": slot_name, "display_name": display_name_for_slot(campaign, slot_name)}
            for slot_name in active_party(campaign)
        ],
        "characters": {
            slot_name: {
                "display_name": display_name_for_slot(campaign, slot_name),
                "scene_id": (state.get("characters", {}).get(slot_name) or {}).get("scene_id", ""),
                "element_affinities": (state.get("characters", {}).get(slot_name) or {}).get("element_affinities", []),
                "element_resistances": (state.get("characters", {}).get(slot_name) or {}).get("element_resistances", []),
                "element_weaknesses": (state.get("characters", {}).get(slot_name) or {}).get("element_weaknesses", []),
                "class_current": normalize_class_current((state.get("characters", {}).get(slot_name) or {}).get("class_current")),
                "skills": [
                    {
                        "id": skill.get("id"),
                        "name": skill.get("name"),
                        "rank": skill.get("rank"),
                        "level": skill.get("level"),
                        "tags": skill.get("tags", []),
                        "elements": skill.get("elements", []),
                        "element_primary": skill.get("element_primary"),
                    }
                    for skill in sorted(
                        [
                            normalize_dynamic_skill_state(
                                skill_value,
                                skill_id=skill_id,
                                skill_name=(skill_value or {}).get("name", skill_id) if isinstance(skill_value, dict) else skill_id,
                                resource_name=resource_name_for_character((state.get("characters", {}).get(slot_name) or {}), world_settings),
                            )
                            for skill_id, skill_value in (((state.get("characters", {}).get(slot_name) or {}).get("skills") or {}).items())
                        ],
                        key=lambda entry: (skill_rank_sort_value(entry.get("rank")), entry.get("level", 1), entry.get("name", "")),
                        reverse=True,
                    )
                ],
                "inventory_names": [
                    ((state.get("items", {}) or {}).get(entry.get("item_id"), {}) or {}).get("name", "")
                    for entry in list_inventory_items((state.get("characters", {}).get(slot_name) or {}))
                ],
            }
            for slot_name in campaign_slots(campaign)
        },
        "known_scenes": {
            scene_id: scene.get("name", scene_id)
            for scene_id, scene in (state.get("scenes") or {}).items()
        },
        "known_items": {
            item_id: item.get("name", "")
            for item_id, item in (state.get("items") or {}).items()
        },
        "world_races": {
            race_id: {
                "name": race.get("name", race_id),
                "aliases": race.get("aliases", []),
            }
            for race_id, race in ((state.get("world") or {}).get("races") or {}).items()
        },
        "world_beast_types": {
            beast_id: {
                "name": beast.get("name", beast_id),
                "aliases": beast.get("aliases", []),
            }
            for beast_id, beast in ((state.get("world") or {}).get("beast_types") or {}).items()
        },
        "world_elements": {
            element_id: {
                "name": element.get("name", element_id),
                "origin": element.get("origin", "generated"),
                "aliases": element.get("aliases", []),
            }
            for element_id, element in ((state.get("world") or {}).get("elements") or {}).items()
        },
        "world_element_relations": (state.get("world") or {}).get("element_relations", {}),
        "world_element_paths": (state.get("world") or {}).get("element_class_paths", {}),
        "world_element_summary": build_world_element_summary(state, limit=18),
        "race_codex_summary": build_race_codex_summary(state, limit=20),
        "beast_codex_summary": build_beast_codex_summary(state, limit=20),
        "npc_codex_summary": build_npc_codex_summary(state, limit=18),
        "npc_codex": (state.get("npc_codex") or {}) if len((state.get("npc_codex") or {})) <= 24 else {},
        "source_text": source_text,
    }
    return json.dumps(payload, ensure_ascii=False)

def normalize_extractor_output_patch(payload: Any) -> Dict[str, Any]:
    candidate = payload.get("patch") if isinstance(payload, dict) and "patch" in payload else payload
    return normalize_patch_semantics(candidate)

def resolve_extractor_conflicts(
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    actor: str,
    action_type: str,
    source_text: str,
    patch: Dict[str, Any],
    *,
    source: str,
) -> Dict[str, Any]:
    resolved = normalize_patch_semantics(patch)
    allow_retcon = action_type == "canon" or str(source_text or "").strip().lower().startswith("retcon:")
    if source == "player" and not allow_retcon:
        actor_patch = (resolved.get("characters") or {}).get(actor) or {}
        next_scene = str(actor_patch.get("scene_id") or "").strip()
        current_scene = str(((state.get("characters", {}) or {}).get(actor) or {}).get("scene_id") or "").strip()
        if next_scene and current_scene and next_scene != current_scene:
            resolved["characters"][actor].pop("scene_id", None)
            if not resolved["characters"][actor]:
                resolved["characters"].pop(actor, None)
            resolved.setdefault("events_add", []).append(
                f"Widerspruch erkannt: {display_name_for_slot(campaign, actor)} kann den Ort nicht still über STORY/DO/SAY überschreiben."
            )
            resolved["map_add_nodes"] = [node for node in (resolved.get("map_add_nodes") or []) if node.get("id") != next_scene]
    for slot_name, upd in list((resolved.get("characters") or {}).items()):
        cleaned_abilities = []
        converted_skills = upd.setdefault("skills_set", {})
        character_resource = resource_name_for_character(((state.get("characters", {}) or {}).get(slot_name) or {}), ((state.get("world") or {}).get("settings") or {}))
        for ability in upd.get("abilities_add", []) or []:
            ability_name = clean_auto_ability_name(ability.get("name", ""))
            normalized_name = normalized_eval_text(ability_name)
            if normalized_name in UNIVERSAL_SKILL_LIKE_NAMES:
                skill_id = skill_id_from_name(ability_name)
                converted_skills[skill_id] = normalize_dynamic_skill_state(
                    {
                        "id": skill_id,
                        "name": ability_name,
                        "rank": "F",
                        "level": 1,
                        "level_max": 10,
                        "tags": list(dict.fromkeys([*(ability.get("tags") or []), "allgemein"])),
                        "description": str(ability.get("description", "") or f"{ability_name} wurde kanonisch gelernt."),
                        "cost": None,
                        "price": None,
                        "cooldown_turns": None,
                        "unlocked_from": "Canon Extractor",
                        "synergy_notes": None,
                    },
                    resource_name=character_resource,
                )
                continue
            cleaned_abilities.append(ability)
        if "abilities_add" in upd:
            upd["abilities_add"] = cleaned_abilities
    return resolved

def make_extraction_candidate(
    *,
    state: Dict[str, Any],
    actor: str,
    source: str,
    entity_type: str,
    operation: str,
    label: str,
    normalized_key: str,
    evidence_text: str,
    payload: Dict[str, Any],
    confidence: float,
) -> Dict[str, Any]:
    return {
        "candidate_id": make_id("xc"),
        "source": str(source or "unknown"),
        "actor": str(actor or ""),
        "turn": max(0, int(((state.get("meta") or {}).get("turn", 0) or 0))),
        "entity_type": str(entity_type or "unknown"),
        "operation": str(operation or ""),
        "label": str(label or "").strip(),
        "normalized_key": str(normalized_key or "").strip(),
        "evidence_text": str(evidence_text or "").strip(),
        "payload": deep_copy(payload or {}),
        "confidence": float(clamp_float(float(confidence or 0.0), 0.0, 1.0)),
        "status": "review",
        "reason_code": EXTRACTION_REASON_LOW_CONFIDENCE,
        "created_at": utc_now(),
    }

def candidate_status_rank(status: str) -> int:
    lowered = str(status or "").strip().lower()
    if lowered == "safe":
        return 3
    if lowered == "review":
        return 2
    return 1

def item_name_in_character_inventory(state: Dict[str, Any], slot_name: str, item_name: str) -> bool:
    normalized_name = normalized_eval_text(item_name)
    if not normalized_name:
        return False
    character = ((state.get("characters") or {}).get(slot_name) or {})
    items_db = state.get("items") or {}
    for entry in list_inventory_items(character):
        item_id = str(entry.get("item_id") or "").strip()
        if not item_id:
            continue
        item = items_db.get(item_id) or {}
        if normalized_eval_text(str(item.get("name") or "")) == normalized_name:
            return True
    return False

def extract_environment_item_mentions(story_text: str, actor_display: str) -> List[Dict[str, str]]:
    mentions: List[Dict[str, str]] = []
    seen = set()
    pattern = re.compile(
        r"\b(?:liegt|liegen|stand|steht|stehen|haengt|hängt|hingen)\s+(?:ein|eine|einen|der|die|das)\s+([^,.!?;\n]{3,80})",
        flags=re.IGNORECASE,
    )
    actor_relevant = actor_relevant_story_sentences(story_text, actor_display)
    actor_relevant_set = set(actor_relevant)
    sentence_pool = list(actor_relevant)
    if not sentence_pool:
        sentence_pool = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", str(story_text or ""))
            if sentence.strip()
        ]
    for sentence in sentence_pool:
        lowered = normalized_eval_text(sentence)
        if sentence not in actor_relevant_set and not re.search(r"\b(ihm|ihr|ihnen)\b", lowered):
            continue
        if any(pattern_acq.search(sentence) for pattern_acq in AUTO_ITEM_ACQUIRE_PATTERNS):
            continue
        if any(pattern_eq.search(sentence) for pattern_eq in AUTO_ITEM_EQUIP_PATTERNS):
            continue
        for match in pattern.findall(sentence):
            item_name = clean_auto_item_name(match)
            normalized_name = normalized_eval_text(item_name)
            if not item_name or not normalized_name or normalized_name in seen:
                continue
            seen.add(normalized_name)
            mentions.append({"name": item_name, "sentence": sentence})
    return mentions

def build_heuristic_candidates(
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    actor: str,
    action_type: str,
    source_text: str,
    *,
    source: str,
) -> List[Dict[str, Any]]:
    if not str(source_text or "").strip():
        return []
    candidates: List[Dict[str, Any]] = []
    seen_keys: set = set()
    actor_display = display_name_for_slot(campaign, actor) if is_slot_id(actor) else actor
    normalized_content = normalized_eval_text(source_text)

    def push(candidate: Dict[str, Any]) -> None:
        key = str(candidate.get("normalized_key") or "").strip()
        if not key or key in seen_keys:
            return
        seen_keys.add(key)
        candidates.append(candidate)

    if actor in (state.get("characters") or {}):
        class_payload = extract_auto_class_change(source_text, actor_display)
        if class_payload:
            normalized_class = normalize_class_current(class_payload)
            if normalized_class:
                class_label = str(normalized_class.get("name") or normalized_class.get("id") or "").strip()
                push(
                    make_extraction_candidate(
                        state=state,
                        actor=actor,
                        source=source,
                        entity_type="class",
                        operation="set_class",
                        label=class_label,
                        normalized_key=f"class:{normalized_eval_text(str(normalized_class.get('id') or class_label))}",
                        evidence_text=source_text,
                        payload={"class_set": normalized_class},
                        confidence=0.86,
                    )
                )
        elif "klasse" in normalized_content and actor_display and normalized_eval_text(actor_display) in normalized_content:
            push(
                make_extraction_candidate(
                    state=state,
                    actor=actor,
                    source=source,
                    entity_type="class",
                    operation="set_class",
                    label="Klassenhinweis",
                    normalized_key=f"class:ambiguous:{actor}",
                    evidence_text=source_text,
                    payload={"ambiguous": True},
                    confidence=0.25,
                )
            )

        for learned in extract_auto_learned_abilities(source_text, actor_display):
            skill_name = str(learned.get("name") or "").strip()
            if not skill_name:
                continue
            push(
                make_extraction_candidate(
                    state=state,
                    actor=actor,
                    source=source,
                    entity_type="skill",
                    operation="add_skill",
                    label=skill_name,
                    normalized_key=f"skill:{normalized_eval_text(skill_name)}",
                    evidence_text=str(learned.get("description") or source_text),
                    payload={
                        "name": skill_name,
                        "description": str(learned.get("description") or "").strip(),
                        "tags": deep_copy(learned.get("tags") or []),
                        "type": str(learned.get("type") or "active"),
                        "explicit_learn": True,
                    },
                    confidence=0.78,
                )
            )

        verb_style_match = re.search(
            r"\b(?:ich|er|sie)\s+(?:kaempft|kämpft|rennt|springt|weicht|bewegt\s+sich)\b",
            normalized_content,
        )
        if verb_style_match and not any(cue in normalized_content for cue in STORY_LEARN_CUES):
            label = str(verb_style_match.group(0) or "stilaktion").strip()
            push(
                make_extraction_candidate(
                    state=state,
                    actor=actor,
                    source=source,
                    entity_type="skill",
                    operation="add_skill",
                    label=label,
                    normalized_key=f"skill:verbstyle:{normalized_eval_text(label)}",
                    evidence_text=source_text,
                    payload={"mode": "style_verb"},
                    confidence=0.2,
                )
            )

        for event in extract_auto_story_item_events(source_text, actor_display):
            item_name = str(event.get("name") or "").strip()
            if not item_name:
                continue
            push(
                make_extraction_candidate(
                    state=state,
                    actor=actor,
                    source=source,
                    entity_type="item",
                    operation="add_item",
                    label=item_name,
                    normalized_key=f"item:{normalized_eval_text(item_name)}",
                    evidence_text=str(event.get("sentence") or source_text),
                    payload={
                        "name": item_name,
                        "mode": str(event.get("mode") or "acquire"),
                        "sentence": str(event.get("sentence") or source_text),
                    },
                    confidence=0.8 if str(event.get("mode") or "") in {"acquire", "equip"} else 0.55,
                )
            )

        for mention in extract_environment_item_mentions(source_text, actor_display):
            item_name = str(mention.get("name") or "").strip()
            if not item_name:
                continue
            push(
                make_extraction_candidate(
                    state=state,
                    actor=actor,
                    source=source,
                    entity_type="item",
                    operation="add_item",
                    label=item_name,
                    normalized_key=f"item:env:{normalized_eval_text(item_name)}",
                    evidence_text=str(mention.get("sentence") or source_text),
                    payload={"name": item_name, "mode": "environment_only"},
                    confidence=0.2,
                )
            )

    for scene in extract_scene_candidates(source_text, actor_display):
        scene_name = str(scene.get("name") or "").strip()
        if not scene_name:
            continue
        scope = str(scene.get("scope") or "").strip().lower()
        scene_id = canonical_scene_id(scene_name)
        targets = active_party(campaign) if scope == "group" and active_party(campaign) else [actor]
        push(
            make_extraction_candidate(
                state=state,
                actor=actor,
                source=source,
                entity_type="map",
                operation="add_scene",
                label=scene_name,
                normalized_key=f"scene:{scene_id}",
                evidence_text=source_text,
                payload={
                    "scene_id": scene_id,
                    "scene_name": scene_name,
                    "scope": scope,
                    "targets": targets,
                },
                confidence=0.82 if scope in {"actor", "group"} else 0.4,
            )
        )
    return candidates

def classify_heuristic_candidate(
    candidate: Dict[str, Any],
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    actor: str,
    source_text: str,
) -> Dict[str, Any]:
    classified = deep_copy(candidate)
    entity_type = str(classified.get("entity_type") or "").strip().lower()
    label = str(classified.get("label") or "").strip()
    payload = classified.get("payload") if isinstance(classified.get("payload"), dict) else {}
    status = "review"
    reason_code = EXTRACTION_REASON_LOW_CONFIDENCE
    confidence = float(classified.get("confidence", 0.0) or 0.0)

    if entity_type == "map":
        scene_id = str(payload.get("scene_id") or canonical_scene_id(label)).strip()
        generic_names = {
            "dorf",
            "wald",
            "strasse",
            "straße",
            "raum",
            "gebaude",
            "gebäude",
            "tuer",
            "tür",
            "haus",
            "gegend",
        }
        normalized_label = normalized_eval_text(label)
        scope = str(payload.get("scope") or "").strip().lower()
        if normalized_label in generic_names or is_generic_scene_identifier(scene_id, label):
            status = "reject"
            reason_code = EXTRACTION_REASON_GENERIC_LOCATION
            confidence = min(confidence, 0.25)
        elif scope in {"actor", "group"}:
            status = "safe"
            reason_code = "SAFE_CONFIRMED"
            confidence = max(confidence, 0.75)
        else:
            status = "review"
            reason_code = EXTRACTION_REASON_LOW_CONFIDENCE
    elif entity_type == "item":
        mode = str(payload.get("mode") or "").strip().lower()
        normalized_label = normalized_eval_text(label)
        if mode == "environment_only":
            status = "reject"
            reason_code = EXTRACTION_REASON_ENV_OBJECT
            confidence = min(confidence, 0.25)
        elif normalized_label in {normalized_eval_text(entry) for entry in AUTO_ITEM_GENERIC_NAMES}:
            status = "reject"
            reason_code = EXTRACTION_REASON_ENV_OBJECT
            confidence = min(confidence, 0.2)
        elif mode in {"acquire", "equip"}:
            status = "safe"
            reason_code = "SAFE_CONFIRMED"
            confidence = max(confidence, 0.72)
        else:
            status = "review"
            reason_code = EXTRACTION_REASON_MISSING_ACQUIRE
            confidence = min(confidence, 0.45)
        if status == "safe" and item_name_in_character_inventory(state, actor, label):
            status = "review"
            reason_code = EXTRACTION_REASON_DUPLICATE
            confidence = min(confidence, 0.5)
    elif entity_type == "skill":
        if str(payload.get("mode") or "").strip().lower() == "style_verb":
            status = "reject"
            reason_code = EXTRACTION_REASON_VERB_STYLE_SKILL
            confidence = min(confidence, 0.25)
        elif payload.get("explicit_learn"):
            status = "safe"
            reason_code = "SAFE_CONFIRMED"
            confidence = max(confidence, 0.72)
        else:
            status = "review"
            reason_code = EXTRACTION_REASON_LOW_CONFIDENCE
        if status == "safe":
            existing_skill_names = {
                normalized_eval_text((entry or {}).get("name", ""))
                for entry in (((state.get("characters") or {}).get(actor) or {}).get("skills") or {}).values()
                if isinstance(entry, dict)
            }
            if normalized_eval_text(label) in existing_skill_names:
                status = "review"
                reason_code = EXTRACTION_REASON_DUPLICATE
                confidence = min(confidence, 0.5)
    elif entity_type == "class":
        class_set = normalize_class_current(payload.get("class_set"))
        if payload.get("ambiguous") or not class_set:
            status = "review"
            reason_code = EXTRACTION_REASON_AMBIGUOUS_CLASS
            confidence = min(confidence, 0.35)
        else:
            existing_class = normalize_class_current((((state.get("characters") or {}).get(actor) or {}).get("class_current")))
            if existing_class and (
                normalized_eval_text(existing_class.get("id", "")) == normalized_eval_text(class_set.get("id", ""))
                or normalized_eval_text(existing_class.get("name", "")) == normalized_eval_text(class_set.get("name", ""))
            ):
                status = "review"
                reason_code = EXTRACTION_REASON_DUPLICATE
                confidence = min(confidence, 0.45)
            else:
                status = "safe"
                reason_code = "SAFE_CONFIRMED"
                confidence = max(confidence, 0.78)
            payload["class_set"] = class_set
    else:
        status = "reject"
        reason_code = EXTRACTION_REASON_LOW_CONFIDENCE
        confidence = min(confidence, 0.2)

    classified["payload"] = payload
    classified["status"] = status
    classified["reason_code"] = reason_code
    classified["confidence"] = clamp_float(confidence, 0.0, 1.0)
    return classified

def split_candidates(candidates: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    deduped: Dict[str, Dict[str, Any]] = {}
    for candidate in candidates:
        key = str(candidate.get("normalized_key") or "").strip() or str(candidate.get("candidate_id") or make_id("xc"))
        current = deduped.get(key)
        if current is None:
            deduped[key] = candidate
            continue
        current_rank = candidate_status_rank(current.get("status", "reject"))
        incoming_rank = candidate_status_rank(candidate.get("status", "reject"))
        if incoming_rank > current_rank:
            deduped[key] = candidate
            continue
        if incoming_rank == current_rank and float(candidate.get("confidence", 0.0) or 0.0) > float(current.get("confidence", 0.0) or 0.0):
            deduped[key] = candidate
    safe: List[Dict[str, Any]] = []
    review: List[Dict[str, Any]] = []
    reject: List[Dict[str, Any]] = []
    for candidate in deduped.values():
        status = str(candidate.get("status") or "").strip().lower()
        if status == "safe":
            safe.append(candidate)
        elif status == "review":
            review.append(candidate)
        else:
            reject.append(candidate)
    return safe, review, reject

def append_extraction_quarantine(state: Dict[str, Any], candidates_review_reject: List[Dict[str, Any]]) -> None:
    if not candidates_review_reject:
        return
    meta = state.setdefault("meta", {})
    quarantine = normalize_extraction_quarantine_meta(meta)
    entries = quarantine.setdefault("entries", [])
    seen = {
        (
            int(entry.get("turn", 0) or 0),
            str(entry.get("actor") or ""),
            str(entry.get("source") or ""),
            str(entry.get("entity_type") or ""),
            normalized_eval_text(entry.get("label", "")),
            str(entry.get("reason_code") or ""),
        )
        for entry in entries
        if isinstance(entry, dict)
    }
    for candidate in candidates_review_reject:
        status = str(candidate.get("status") or "").strip().lower()
        if status not in {"review", "reject"}:
            continue
        key = (
            int(candidate.get("turn", 0) or 0),
            str(candidate.get("actor") or ""),
            str(candidate.get("source") or ""),
            str(candidate.get("entity_type") or ""),
            normalized_eval_text(candidate.get("label", "")),
            str(candidate.get("reason_code") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        entries.append(
            {
                "id": make_id("xq"),
                "turn": max(0, int(candidate.get("turn", 0) or 0)),
                "actor": str(candidate.get("actor") or "").strip(),
                "source": str(candidate.get("source") or "unknown").strip(),
                "entity_type": str(candidate.get("entity_type") or "unknown").strip(),
                "status": status,
                "reason_code": str(candidate.get("reason_code") or EXTRACTION_REASON_LOW_CONFIDENCE).strip(),
                "label": str(candidate.get("label") or "").strip(),
                "payload": deep_copy(candidate.get("payload") or {}),
                "created_at": str(candidate.get("created_at") or utc_now()),
            }
        )
    max_entries = int(quarantine.get("max_entries", EXTRACTION_QUARANTINE_DEFAULT_MAX) or EXTRACTION_QUARANTINE_DEFAULT_MAX)
    if len(entries) > max_entries:
        quarantine["entries"] = entries[-max_entries:]

def safe_candidates_to_patch(
    candidates_safe: List[Dict[str, Any]],
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    actor: str,
) -> Dict[str, Any]:
    patch = blank_patch()
    state_items = state.get("items") or {}
    for candidate in candidates_safe:
        entity_type = str(candidate.get("entity_type") or "").strip().lower()
        payload = candidate.get("payload") if isinstance(candidate.get("payload"), dict) else {}
        if entity_type == "map":
            scene_id = str(payload.get("scene_id") or "").strip()
            scene_name = str(payload.get("scene_name") or candidate.get("label") or "").strip()
            targets = [slot for slot in (payload.get("targets") or [actor]) if slot in (state.get("characters") or {})]
            if not scene_id or not scene_name or not targets:
                continue
            known_scene_ids = set((state.get("scenes") or {}).keys()) | set(((state.get("map") or {}).get("nodes") or {}).keys())
            if scene_id not in known_scene_ids and not any(str(node.get("id") or "").strip() == scene_id for node in (patch.get("map_add_nodes") or [])):
                patch["map_add_nodes"].append(
                    {
                        "id": scene_id,
                        "name": scene_name,
                        "type": "location",
                        "danger": 1,
                        "discovered": True,
                    }
                )
            for slot_name in targets:
                patch["characters"].setdefault(slot_name, {})["scene_id"] = scene_id
        elif entity_type == "item":
            item_name = str(payload.get("name") or candidate.get("label") or "").strip()
            mode = str(payload.get("mode") or "acquire").strip().lower()
            sentence = str(payload.get("sentence") or candidate.get("evidence_text") or "")
            if not item_name or actor not in (state.get("characters") or {}):
                continue
            target_patch = patch.setdefault("characters", {}).setdefault(actor, {})
            target_patch.setdefault("inventory_add", [])
            target_patch.setdefault("equipment_set", {})
            candidate_item_id = item_id_from_name(item_name)
            item_id = candidate_item_id
            suffix = 2
            while item_id in state_items or item_id in (patch.get("items_new") or {}):
                known = state_items.get(item_id) or (patch.get("items_new") or {}).get(item_id) or {}
                if normalized_eval_text(str((known or {}).get("name") or "")) == normalized_eval_text(item_name):
                    break
                item_id = f"{candidate_item_id}-{suffix}"
                suffix += 1
            item_stub = build_auto_item_stub(item_name, sentence)
            patch.setdefault("items_new", {})[item_id] = ensure_item_shape(
                item_id,
                {
                    "name": item_name[0].upper() + item_name[1:] if item_name else item_name,
                    "rarity": "common",
                    "slot": item_stub.get("slot", ""),
                    "weight": 1,
                    "stackable": False,
                    "max_stack": 1,
                    "weapon_profile": item_stub.get("weapon_profile", {}),
                    "modifiers": [],
                    "effects": [],
                    "durability": {"current": 100, "max": 100},
                    "cursed": False,
                    "curse_text": "",
                    "tags": item_stub.get("tags", ["story_auto", "auto_item"]),
                },
            )
            if item_id not in (target_patch.get("inventory_add") or []):
                target_patch["inventory_add"].append(item_id)
            if mode == "equip":
                equip_slot = item_stub.get("slot") or "weapon"
                target_patch["equipment_set"].setdefault(equip_slot, item_id)
            if not target_patch.get("equipment_set"):
                target_patch.pop("equipment_set", None)
        elif entity_type == "skill":
            if actor not in (state.get("characters") or {}):
                continue
            skill_name = str(payload.get("name") or candidate.get("label") or "").strip()
            if not skill_name:
                continue
            resource_name = resource_name_for_character(
                ((state.get("characters") or {}).get(actor) or {}),
                ((state.get("world") or {}).get("settings") or {}),
            )
            skill_id = skill_id_from_name(skill_name)
            target_patch = patch.setdefault("characters", {}).setdefault(actor, {})
            target_patch.setdefault("skills_set", {})
            target_patch["skills_set"][skill_id] = normalize_dynamic_skill_state(
                {
                    "id": skill_id,
                    "name": skill_name,
                    "rank": "F",
                    "level": 1,
                    "level_max": 10,
                    "tags": deep_copy(payload.get("tags") or ["allgemein"]),
                    "description": str(payload.get("description") or f"{skill_name} wurde im Abenteuer gelernt."),
                    "cost": {"resource": resource_name, "amount": 1} if "magie" in (payload.get("tags") or []) else None,
                    "price": None,
                    "cooldown_turns": None,
                    "unlocked_from": "Story",
                    "synergy_notes": None,
                },
                resource_name=resource_name,
            )
        elif entity_type == "class":
            class_set = normalize_class_current(payload.get("class_set"))
            if not class_set or actor not in (state.get("characters") or {}):
                continue
            patch.setdefault("characters", {}).setdefault(actor, {})["class_set"] = class_set
    return patch

def merge_safe_patch_additive(
    llm_patch: Dict[str, Any],
    safe_patch: Dict[str, Any],
    state: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    merged = normalize_patch_semantics(llm_patch)
    safe = normalize_patch_semantics(safe_patch)
    conflicts: List[Dict[str, Any]] = []

    merged_items = merged.setdefault("items_new", {})
    for item_id, item_payload in (safe.get("items_new") or {}).items():
        if item_id in merged_items:
            conflicts.append({"entity_type": "item", "label": str((item_payload or {}).get("name") or item_id), "payload": {"item_id": item_id}})
            continue
        merged_items[item_id] = deep_copy(item_payload)

    existing_node_ids = {str(node.get("id") or "").strip() for node in (merged.get("map_add_nodes") or []) if isinstance(node, dict)}
    for node in (safe.get("map_add_nodes") or []):
        node_id = str((node or {}).get("id") or "").strip()
        if not node_id or node_id in existing_node_ids:
            continue
        existing_node_ids.add(node_id)
        merged.setdefault("map_add_nodes", []).append(deep_copy(node))

    existing_edges = {
        (str(edge.get("from") or "").strip(), str(edge.get("to") or "").strip(), str(edge.get("kind") or "path").strip())
        for edge in (merged.get("map_add_edges") or [])
        if isinstance(edge, dict)
    }
    for edge in (safe.get("map_add_edges") or []):
        if not isinstance(edge, dict):
            continue
        key = (str(edge.get("from") or "").strip(), str(edge.get("to") or "").strip(), str(edge.get("kind") or "path").strip())
        if not key[0] or not key[1] or key in existing_edges:
            continue
        existing_edges.add(key)
        merged.setdefault("map_add_edges", []).append(deep_copy(edge))

    existing_events = {str(event) for event in (merged.get("events_add") or [])}
    for event in (safe.get("events_add") or []):
        text = str(event or "").strip()
        if not text or text in existing_events:
            continue
        existing_events.add(text)
        merged.setdefault("events_add", []).append(text)

    merged_characters = merged.setdefault("characters", {})
    for slot_name, safe_update in (safe.get("characters") or {}).items():
        if slot_name not in (state.get("characters") or {}):
            continue
        target = merged_characters.setdefault(slot_name, {})
        if safe_update.get("scene_id"):
            if target.get("scene_id"):
                conflicts.append(
                    {
                        "entity_type": "map",
                        "label": str(safe_update.get("scene_id") or ""),
                        "payload": {"slot": slot_name, "scene_id": safe_update.get("scene_id")},
                    }
                )
            else:
                target["scene_id"] = str(safe_update.get("scene_id") or "").strip()

        if safe_update.get("class_set"):
            if target.get("class_set") or target.get("class_update"):
                conflicts.append(
                    {
                        "entity_type": "class",
                        "label": str((safe_update.get("class_set") or {}).get("name") or ""),
                        "payload": {"slot": slot_name},
                    }
                )
            else:
                target["class_set"] = deep_copy(safe_update.get("class_set"))

        safe_skills = safe_update.get("skills_set") or {}
        if safe_skills:
            target_skills = target.setdefault("skills_set", {})
            existing_state_skill_names = {
                normalized_eval_text((entry or {}).get("name", ""))
                for entry in (((state.get("characters") or {}).get(slot_name) or {}).get("skills") or {}).values()
                if isinstance(entry, dict)
            }
            existing_target_skill_names = {
                normalized_eval_text((entry or {}).get("name", ""))
                for entry in (target_skills or {}).values()
                if isinstance(entry, dict)
            }
            for skill_id, skill_payload in safe_skills.items():
                skill_name_norm = normalized_eval_text((skill_payload or {}).get("name", ""))
                if skill_id in target_skills or (skill_name_norm and (skill_name_norm in existing_state_skill_names or skill_name_norm in existing_target_skill_names)):
                    conflicts.append(
                        {
                            "entity_type": "skill",
                            "label": str((skill_payload or {}).get("name") or skill_id),
                            "payload": {"slot": slot_name, "skill_id": skill_id},
                        }
                    )
                    continue
                target_skills[skill_id] = deep_copy(skill_payload)
                if skill_name_norm:
                    existing_target_skill_names.add(skill_name_norm)

        safe_inventory_add = safe_update.get("inventory_add") or []
        if safe_inventory_add:
            target_inventory_add = target.setdefault("inventory_add", [])
            existing_inventory_ids = {
                str(entry.get("item_id") or "").strip()
                for entry in list_inventory_items(((state.get("characters") or {}).get(slot_name) or {}))
                if str(entry.get("item_id") or "").strip()
            }
            for item_id in safe_inventory_add:
                item_key = str(item_id or "").strip()
                if not item_key:
                    continue
                if item_key in existing_inventory_ids or item_key in target_inventory_add:
                    conflicts.append({"entity_type": "item", "label": item_key, "payload": {"slot": slot_name, "item_id": item_key}})
                    continue
                target_inventory_add.append(item_key)

        safe_equipment = normalize_equipment_update_payload(safe_update.get("equipment_set") or safe_update.get("equip_set") or {})
        if safe_equipment:
            target_equipment = normalize_equipment_update_payload(target.get("equipment_set") or target.get("equip_set") or {})
            for equip_slot, equip_item_id in safe_equipment.items():
                if not equip_item_id:
                    continue
                if target_equipment.get(equip_slot):
                    conflicts.append(
                        {
                            "entity_type": "item",
                            "label": equip_item_id,
                            "payload": {"slot": slot_name, "equip_slot": equip_slot, "item_id": equip_item_id},
                        }
                    )
                    continue
                target_equipment[equip_slot] = equip_item_id
            if target_equipment:
                target["equipment_set"] = target_equipment
                target.pop("equip_set", None)
    return merged, conflicts

def call_canon_extractor(
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    actor: str,
    action_type: str,
    source_text: str,
    *,
    source: str,
) -> Dict[str, Any]:
    if not str(source_text or "").strip():
        return blank_patch()
    heuristic_candidates = build_heuristic_candidates(campaign, state, actor, action_type, source_text, source=source)
    classified_candidates = [
        classify_heuristic_candidate(candidate, campaign, state, actor, source_text)
        for candidate in heuristic_candidates
    ]
    safe_candidates, review_candidates, reject_candidates = split_candidates(classified_candidates)
    append_extraction_quarantine(state, review_candidates + reject_candidates)
    context_packet = build_extractor_context_packet(campaign, state, actor, action_type, source_text, source=source)
    user_prompt = (
        "STATE_PACKET(JSON):\n"
        + context_packet
        + "\n\nOUTPUT-KONTRAKT:\n"
        + CANON_EXTRACTOR_JSON_CONTRACT
        + "\n\nExtrahiere nur kanonische Fakten aus source_text als Patch. Keine Prosa. Keine Erklärungen."
    )
    llm_patch = blank_patch()
    try:
        payload = call_ollama_schema(
            CANON_EXTRACTOR_SYSTEM_PROMPT,
            user_prompt,
            CANON_EXTRACTOR_SCHEMA,
            timeout=120,
            temperature=0.1,
        )
        llm_patch = normalize_extractor_output_patch(payload)
    except Exception:
        llm_patch = blank_patch()
    safe_patch = safe_candidates_to_patch(safe_candidates, campaign, state, actor)
    merged_patch, merge_conflicts = merge_safe_patch_additive(llm_patch, safe_patch, state)
    if merge_conflicts:
        conflict_candidates: List[Dict[str, Any]] = []
        for conflict in merge_conflicts:
            conflict_candidates.append(
                {
                    "candidate_id": make_id("xc"),
                    "source": source,
                    "actor": actor,
                    "turn": max(0, int(((state.get("meta") or {}).get("turn", 0) or 0))),
                    "entity_type": str(conflict.get("entity_type") or "unknown"),
                    "operation": "merge_conflict",
                    "label": str(conflict.get("label") or "").strip(),
                    "normalized_key": f"conflict:{normalized_eval_text(str(conflict.get('label') or ''))}",
                    "evidence_text": str(source_text or ""),
                    "payload": deep_copy(conflict.get("payload") or {}),
                    "confidence": 0.35,
                    "status": "review",
                    "reason_code": EXTRACTION_REASON_CONFLICT_WITH_LLM,
                    "created_at": utc_now(),
                }
            )
        append_extraction_quarantine(state, conflict_candidates)
    return resolve_extractor_conflicts(campaign, state, actor, action_type, source_text, merged_patch, source=source)

def scene_name_from_state(state: Dict[str, Any], scene_id: str) -> str:
    sid = str(scene_id or "").strip()
    if not sid:
        return ""
    scenes = state.get("scenes") or {}
    if sid in scenes:
        return str((scenes.get(sid) or {}).get("name") or sid).strip()
    map_nodes = ((state.get("map") or {}).get("nodes") or {})
    if sid in map_nodes:
        return str((map_nodes.get(sid) or {}).get("name") or sid).strip()
    return sid

def existing_pc_aliases(campaign: Dict[str, Any], state: Dict[str, Any]) -> set:
    aliases = set()
    for slot_name in campaign_slots(campaign):
        aliases.add(normalize_npc_alias(slot_name))
        aliases.add(normalize_npc_alias(display_name_for_slot(campaign, slot_name)))
        character = ((state.get("characters") or {}).get(slot_name) or {})
        aliases.add(normalize_npc_alias(str((character.get("bio") or {}).get("name") or "")))
    for player in (campaign.get("players") or {}).values():
        aliases.add(normalize_npc_alias(str((player or {}).get("display_name") or "")))
    aliases.discard("")
    return aliases

def is_generic_npc_name(name: str) -> bool:
    normalized = normalize_npc_alias(name)
    if not normalized:
        return True
    tokens = [token for token in normalized.split(" ") if token]
    if not tokens:
        return True
    if len(tokens) == 1 and tokens[0] in NPC_GENERIC_NAME_TOKENS:
        return True
    if len(tokens) <= 2 and all(token in NPC_GENERIC_NAME_TOKENS for token in tokens):
        return True
    return False

def resolve_npc_scene_hint(state: Dict[str, Any], scene_hint: str) -> str:
    hint = str(scene_hint or "").strip()
    if not hint:
        return ""
    scenes = state.get("scenes") or {}
    map_nodes = ((state.get("map") or {}).get("nodes") or {})
    if hint in scenes or hint in map_nodes:
        return hint
    normalized_hint = normalized_eval_text(hint)
    for scene_id, entry in scenes.items():
        if normalized_eval_text(str((entry or {}).get("name") or scene_id)) == normalized_hint:
            return scene_id
    for scene_id, entry in map_nodes.items():
        if normalized_eval_text(str((entry or {}).get("name") or scene_id)) == normalized_hint:
            return scene_id
    return ""

def best_matching_npc_id(state: Dict[str, Any], name: str) -> str:
    alias_index = state.get("npc_alias_index") or {}
    codex = state.get("npc_codex") or {}
    alias = normalize_npc_alias(name)
    if alias and alias in alias_index and alias_index[alias] in codex:
        return alias_index[alias]
    best_ratio = 0.0
    best_id = ""
    for npc_id, entry in codex.items():
        existing_alias = normalize_npc_alias(str((entry or {}).get("name") or ""))
        if not existing_alias:
            continue
        ratio = SequenceMatcher(None, alias, existing_alias).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_id = npc_id
    if best_ratio >= 0.9:
        return best_id
    return ""

def npc_relevance_score(upsert: Dict[str, Any], source_text: str) -> int:
    explicit = upsert.get("relevance_score")
    if explicit is not None:
        return max(0, int(explicit or 0))
    score = 0
    if str(upsert.get("goal") or "").strip():
        score += 2
    if str(upsert.get("faction") or "").strip() or str(upsert.get("role_hint") or "").strip():
        score += 2
    if str(upsert.get("backstory_short") or "").strip():
        score += 1
    if int(upsert.get("level", 0) or 0) > 0:
        score += 1
    name = str(upsert.get("name") or "").strip()
    normalized_source = normalized_eval_text(source_text)
    if name and normalized_eval_text(name) in normalized_source:
        score += 1
    if name and normalized_source.count(normalized_eval_text(name)) > 1:
        score += 1
    return score

def pick_more_specific_text(current: str, incoming: str) -> str:
    cur = str(current or "").strip()
    inc = str(incoming or "").strip()
    if not inc:
        return cur
    if not cur:
        return inc
    if normalized_eval_text(cur) in {"unbekannt", "unknown", "?"}:
        return inc
    if len(inc) > len(cur) + 6:
        return inc
    return cur

def apply_npc_upserts(
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    npc_upserts: List[Dict[str, Any]],
    *,
    source_text: str,
    turn_number: int,
) -> List[str]:
    if not npc_upserts:
        return []
    state.setdefault("npc_codex", {})
    state.setdefault("npc_alias_index", {})
    codex = state["npc_codex"]
    alias_index = state["npc_alias_index"]
    pc_aliases = existing_pc_aliases(campaign, state)
    npc_resource_name = normalize_resource_name(str((((state.get("world") or {}).get("settings") or {}).get("resource_name") or "Aether")), "Aether")
    touched: List[str] = []
    for raw in npc_upserts:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "").strip()
        if not name:
            continue
        alias = normalize_npc_alias(name)
        if not alias or alias in pc_aliases or is_generic_npc_name(name):
            continue
        relevance = npc_relevance_score(raw, source_text)
        if relevance < 2:
            continue
        existing_id = best_matching_npc_id(state, name)
        npc_id = existing_id or npc_id_from_name(name)
        existing = normalize_npc_entry(codex.get(npc_id), fallback_npc_id=npc_id) if npc_id in codex else None
        entry = existing or default_npc_entry(npc_id, name)
        entry["name"] = pick_more_specific_text(entry.get("name", ""), name)
        entry["race"] = pick_more_specific_text(entry.get("race", "Unbekannt"), raw.get("race") or "")
        entry["age"] = pick_more_specific_text(entry.get("age", "Unbekannt"), raw.get("age") or "")
        entry["goal"] = pick_more_specific_text(entry.get("goal", ""), raw.get("goal") or "")
        entry["backstory_short"] = pick_more_specific_text(entry.get("backstory_short", ""), raw.get("backstory_short") or "")
        entry["role_hint"] = pick_more_specific_text(entry.get("role_hint", ""), raw.get("role_hint") or "")
        entry["faction"] = pick_more_specific_text(entry.get("faction", ""), raw.get("faction") or "")
        entry["level"] = clamp(
            max(int(entry.get("level", 1) or 1), int(raw.get("level", 0) or 0)),
            1,
            999,
        )
        entry["status"] = str(raw.get("status") or entry.get("status") or "active").strip().lower()
        if entry["status"] not in NPC_STATUS_ALLOWED:
            entry["status"] = "active"
        incoming_class = normalize_class_current(raw.get("class_current"))
        if incoming_class:
            existing_class = normalize_class_current(entry.get("class_current"))
            if not existing_class:
                entry["class_current"] = incoming_class
            else:
                merged_class = deep_copy(existing_class)
                merged_class["rank"] = (
                    incoming_class.get("rank")
                    if class_rank_sort_value(incoming_class.get("rank")) >= class_rank_sort_value(existing_class.get("rank"))
                    else existing_class.get("rank")
                )
                merged_class["level"] = max(
                    int(existing_class.get("level", 1) or 1),
                    int(incoming_class.get("level", 1) or 1),
                )
                merged_class["level_max"] = max(
                    int(existing_class.get("level_max", 10) or 10),
                    int(incoming_class.get("level_max", 10) or 10),
                )
                merged_class["xp"] = max(
                    int(existing_class.get("xp", 0) or 0),
                    int(incoming_class.get("xp", 0) or 0),
                )
                merged_class["xp_next"] = max(
                    1,
                    int(existing_class.get("xp_next", 1) or 1),
                    int(incoming_class.get("xp_next", 1) or 1),
                )
                merged_class["name"] = pick_more_specific_text(existing_class.get("name", ""), incoming_class.get("name", ""))
                merged_class["description"] = pick_more_specific_text(
                    existing_class.get("description", ""),
                    incoming_class.get("description", ""),
                )
                merged_class["affinity_tags"] = list(
                    dict.fromkeys(
                        [str(tag).strip() for tag in (existing_class.get("affinity_tags") or []) if str(tag).strip()]
                        + [str(tag).strip() for tag in (incoming_class.get("affinity_tags") or []) if str(tag).strip()]
                    )
                )
                incoming_asc = incoming_class.get("ascension") if isinstance(incoming_class.get("ascension"), dict) else {}
                existing_asc = merged_class.get("ascension") if isinstance(merged_class.get("ascension"), dict) else {}
                if incoming_asc and str(incoming_asc.get("status") or "none").strip().lower() != "none":
                    merged_class["ascension"] = deep_copy(incoming_asc)
                elif existing_asc:
                    merged_class["ascension"] = existing_asc
                entry["class_current"] = normalize_class_current(merged_class)

        incoming_skills = raw.get("skills") if isinstance(raw.get("skills"), dict) else {}
        if incoming_skills:
            existing_skill_store = normalize_skill_store(entry.get("skills") or {}, resource_name=npc_resource_name)
            for raw_skill_id, raw_skill_value in incoming_skills.items():
                incoming_skill = normalize_dynamic_skill_state(
                    raw_skill_value,
                    skill_id=str(raw_skill_id),
                    skill_name=(raw_skill_value or {}).get("name", raw_skill_id) if isinstance(raw_skill_value, dict) else str(raw_skill_id),
                    resource_name=npc_resource_name,
                    unlocked_from="NPCCodex",
                )
                existing_skill = existing_skill_store.get(incoming_skill["id"])
                existing_skill_store[incoming_skill["id"]] = (
                    merge_dynamic_skill(existing_skill, incoming_skill, resource_name=npc_resource_name)
                    if existing_skill
                    else incoming_skill
                )
            entry["skills"] = existing_skill_store
        entry["mention_count"] = int(entry.get("mention_count", 0) or 0) + 1
        entry["relevance_score"] = max(int(entry.get("relevance_score", 0) or 0), relevance)
        entry["last_seen_turn"] = max(int(entry.get("last_seen_turn", 0) or 0), int(turn_number or 0))
        if not entry.get("first_seen_turn"):
            entry["first_seen_turn"] = int(turn_number or 0)
        scene_id = resolve_npc_scene_hint(state, str(raw.get("scene_hint") or ""))
        if scene_id:
            entry["last_seen_scene_id"] = scene_id
        history_note = str(raw.get("history_note") or "").strip()
        if history_note:
            note = f"Turn {int(turn_number or 0)}: {history_note[:220]}"
            history = [str(item).strip() for item in (entry.get("history_notes") or []) if str(item).strip()]
            if not history or history[-1] != note:
                history.append(note)
            entry["history_notes"] = history[-24:]
        tags = [str(tag).strip() for tag in (entry.get("tags") or []) if str(tag).strip()]
        entry["tags"] = list(dict.fromkeys(tags + ["npc", "story_relevant"]))
        normalized_entry = normalize_npc_entry(entry, fallback_npc_id=npc_id)
        if not normalized_entry:
            continue
        codex[npc_id] = normalized_entry
        alias_index[normalize_npc_alias(normalized_entry["name"])] = npc_id
        touched.append(npc_id)
        if not existing:
            state.setdefault("events", []).append(
                f"NPC-Codex: {normalized_entry['name']} ({normalized_entry.get('race') or 'Unbekannt'}) wurde erfasst."
            )
    return list(dict.fromkeys(touched))

def contains_any_normalized_token(text: str, tokens: set) -> bool:
    normalized_text = normalize_codex_alias_text(text)
    if not normalized_text:
        return False
    for token in (tokens or set()):
        token_norm = normalize_codex_alias_text(token)
        if not token_norm:
            continue
        if re.search(rf"(?<!\w){re.escape(token_norm)}(?!\w)", normalized_text):
            return True
    return False

def collect_beast_observed_abilities(text: str, beast_profile: Dict[str, Any]) -> List[str]:
    normalized_text = normalize_codex_alias_text(text)
    observed: List[str] = []
    for ability in (beast_profile.get("known_abilities") or []):
        ability_text = str(ability or "").strip()
        if not ability_text:
            continue
        ability_norm = normalize_codex_alias_text(ability_text)
        if ability_norm and re.search(rf"(?<!\w){re.escape(ability_norm)}(?!\w)", normalized_text):
            observed.append(ability_text)
    return observed

def collect_codex_triggers(
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    *,
    actor: str,
    action_type: str,
    player_text: str,
    gm_text: str,
    patch: Dict[str, Any],
    npc_updates: List[str],
    turn_number: int,
) -> Dict[str, Any]:
    normalize_world_codex_structures(state)
    world = state.get("world") or {}
    races = world.get("races") if isinstance(world.get("races"), dict) else {}
    beasts = world.get("beast_types") if isinstance(world.get("beast_types"), dict) else {}
    race_alias_index = world.get("race_alias_index") if isinstance(world.get("race_alias_index"), dict) else {}
    beast_alias_index = world.get("beast_alias_index") if isinstance(world.get("beast_alias_index"), dict) else {}
    exact_name_index = build_world_exact_name_index(world)

    text_parts = [str(player_text or "").strip(), str(gm_text or "").strip()]
    for event in (patch.get("events_add") or []):
        if str(event or "").strip():
            text_parts.append(str(event).strip())
    combined_text = "\n".join(part for part in text_parts if part)

    race_result = resolve_codex_entity_ids(combined_text, race_alias_index, exact_name_index.get("race_names") or {})
    beast_result = resolve_codex_entity_ids(combined_text, beast_alias_index, exact_name_index.get("beast_names") or {})
    triggers_by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def merge_trigger(kind: str, entity_id: str, payload: Dict[str, Any]) -> None:
        key = (kind, entity_id)
        existing = triggers_by_key.get(key)
        if not existing:
            triggers_by_key[key] = {
                "kind": kind,
                "entity_id": entity_id,
                "knowledge_target": int(payload.get("knowledge_target", 0) or 0),
                "trigger_type": str(payload.get("trigger_type") or ""),
                "encounter_inc": int(payload.get("encounter_inc", 0) or 0),
                "known_individuals": stable_sorted_unique_strings(payload.get("known_individuals") or [], limit=32),
                "observed_abilities": stable_sorted_unique_strings(payload.get("observed_abilities") or [], limit=32),
                "defeated_inc": int(payload.get("defeated_inc", 0) or 0),
            }
            return
        existing["knowledge_target"] = max(int(existing.get("knowledge_target", 0) or 0), int(payload.get("knowledge_target", 0) or 0))
        existing["encounter_inc"] = int(existing.get("encounter_inc", 0) or 0) + int(payload.get("encounter_inc", 0) or 0)
        existing["defeated_inc"] = int(existing.get("defeated_inc", 0) or 0) + int(payload.get("defeated_inc", 0) or 0)
        existing["known_individuals"] = stable_sorted_unique_strings(
            list(existing.get("known_individuals") or []) + list(payload.get("known_individuals") or []),
            limit=32,
        )
        existing["observed_abilities"] = stable_sorted_unique_strings(
            list(existing.get("observed_abilities") or []) + list(payload.get("observed_abilities") or []),
            limit=32,
        )
        if int(payload.get("knowledge_target", 0) or 0) >= int(existing.get("knowledge_target", 0) or 0):
            existing["trigger_type"] = str(payload.get("trigger_type") or existing.get("trigger_type") or "")

    race_contact = contains_any_normalized_token(combined_text, CODEX_RACE_TRIGGER_CONTACT)
    race_lore = contains_any_normalized_token(combined_text, CODEX_RACE_TRIGGER_LORE)
    beast_combat = contains_any_normalized_token(combined_text, CODEX_BEAST_TRIGGER_COMBAT)
    beast_defeat = contains_any_normalized_token(combined_text, CODEX_BEAST_TRIGGER_DEFEAT)
    beast_ability = contains_any_normalized_token(combined_text, CODEX_BEAST_TRIGGER_ABILITY)

    for race_id in (race_result.get("matched") or []):
        knowledge_target = 1
        trigger_type = "race_first_contact"
        if race_contact:
            knowledge_target = max(knowledge_target, 2)
            trigger_type = "race_first_contact"
        if race_lore:
            knowledge_target = max(knowledge_target, 3)
            trigger_type = "race_lore_discovered"
        merge_trigger(
            CODEX_KIND_RACE,
            race_id,
            {
                "knowledge_target": knowledge_target,
                "trigger_type": trigger_type,
                "encounter_inc": 1,
            },
        )

    for beast_id in (beast_result.get("matched") or []):
        beast_profile = (beasts.get(beast_id) or {}) if isinstance(beasts, dict) else {}
        knowledge_target = 1
        trigger_type = "beast_first_sighting"
        defeated_inc = 0
        if beast_combat:
            knowledge_target = max(knowledge_target, 2)
            trigger_type = "beast_first_sighting"
        if beast_ability:
            knowledge_target = max(knowledge_target, 3)
            trigger_type = "beast_ability_observed"
        if beast_defeat:
            knowledge_target = max(knowledge_target, 3)
            trigger_type = "beast_defeated"
            defeated_inc = 1
        if contains_any_normalized_token(combined_text, CODEX_RACE_TRIGGER_LORE):
            knowledge_target = max(knowledge_target, 4)
            trigger_type = "codex_research_unlock"
        merge_trigger(
            CODEX_KIND_BEAST,
            beast_id,
            {
                "knowledge_target": knowledge_target,
                "trigger_type": trigger_type,
                "encounter_inc": 1,
                "defeated_inc": defeated_inc,
                "observed_abilities": collect_beast_observed_abilities(combined_text, beast_profile),
            },
        )

    npc_codex = state.get("npc_codex") if isinstance(state.get("npc_codex"), dict) else {}
    for npc_id in (npc_updates or []):
        npc = npc_codex.get(npc_id) if isinstance(npc_codex, dict) else None
        if not isinstance(npc, dict):
            continue
        race_name = str(npc.get("race") or "").strip()
        npc_name = str(npc.get("name") or "").strip()
        if not race_name:
            continue
        npc_race_result = resolve_codex_entity_ids(race_name, race_alias_index, exact_name_index.get("race_names") or {})
        for race_id in (npc_race_result.get("matched") or []):
            merge_trigger(
                CODEX_KIND_RACE,
                race_id,
                {
                    "knowledge_target": 2,
                    "trigger_type": "race_first_contact",
                    "encounter_inc": 1,
                    "known_individuals": [npc_name] if npc_name else [],
                },
            )

    return {
        "triggers": list(triggers_by_key.values()),
        "ambiguous": {
            "races": deep_copy(race_result.get("ambiguous") or []),
            "beasts": deep_copy(beast_result.get("ambiguous") or []),
        },
        "source_turn": int(turn_number or 0),
        "actor": actor,
        "action_type": action_type,
    }

def apply_codex_triggers(state: Dict[str, Any], trigger_bundle: Dict[str, Any], *, turn_number: int) -> List[Dict[str, Any]]:
    normalize_world_codex_structures(state)
    world = state.get("world") or {}
    races = world.get("races") if isinstance(world.get("races"), dict) else {}
    beasts = world.get("beast_types") if isinstance(world.get("beast_types"), dict) else {}
    codex = state.setdefault("codex", {})
    codex_races = codex.setdefault("races", {})
    codex_beasts = codex.setdefault("beasts", {})
    updates: List[Dict[str, Any]] = []

    for trigger in (trigger_bundle.get("triggers") or []):
        kind = str(trigger.get("kind") or "").strip().lower()
        entity_id = str(trigger.get("entity_id") or "").strip()
        if not entity_id:
            continue
        if kind == CODEX_KIND_RACE and entity_id not in races:
            continue
        if kind == CODEX_KIND_BEAST and entity_id not in beasts:
            continue
        profile = races.get(entity_id) if kind == CODEX_KIND_RACE else beasts.get(entity_id)
        if not isinstance(profile, dict):
            continue
        target_map = codex_races if kind == CODEX_KIND_RACE else codex_beasts
        entry_before = normalize_codex_entry_stable(target_map.get(entity_id), kind=kind)
        entry_after = deep_copy(entry_before)
        entry_after["encounter_count"] = int(entry_after.get("encounter_count", 0) or 0) + max(0, int(trigger.get("encounter_inc", 0) or 0))
        entry_after["knowledge_level"] = clamp(
            max(int(entry_after.get("knowledge_level", 0) or 0), int(trigger.get("knowledge_target", 0) or 0)),
            CODEX_KNOWLEDGE_LEVEL_MIN,
            CODEX_KNOWLEDGE_LEVEL_MAX,
        )
        if int(entry_after.get("knowledge_level", 0) or 0) > 0:
            entry_after["discovered"] = True
            if not int(entry_after.get("first_seen_turn", 0) or 0):
                entry_after["first_seen_turn"] = max(0, int(turn_number or 0))
        entry_after["last_updated_turn"] = max(int(entry_after.get("last_updated_turn", 0) or 0), max(0, int(turn_number or 0)))
        derived_blocks = codex_blocks_for_level(kind, int(entry_after.get("knowledge_level", 0) or 0))
        entry_after["known_blocks"] = [block for block in codex_block_order(kind) if block in set((entry_after.get("known_blocks") or []) + derived_blocks)]
        profile_facts = codex_facts_for_blocks(kind, profile, entry_after.get("known_blocks") or [])
        entry_after["known_facts"] = merge_known_facts_stable(entry_after.get("known_facts") or [], profile_facts)

        if kind == CODEX_KIND_RACE:
            entry_after["known_individuals"] = stable_sorted_unique_strings(
                list(entry_after.get("known_individuals") or []) + list(trigger.get("known_individuals") or []),
                limit=64,
            )
        else:
            entry_after["defeated_count"] = int(entry_after.get("defeated_count", 0) or 0) + max(0, int(trigger.get("defeated_inc", 0) or 0))
            entry_after["observed_abilities"] = stable_sorted_unique_strings(
                list(entry_after.get("observed_abilities") or []) + list(trigger.get("observed_abilities") or []),
                limit=64,
            )

        normalized_after = normalize_codex_entry_stable(entry_after, kind=kind)
        target_map[entity_id] = normalized_after
        if normalized_after != entry_before:
            updates.append(
                {
                    "kind": kind,
                    "entity_id": entity_id,
                    "name": str(profile.get("name") or entity_id),
                    "trigger_type": str(trigger.get("trigger_type") or ""),
                    "knowledge_before": int(entry_before.get("knowledge_level", 0) or 0),
                    "knowledge_after": int(normalized_after.get("knowledge_level", 0) or 0),
                    "new_blocks": [
                        block
                        for block in (normalized_after.get("known_blocks") or [])
                        if block not in (entry_before.get("known_blocks") or [])
                    ],
                }
            )

    for ambiguous_kind, rows in ((trigger_bundle.get("ambiguous") or {}).items()):
        for row in (rows or []):
            alias = str((row or {}).get("alias") or "").strip()
            entity_ids = [str(entry).strip() for entry in ((row or {}).get("entity_ids") or []) if str(entry).strip()]
            if not alias or len(entity_ids) < 2:
                continue
            updates.append(
                {
                    "kind": "ambiguous",
                    "entity_kind": ambiguous_kind[:-1] if ambiguous_kind.endswith("s") else ambiguous_kind,
                    "alias": alias,
                    "entity_ids": entity_ids,
                }
            )

    normalize_world_codex_structures(state)
    return updates

def build_npc_extractor_context_packet(
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    actor: str,
    action_type: str,
    player_text: str,
    gm_text: str,
) -> str:
    payload = {
        "actor": actor,
        "actor_display": display_name_for_slot(campaign, actor) if is_slot_id(actor) else actor,
        "action_type": action_type,
        "active_party": [
            {"slot_id": slot_name, "display_name": display_name_for_slot(campaign, slot_name)}
            for slot_name in active_party(campaign)
        ],
        "known_npcs": build_npc_codex_summary(state, limit=28),
        "known_scenes": {
            scene_id: scene.get("name", scene_id)
            for scene_id, scene in (state.get("scenes") or {}).items()
        },
        "player_text": str(player_text or ""),
        "gm_text": str(gm_text or ""),
    }
    return json.dumps(payload, ensure_ascii=False)

def call_npc_extractor(
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    actor: str,
    action_type: str,
    player_text: str,
    gm_text: str,
) -> List[Dict[str, Any]]:
    if not str(player_text or "").strip() and not str(gm_text or "").strip():
        return []
    context_packet = build_npc_extractor_context_packet(campaign, state, actor, action_type, player_text, gm_text)
    user_prompt = (
        "STATE_PACKET(JSON):\n"
        + context_packet
        + "\n\nOUTPUT-KONTRAKT:\n"
        + NPC_EXTRACTOR_JSON_CONTRACT
    )
    try:
        payload = call_ollama_schema(
            NPC_EXTRACTOR_SYSTEM_PROMPT,
            user_prompt,
            NPC_EXTRACTOR_SCHEMA,
            timeout=120,
            temperature=0.15,
        )
        raw_entries = payload.get("npc_upserts") if isinstance(payload, dict) else []
        if not isinstance(raw_entries, list):
            return []
        return [entry for entry in raw_entries if isinstance(entry, dict)]
    except Exception:
        return []

def normalize_request_option_text(option: Any) -> str:
    if isinstance(option, dict):
        for key in ("text", "label", "value", "name", "title"):
            value = option.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return ""
    if option is None:
        return ""
    if isinstance(option, (list, tuple, set)):
        return ""
    return str(option).strip()

def normalize_request_entry(entry: Any, *, default_actor: str = "") -> Optional[Dict[str, Any]]:
    if not isinstance(entry, dict):
        return None
    request_type = str(entry.get("type") or "").strip().lower()
    question = str(entry.get("question") or entry.get("prompt") or "").strip()
    raw_options = entry.get("options")
    if raw_options is None:
        raw_options = entry.get("choices")
    if isinstance(raw_options, dict):
        raw_options = list(raw_options.values())
    elif raw_options is None:
        raw_options = []
    elif not isinstance(raw_options, list):
        raw_options = [raw_options]
    options: List[str] = []
    seen = set()
    for raw_option in raw_options:
        option_text = normalize_request_option_text(raw_option)
        normalized_option = normalized_eval_text(option_text)
        if not option_text or normalized_option in seen:
            continue
        seen.add(normalized_option)
        options.append(option_text)
    if request_type not in {"clarify", "choice", "none"}:
        if options:
            request_type = "choice"
        elif question:
            request_type = "clarify"
        else:
            request_type = "none"
    if request_type == "choice" and not options:
        request_type = "clarify" if question else "none"
    actor = str(entry.get("actor") or default_actor or "").strip()
    normalized_entry: Dict[str, Any] = {"type": request_type, "actor": actor}
    if request_type in {"clarify", "choice"} and question:
        normalized_entry["question"] = question
    if request_type == "choice" and options:
        normalized_entry["options"] = options
    return normalized_entry

def normalize_requests_payload(payload: Any, *, default_actor: str = "") -> List[Dict[str, Any]]:
    if payload is None:
        raw_entries: List[Any] = []
    elif isinstance(payload, dict):
        raw_entries = [payload]
    elif isinstance(payload, list):
        raw_entries = payload
    else:
        raw_entries = []
    normalized_entries: List[Dict[str, Any]] = []
    for raw_entry in raw_entries:
        normalized_entry = normalize_request_entry(raw_entry, default_actor=default_actor)
        if normalized_entry:
            normalized_entries.append(normalized_entry)
    return normalized_entries

def normalize_model_output_payload(payload: Any, *, default_actor: str = "") -> Dict[str, Any]:
    candidate = payload
    if isinstance(candidate, dict):
        for wrapper_key in ("response", "result", "output", "content", "data"):
            wrapped = candidate.get(wrapper_key)
            if isinstance(wrapped, dict) and (
                "story" in wrapped
                or "patch" in wrapped
                or "requests" in wrapped
                or "gm_text" in wrapped
                or "text" in wrapped
            ):
                candidate = wrapped
                break
    if not isinstance(candidate, dict):
        return {}

    story = candidate.get("story")
    if not isinstance(story, str) or not story.strip():
        for fallback_key in ("gm_text", "text", "narration", "message"):
            fallback_story = candidate.get(fallback_key)
            if isinstance(fallback_story, str) and fallback_story.strip():
                story = fallback_story
                break

    patch = normalize_patch_payload(candidate.get("patch"))

    normalized = {
        "story": str(story or "").strip(),
        "patch": patch,
        "requests": normalize_requests_payload(candidate.get("requests"), default_actor=default_actor),
    }
    return normalized if normalized["story"] else {}

def call_ollama_chat(
    system: str,
    user: str,
    *,
    format_schema: Optional[Dict[str, Any]] = None,
    timeout: Optional[int] = None,
    temperature: Optional[float] = None,
    repeat_penalty: Optional[float] = None,
) -> str:
    request_timeout = max(30, int(timeout or OLLAMA_TIMEOUT_SEC))
    options = {
        "temperature": OLLAMA_TEMPERATURE if temperature is None else temperature,
        "num_ctx": OLLAMA_NUM_CTX,
        "repeat_penalty": OLLAMA_REPEAT_PENALTY if repeat_penalty is None else repeat_penalty,
        "repeat_last_n": OLLAMA_REPEAT_LAST_N,
    }
    seed = ollama_request_seed()
    if seed is not None:
        options["seed"] = seed
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": options,
    }
    if format_schema is not None:
        payload["format"] = format_schema
    response = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=request_timeout)
    if response.status_code != 200:
        message = f"Ollama error {response.status_code}: {response.text[:500]}"
        if format_schema is not None and ollama_format_fallback_needed(message):
            fallback_user = (
                user
                + "\n\nWICHTIGER FALLBACK-HINWEIS:\n"
                + "Das Modell konnte das Schema-Format nicht verwenden. "
                + schema_fallback_instruction(format_schema)
            )
            return call_ollama_chat(
                system,
                fallback_user,
                format_schema=None,
                timeout=request_timeout,
                temperature=temperature,
                repeat_penalty=repeat_penalty,
            )
        raise RuntimeError(message)
    return (response.json().get("message", {}) or {}).get("content", "").strip()

def call_ollama_json(
    system: str,
    user: str,
    *,
    temperature: Optional[float] = None,
    repeat_penalty: Optional[float] = None,
    trace_ctx: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    content = call_ollama_chat(
        system,
        user,
        format_schema=RESPONSE_SCHEMA,
        timeout=max(180, OLLAMA_TIMEOUT_SEC),
        temperature=OLLAMA_TEMPERATURE if temperature is None else temperature,
        repeat_penalty=repeat_penalty,
    )
    try:
        parsed = extract_json_payload(content)
        emit_turn_phase_event(
            trace_ctx,
            phase="narrator_json_parse_repair",
            success=True,
            extra={"mode": "parse_ok"},
        )
        return parsed
    except RuntimeError as exc:
        if "Model returned non-JSON content" not in str(exc):
            raise
        emit_turn_phase_event(
            trace_ctx,
            phase="narrator_json_parse_repair",
            success=False,
            error_code=ERROR_CODE_JSON_REPAIR,
            error_class=exc.__class__.__name__,
            message=str(exc)[:240],
            extra={"mode": "parse_failed_repair_attempt"},
        )
        try:
            repaired = repair_json_payload_with_model(system, content, schema=RESPONSE_SCHEMA)
        except Exception as repair_exc:
            emit_turn_phase_event(
                trace_ctx,
                phase="narrator_json_parse_repair",
                success=False,
                error_code=ERROR_CODE_JSON_REPAIR,
                error_class=repair_exc.__class__.__name__,
                message=str(repair_exc)[:240],
                extra={"mode": "repair_failed"},
            )
            if trace_ctx is not None:
                raise turn_flow_error(
                    error_code=ERROR_CODE_JSON_REPAIR,
                    phase="narrator_json_parse_repair",
                    trace_ctx=trace_ctx,
                    exc=repair_exc,
                )
            raise
        emit_turn_phase_event(
            trace_ctx,
            phase="narrator_json_parse_repair",
            success=True,
            extra={"mode": "repair_ok"},
        )
        return repaired

def call_ollama_schema(system: str, user: str, schema: Dict[str, Any], *, timeout: Optional[int] = None, temperature: float = 0.45) -> Dict[str, Any]:
    schema_timeout = max(90, int(timeout or OLLAMA_TIMEOUT_SEC))
    content = call_ollama_chat(system, user, format_schema=schema, timeout=schema_timeout, temperature=temperature)
    try:
        return extract_json_payload(content)
    except RuntimeError as exc:
        if "Model returned non-JSON content" not in str(exc):
            raise
        return repair_json_payload_with_model(system, content, schema=schema, timeout=min(schema_timeout, 120))

def clean_setup_ai_copy(text: str) -> str:
    return str(text or "").strip().strip('"').strip("'").strip()

def is_bad_setup_ai_copy(text: str) -> bool:
    lowered = clean_setup_ai_copy(text).lower()
    if not lowered:
        return True
    meta_markers = (
        "frage-id:",
        "typ:",
        "setup-stufe:",
        "aktuelles weltprofil:",
        "es geht um den slot",
        '"premise":',
        '"tone":',
        '"difficulty":',
        '"player_count":',
        "{",
        "}",
    )
    if any(marker in lowered for marker in meta_markers):
        return True
    if len(lowered) > 260:
        return True
    return False

def generate_setup_ai_copy(
    campaign: Dict[str, Any],
    question: Dict[str, Any],
    *,
    setup_type: str,
    slot_name: Optional[str] = None,
) -> str:
    prompt = question.get("prompt_template") or question["label"]
    summary = campaign.get("setup", {}).get("world", {}).get("summary", {})
    role_text = (
        f"Es geht um den Slot {slot_name} ({display_name_for_slot(campaign, slot_name)})"
        if slot_name
        else "Es geht um das Welt-Setup"
    )
    user = (
        f"Frage-ID: {question['id']}\n"
        f"Typ: {question['type']}\n"
        f"Setup-Stufe: {setup_type}\n"
        f"{role_text}\n"
        f"Aktuelles Weltprofil: {json.dumps(summary, ensure_ascii=False)}\n"
        f"Basistext: {prompt}"
    )
    try:
        text = call_ollama_text(SETUP_QUESTION_SYSTEM_PROMPT, user)
        text = clean_setup_ai_copy(text)
        return prompt if is_bad_setup_ai_copy(text) or looks_non_german_text(text, allow_short=True) else text
    except Exception:
        return prompt

def get_persisted_question_ai_copy(setup_node: Dict[str, Any], question_id: str) -> str:
    runtime = (setup_node.get("question_runtime") or {}).get(question_id) or {}
    return clean_setup_ai_copy(runtime.get("ai_copy", ""))

def store_question_ai_copy(setup_node: Dict[str, Any], question_id: str, ai_copy: str, source: str) -> str:
    runtime = setup_node.setdefault("question_runtime", {})
    cleaned = clean_setup_ai_copy(ai_copy)
    runtime[question_id] = {
        "ai_copy": cleaned,
        "generated_at": utc_now(),
        "source": source,
    }
    return cleaned

def ensure_question_ai_copy(
    campaign: Dict[str, Any],
    *,
    setup_type: str,
    question_id: str,
    slot_name: Optional[str] = None,
) -> str:
    question_map = WORLD_QUESTION_MAP if setup_type == "world" else CHARACTER_QUESTION_MAP
    question = question_map.get(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Unbekannte Setup-Frage.")
    if setup_type == "world":
        setup_node = campaign["setup"]["world"]
    else:
        setup_node = campaign["setup"]["characters"].get(slot_name or "")
        if not setup_node:
            raise HTTPException(status_code=404, detail="Unbekannter Setup-Slot.")
    existing = get_persisted_question_ai_copy(setup_node, question_id)
    if existing:
        return existing
    generated = generate_setup_ai_copy(campaign, question, setup_type=setup_type, slot_name=slot_name)
    source = "fallback" if clean_setup_ai_copy(generated) == clean_setup_ai_copy(question.get("prompt_template") or question["label"]) else "ai"
    return store_question_ai_copy(setup_node, question_id, generated or question["label"], source)

def build_setup_option_context(
    campaign: Dict[str, Any],
    *,
    setup_type: str,
    slot_name: Optional[str] = None,
    setup_node: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    world_answers = (((campaign.get("setup") or {}).get("world") or {}).get("answers") or {})
    world_summary = (((campaign.get("setup") or {}).get("world") or {}).get("summary") or {})
    character_node = (((campaign.get("setup") or {}).get("characters") or {}).get(slot_name or "")) or {}
    character_answers = (setup_node or character_node).get("answers", {}) or {}
    character_summary = (character_node.get("summary") or {})
    return {
        "setup_type": setup_type,
        "slot_name": slot_name or "",
        "slot_display_name": display_name_for_slot(campaign, slot_name) if slot_name else "",
        "theme": extract_text_answer(world_answers.get("theme")) or str(world_summary.get("theme", "") or ""),
        "campaign_length": normalize_campaign_length_choice(
            extract_text_answer(world_answers.get("campaign_length")) or str(world_summary.get("campaign_length", "") or "")
        ),
        "tone": extract_text_answer(world_answers.get("tone")) or str(world_summary.get("tone", "") or ""),
        "difficulty": extract_text_answer(world_answers.get("difficulty")) or str(world_summary.get("difficulty", "") or ""),
        "world_structure": extract_text_answer(world_answers.get("world_structure")) or str(world_summary.get("world_structure", "") or ""),
        "resource_scarcity": extract_text_answer(world_answers.get("resource_scarcity")) or str(world_summary.get("resource_scarcity", "") or ""),
        "resource_name": extract_text_answer(world_answers.get("resource_name")) or str(world_summary.get("resource_name", "") or ""),
        "monsters_density": extract_text_answer(world_answers.get("monsters_density")) or str(world_summary.get("monsters_density", "") or ""),
        "healing_frequency": extract_text_answer(world_answers.get("healing_frequency")) or str(world_summary.get("healing_frequency", "") or ""),
        "ruleset": normalize_ruleset_choice(extract_text_answer(world_answers.get("ruleset")) or str(world_summary.get("ruleset", "") or "")),
        "attribute_range": str(world_summary.get("attribute_range_label", "") or extract_text_answer(world_answers.get("attribute_range"))),
        "char_gender": extract_text_answer(character_answers.get("char_gender")) or str(character_summary.get("gender", "") or ""),
        "char_age": extract_text_answer(character_answers.get("char_age")) or str(character_summary.get("age_stage", "") or ""),
        "strength": extract_text_answer(character_answers.get("strength")) or str(character_summary.get("strength", "") or ""),
        "weakness": extract_text_answer(character_answers.get("weakness")) or str(character_summary.get("weakness", "") or ""),
        "class_start_mode": extract_text_answer(character_answers.get("class_start_mode")) or str(character_summary.get("class_start_mode", "") or ""),
        "current_focus": extract_text_answer(character_answers.get("current_focus")) or str(character_summary.get("current_focus", "") or character_summary.get("focus", "") or ""),
        "personality_tags": extract_text_answer(character_answers.get("personality_tags")) or ", ".join(character_summary.get("personality_tags", []) or character_summary.get("personality", []) or []),
    }

def append_context_hint(base: str, hint: str) -> str:
    base = str(base or "").strip()
    hint = str(hint or "").strip()
    if not hint:
        return base
    if not base:
        return hint
    return f"{base} {hint}"

def dynamic_option_description(question_id: str, option: str, context: Dict[str, str]) -> str:
    theme = context.get("theme", "")
    tone = context.get("tone", "")
    world_structure = context.get("world_structure", "")
    difficulty = context.get("difficulty", "")
    monsters_density = context.get("monsters_density", "")
    resource_scarcity = context.get("resource_scarcity", "")
    resource_name = context.get("resource_name", "")
    ruleset = context.get("ruleset", "")
    strength = context.get("strength", "")
    weakness = context.get("weakness", "")
    focus = context.get("current_focus", "")

    if question_id == "theme":
        descriptions = {
            "Dark Isekai (Survival/Horror)": "Zieht den Run in Richtung knapper Flucht, unklarer Gefahr und existenzieller Unsicherheit.",
            "Grimdark Fantasy (Krieg/Fraktionen)": "Stellt Machtblöcke, Verrat und ein zermürbendes großes Konfliktfeld in den Vordergrund.",
            "Monster-Hunt (Jagd/Beute/Upgrade)": "Fokussiert Beutezüge, gefährliche Fährten und spürbaren Fortschritt über besiegte Bedrohungen.",
            "Mystery/Occult (Geheimnisse/Kulte)": "Legt den Schwerpunkt auf verborgene Wahrheiten, Rituale, Kulte und langsames Entschlüsseln.",
            "Dungeon-Crawl (Fallen/Loot/Progress)": "Bringt enge Räume, riskante Vorstöße, Fallen und klaren Vorwärtsdruck in die Szenen.",
            "Sandbox (freie Erkundung)": "Öffnet die Welt stärker, damit Entdeckung, Umwege und selbstgewählte Prioritäten tragen.",
        }
        return append_context_hint(descriptions.get(option, ""), f"Der aktuelle Ton {tone} färbt diese Richtung zusätzlich ein." if tone else "")
    if question_id == "player_count":
        try:
            count = int(option)
        except ValueError:
            count = 1
        if count == 1:
            return "Hält alles eng, persönlich und stark auf eine einzelne Hauptfigur konzentriert."
        if count <= 3:
            return "Gibt jeder Figur klaren Raum und hält die Gruppe trotzdem beweglich."
        return "Erzeugt mehr Gruppendynamik, Reibung und mehrere gleichzeitige Blickwinkel."
    if question_id == "campaign_length":
        descriptions = {
            "Kurz": "Zielt auf einen kompakten Run mit schnellerem Plot-Fortschritt und klaren Meilensteinen (~120 Turns).",
            "Mittel": "Balanciert Fortschritt und Details für längere Kampagnenphasen (~720 Turns).",
            "Unbestimmt": "Kein fixes Endziel; die Kampagne kann offen weiterlaufen, solange der Tisch es will.",
        }
        return descriptions.get(option, "")
    if question_id == "tone":
        descriptions = {
            "Düster-realistisch": "Erdet jede Szene und lässt Gewalt, Hunger und Verlust schwer und glaubwürdig wirken.",
            "Anime-dark (stilisiert, brutal wenn nötig)": "Erlaubt größere Bilder, klare Archetypen und dennoch harte Spitzen im richtigen Moment.",
            "Brutal/gnadenlos": "Macht die Welt härter, direkter und weniger verzeihend in ihren Konsequenzen.",
            "Melancholisch/hoffnungslos": "Schiebt Trauer, Verfall und ein langsames Gefühl des Untergehens in den Vordergrund.",
            "Zynisch/dreckig": "Betont Niedertracht, schmutzige Deals und Figuren, die eher überleben als glänzen wollen.",
            "Mystisch/bedrohlich": "Lässt vieles größer, älter und unheilvoller wirken, auch wenn die Gefahr noch unsichtbar ist.",
        }
        return append_context_hint(descriptions.get(option, ""), f"Passt stark zu {theme}." if theme else "")
    if question_id == "difficulty":
        descriptions = {
            "Gritty": "Fehler tun weh, aber die Welt lässt noch Luft für knappe Erholung und kluge Auswege.",
            "Brutal": "Konsequenzen sitzen tiefer, Ressourcen kippen schneller und falsche Risiken rächen sich spürbar.",
            "Hardcore": "Die Welt gönnt kaum Puffer; selbst gute Pläne müssen mit maximalem Druck gerechnet werden.",
        }
        return append_context_hint(descriptions.get(option, ""), f"Mit Ton {tone} wirkt das noch kompromissloser." if tone else "")
    if question_id == "monsters_density":
        descriptions = {
            "Selten": "Monstern begegnet man weniger oft, dafür wirken einzelne Auftritte größer und markanter.",
            "Regelmäßig": "Hält stetigen Druck in der Welt, ohne jede Szene automatisch in Kampf zu kippen.",
            "Überall": "Macht Bewegung selbst zum Risiko und drückt den Run stark in Richtung permanenter Bedrohung.",
            "Situativ (nur in bestimmten Zonen)": "Erlaubt ruhige Zwischenräume und klar abgegrenzte Höllenzonen mit eigenem Profil.",
        }
        return append_context_hint(descriptions.get(option, ""), f"Das kontrastiert gerade mit der Knappheit {resource_scarcity}." if resource_scarcity else "")
    if question_id == "resource_scarcity":
        descriptions = {
            "Niedrig": "Lässt den Run freier atmen und verschiebt den Druck eher auf Konflikte als auf Versorgung.",
            "Mittel": "Hält Versorgung relevant, ohne jede Entscheidung sofort in blanken Mangel zu verwandeln.",
            "Hoch": "Macht Vorräte, Licht, Wasser und Werkzeug schnell zu eigenen Story-Treibern.",
            "Extrem": "Schon der nächste Tag wird zur Frage von Kälte, Hunger, Improvisation und bitteren Prioritäten.",
        }
        return append_context_hint(descriptions.get(option, ""), f"Monsterdichte: {monsters_density}." if monsters_density else "")
    if question_id == "resource_name":
        descriptions = {
            "Aether": "Wirkt archaisch-mystisch und passt gut zu Relikten, Siegeln und uralten Strukturen.",
            "Mana": "Klingt klassisch-fantastisch und hält Magie als gut lesbaren Kernbegriff.",
            "Ki": "Schiebt Fokus auf Körperdisziplin, innere Strömung und kontrollierte Technik.",
            "Chakra": "Betont spirituelle Zentren, innere Balance und kultische Systeme.",
            "Prana": "Färbt die Welt stärker lebensenergetisch und naturverbunden.",
            "Flux": "Wirkt technomagisch, instabil und experimentell.",
            "Essenz": "Fühlt sich roh, alchemistisch und existenziell an.",
        }
        return append_context_hint(descriptions.get(option, ""), f"Aktuell gesetzt: {resource_name}." if resource_name else "")
    if question_id == "healing_frequency":
        descriptions = {
            "Selten": "Verletzungen bleiben länger relevant und schreiben sich tiefer in den Szenenverlauf ein.",
            "Normal": "Hält Schaden spürbar, ohne den Run in Dauerlähmung zu drücken.",
            "Häufig": "Erlaubt aggressiveres Spiel, weil Rückschläge eher abgefangen werden können.",
        }
        return append_context_hint(descriptions.get(option, ""), f"In Kombination mit {difficulty} bleibt das gut lesbar." if difficulty else "")
    if question_id == "ruleset":
        descriptions = {
            "Konsequent": "Lässt Entscheidungen direkt und klar zurückschlagen, ohne Ausweichen über Zufall oder Gnade.",
            "Dramatisch": "Gewichtet emotionale Wendungen und bittere Kosten stärker als nüchterne Härte.",
            "Erbarmungslos": "Spielt jede falsche Entscheidung brutal aus und hält den Druck permanent hoch.",
        }
        return append_context_hint(descriptions.get(option, ""), f"Gerade bei Wertebereich {context.get('attribute_range', '')} wirkt das besonders klar." if context.get("attribute_range") else "")
    if question_id == "attribute_range":
        descriptions = {
            "1-10": "Bleibt kompakt und schnell lesbar; kleine Unterschiede wirken sofort bedeutsam.",
            "1-20": "Gibt etwas feinere Abstufungen, ohne das Blatt mit Zahlen zu überfrachten.",
            "1-100": "Erlaubt sehr feine Skalen, große Schwankungen und detailreiche Progression.",
        }
        return append_context_hint(descriptions.get(option, ""), f"Mit {ruleset} bleibt die Skala gut greifbar." if ruleset else "")
    if question_id == "outcome_model":
        descriptions = {
            "Erfolg / Misserfolg": "Hält Szenen direkter und klarer, mit harten Kanten zwischen gelungen und misslungen.",
            "Erfolg / Teilerfolg / Misserfolg-mit-Preis": "Gibt dem GM mehr graue Zwischenräume, Kosten und bittere Kompromisse.",
            "Cinematic (weniger Würfe, harte Konsequenzen)": "Setzt auf weniger Unterbrechung und größere Wendepunkte pro Entscheidung.",
        }
        return append_context_hint(descriptions.get(option, ""), f"Passt gut zu {tone}." if tone else "")
    if question_id == "world_structure":
        descriptions = {
            "Hub + Dungeons": "Schafft einen wiederkehrenden sicheren Kern und klare Ausbrüche in gefährliche Zonen.",
            "Zonen/Regionen (mit Grenzen/Fog of War)": "Betont Fortschritt über erkundete Grenzen und Stück-für-Stück-Enthüllung.",
            "Offene Welt (Sandbox)": "Lässt die Gruppe stärker selbst treiben, umleiten und Prioritäten setzen.",
            "Reise-Kampagne (Road-Movie)": "Schiebt Bewegung, Weggefährten, Durchgangsorte und stetigen Ortswechsel nach vorn.",
            "Stadtzentriert (Intrigen/Fraktionen)": "Verdichtet Drama auf Beziehungen, Fraktionen, Deals und Machtspiele an einem Knotenpunkt.",
        }
        return append_context_hint(descriptions.get(option, ""), f"Der bisherige Ton {tone} bekommt darin einen klaren Raum." if tone else "")
    if question_id == "world_laws":
        hint = "Verankert ein dauerhaftes Weltgesetz, das Entscheidungen und Risiken fortlaufend färbt."
        if theme:
            hint = append_context_hint(hint, f"Gerade im Rahmen von {theme} kann das starke Kontraste erzeugen.")
        return hint
    if question_id == "char_gender":
        return append_context_hint("Legt die Identität der Figur fest, ohne ihre Spielstärke oder Klasse vorzugeben.", f"Die Welt {theme} reagiert dann auf genau diese Figur." if theme else "")
    if question_id == "char_age":
        descriptions = {
            "Teen (16-19)": "Bringt frühe Härte, Unfertigkeit und oft mehr rohen Trotz in den Run.",
            "Jung (20-25)": "Fühlt sich beweglich, suchend und offen für schnelle Richtungswechsel an.",
            "Erwachsen (26-35)": "Gibt der Figur greifbare Reife, Entscheidungen mit Gewicht und klare Altlasten.",
            "Älter (36+)": "Stärkt Lebenserfahrung, Müdigkeit, Narben und eine andere Art von Autorität.",
        }
        return append_context_hint(descriptions.get(option, ""), f"Passt gut zu Fokus {focus}." if focus else "")
    if question_id == "personality_tags":
        return append_context_hint("Setzt eine spürbare Charakterkante, die in Dialogen, Risiken und Gruppenspannung sichtbar werden kann.", f"Besonders interessant neben {weakness}." if weakness else "")
    if question_id == "strength":
        return append_context_hint("Macht klar, worin die Figur unter Druck verlässlich glänzen darf.", f"In dieser Welt mit {theme} kann das besonders tragen." if theme else "")
    if question_id == "weakness":
        return append_context_hint("Gibt der Welt einen echten Hebel, um Druck auf die Figur auszuüben.", f"Das reibt sich spannend mit Stärke {strength}." if strength else "")
    if question_id == "current_focus":
        return append_context_hint("Bestimmt, worauf die Figur in den ersten Szenen instinktiv zusteuert.", f"Zusammen mit Stärke {strength} entsteht sofort eine klare Dynamik." if strength else "")
    if question_id == "class_start_mode":
        return "Legt fest, ob die Klasse sofort entsteht, von dir direkt definiert wird oder sich erst in der Story bildet."
    if question_id == "isekai_price":
        return append_context_hint("Sorgt dafür, dass die Ankunft sofort eine greifbare Narbe oder Last hinterlässt.", f"Bei Schwäche {weakness} kann das besonders wehtun." if weakness else "")
    return ""

def dynamic_other_hint(question: Dict[str, Any], context: Dict[str, str]) -> str:
    theme = context.get("theme", "")
    tone = context.get("tone", "")
    if question["type"] == "select":
        if context.get("setup_type") == "world":
            return f"Wenn nichts passt, gib eine eigene Welt-Richtung an, die trotzdem mit {theme or 'dem Run'} und {tone or 'dem aktuellen Ton'} zusammenarbeitet."
        return f"Wenn nichts passt, beschreibe eine eigene Antwort, die zur Figur und zur Welt {theme or 'des Runs'} passt."
    if question["type"] == "multiselect":
        if context.get("setup_type") == "world":
            return "Eigene zusätzliche Gesetze oder Marker kannst du hier als kommagetrennte Liste ergänzen."
        return "Eigene zusätzliche Merkmale kannst du hier als kommagetrennte Liste ergänzen."
    return ""

def build_dynamic_option_entries(
    question: Dict[str, Any],
    *,
    context: Dict[str, str],
) -> List[Dict[str, str]]:
    entries = []
    for option in question.get("options", []) or []:
        text = str(option).strip()
        if not text:
            continue
        entries.append(
            {
                "value": text,
                "label": text,
                "description": dynamic_option_description(question["id"], text, context),
            }
        )
    return entries

def build_question_payload(
    question: Dict[str, Any],
    *,
    campaign: Dict[str, Any],
    setup_type: str,
    ai_copy: str,
    slot_name: Optional[str] = None,
    setup_node: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    context = build_setup_option_context(
        campaign,
        setup_type=setup_type,
        slot_name=slot_name,
        setup_node=setup_node,
    )
    payload = {
        "question_id": question["id"],
        "label": question["label"],
        "type": question["type"],
        "required": question.get("required", False),
        "options": question.get("options", []),
        "option_entries": build_dynamic_option_entries(question, context=context),
        "min_selected": question.get("min_selected"),
        "max_selected": question.get("max_selected"),
        "allow_other": question.get("allow_other", False),
        "other_hint": dynamic_other_hint(question, context),
        "ai_copy": clean_setup_ai_copy(ai_copy) or question["label"],
        "existing_answer": None,
    }
    if setup_node:
        payload["existing_answer"] = deep_copy(setup_node.get("answers", {}).get(question["id"]))
    return payload

def setup_helper_dependencies() -> setup_helpers.SetupHelperDependencies:
    return setup_helpers.SetupHelperDependencies(
        setup_random_system_prompt=SETUP_RANDOM_SYSTEM_PROMPT,
        setup_random_schema=SETUP_RANDOM_SCHEMA,
        target_turns_defaults=TARGET_TURNS_DEFAULTS,
        pacing_profile_defaults=PACING_PROFILE_DEFAULTS,
        max_players=MAX_PLAYERS,
        call_ollama_schema=call_ollama_schema,
        extract_text_answer=extract_text_answer,
        normalized_eval_text=normalized_eval_text,
        utc_now=utc_now,
        deep_copy=deep_copy,
        current_question_id=current_question_id,
        normalize_answer_summary_defaults=normalize_answer_summary_defaults,
        normalize_resource_name=normalize_resource_name,
        normalize_campaign_length_choice=normalize_campaign_length_choice,
        normalize_ruleset_choice=normalize_ruleset_choice,
        parse_attribute_range=parse_attribute_range,
        parse_factions=parse_factions,
        parse_lines=parse_lines,
        parse_earth_items=parse_earth_items,
        normalize_world_settings=normalize_world_settings,
        ensure_world_codex_from_setup=ensure_world_codex_from_setup,
        initialize_dynamic_slots=initialize_dynamic_slots,
        apply_world_summary_to_boards=apply_world_summary_to_boards,
        apply_character_summary_to_state=apply_character_summary_to_state,
        maybe_start_adventure=maybe_start_adventure,
    )

def validate_answer_payload(question: Dict[str, Any], answer: Dict[str, Any]) -> Any:
    return setup_helpers.validate_answer_payload(question, answer)

def fallback_random_text(question_id: str, *, setup_type: str, campaign: Dict[str, Any], slot_name: Optional[str] = None) -> str:
    return setup_helpers.fallback_random_text(
        question_id,
        setup_type=setup_type,
        campaign=campaign,
        slot_name=slot_name,
        deps=setup_helper_dependencies(),
    )

def fallback_random_answer_payload(
    campaign: Dict[str, Any],
    question: Dict[str, Any],
    *,
    setup_type: str,
    slot_name: Optional[str] = None,
) -> Dict[str, Any]:
    return setup_helpers.fallback_random_answer_payload(
        campaign,
        question,
        setup_type=setup_type,
        slot_name=slot_name,
        deps=setup_helper_dependencies(),
    )

def generate_random_setup_answer(
    campaign: Dict[str, Any],
    question: Dict[str, Any],
    *,
    setup_type: str,
    slot_name: Optional[str] = None,
    setup_node: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return setup_helpers.generate_random_setup_answer(
        campaign,
        question,
        setup_type=setup_type,
        slot_name=slot_name,
        setup_node=setup_node,
        deps=setup_helper_dependencies(),
    )

def store_setup_answer(
    setup_node: Dict[str, Any],
    question: Dict[str, Any],
    stored: Any,
    *,
    player_id: Optional[str],
    source: str = "manual",
) -> None:
    return setup_helpers.store_setup_answer(
        setup_node,
        question,
        stored,
        player_id=player_id,
        source=source,
        deps=setup_helper_dependencies(),
    )

def setup_answer_to_input_payload(question: Dict[str, Any], stored: Any) -> Dict[str, Any]:
    return setup_helpers.setup_answer_to_input_payload(question, stored)

def setup_answer_preview_text(question: Dict[str, Any], stored: Any) -> str:
    return setup_helpers.setup_answer_preview_text(question, stored)

def build_random_setup_preview(
    campaign: Dict[str, Any],
    setup_node: Dict[str, Any],
    question_map: Dict[str, Dict[str, Any]],
    *,
    setup_type: str,
    player_id: Optional[str],
    slot_name: Optional[str] = None,
    mode: str,
    question_id: Optional[str] = None,
    preview_answers: Optional[List["SetupAnswerIn"]] = None,
) -> List[Dict[str, Any]]:
    return setup_helpers.build_random_setup_preview(
        campaign,
        setup_node,
        question_map,
        setup_type=setup_type,
        player_id=player_id,
        slot_name=slot_name,
        mode=mode,
        question_id=question_id,
        preview_answers=preview_answers,
        deps=setup_helper_dependencies(),
    )

def apply_random_setup_preview(
    campaign: Dict[str, Any],
    setup_node: Dict[str, Any],
    question_map: Dict[str, Dict[str, Any]],
    preview_answers: List["SetupAnswerIn"],
    *,
    player_id: Optional[str],
) -> int:
    return setup_helpers.apply_random_setup_preview(
        campaign,
        setup_node,
        question_map,
        preview_answers,
        player_id=player_id,
        deps=setup_helper_dependencies(),
    )

def finalize_world_setup(campaign: Dict[str, Any], player_id: Optional[str]) -> None:
    setup_helpers.finalize_world_setup(campaign, player_id, deps=setup_helper_dependencies())

def finalize_character_setup(campaign: Dict[str, Any], slot_name: str) -> Optional[Dict[str, Any]]:
    return setup_helpers.finalize_character_setup(campaign, slot_name, deps=setup_helper_dependencies())

def build_world_summary(campaign: Dict[str, Any]) -> Dict[str, Any]:
    return setup_helpers.build_world_summary(campaign, deps=setup_helper_dependencies())

def build_character_summary(campaign: Dict[str, Any], slot_name: str) -> Dict[str, Any]:
    return setup_helpers.build_character_summary(campaign, slot_name, deps=setup_helper_dependencies())

def apply_world_summary_to_boards(campaign: Dict[str, Any], updated_by: Optional[str]) -> None:
    summary = campaign["setup"]["world"]["summary"]
    boards = campaign.setdefault("boards", {})
    if not isinstance(boards, dict):
        boards = {}
        campaign["boards"] = boards

    boards["plot_essentials"] = {
        "premise": summary.get("premise", ""),
        "current_goal": "",
        "current_threat": summary.get("central_conflict", ""),
        "active_scene": "",
        "open_loops": [],
        "tone": summary.get("tone", ""),
        "updated_at": utc_now(),
        "updated_by": updated_by,
    }
    authors_lines = [
        f"Theme: {summary.get('theme', '')}",
        f"Ton: {summary.get('tone', '')}",
        f"Schwierigkeit: {summary.get('difficulty', '')}",
        f"Wertebereich: {summary.get('attribute_range_label', '')}",
        f"Kraftquelle: {summary.get('resource_name', '')}",
        f"Tod: {summary.get('death_policy', '')}",
        f"Ressourcen: {summary.get('resource_scarcity', '')}",
        f"Heilung: {summary.get('healing_frequency', '')}",
        f"Monsterdichte: {summary.get('monsters_density', '')}",
        f"Erzählrahmen: {summary.get('ruleset', '')}",
        f"Outcome-Modell: {summary.get('outcome_model', '')}",
        f"Weltstruktur: {summary.get('world_structure', '')}",
        f"Weltgesetze: {', '.join(summary.get('world_laws', []))}",
        f"Zentraler Konflikt: {summary.get('central_conflict', '')}",
        f"Tabus/Notizen: {summary.get('taboos', '')}",
    ]
    boards["authors_note"] = {
        "content": "\n".join(line for line in authors_lines if line.split(": ", 1)[1]),
        "updated_at": utc_now(),
        "updated_by": updated_by,
    }
    world_info_entries: List[Dict[str, Any]] = [
        {
            "entry_id": make_id("world"),
            "title": "Weltstruktur",
            "category": "world",
            "content": summary.get("world_structure", ""),
            "tags": ["setup"],
            "updated_at": utc_now(),
            "updated_by": updated_by,
        },
        {
            "entry_id": make_id("world"),
            "title": "Wertebereich",
            "category": "rule",
            "content": summary.get("attribute_range_label", ""),
            "tags": ["setup", "rule"],
            "updated_at": utc_now(),
            "updated_by": updated_by,
        },
        {
            "entry_id": make_id("world"),
            "title": "Kraftquelle",
            "category": "rule",
            "content": summary.get("resource_name", ""),
            "tags": ["setup", "rule"],
            "updated_at": utc_now(),
            "updated_by": updated_by,
        },
        {
            "entry_id": make_id("world"),
            "title": "Weltgesetze",
            "category": "rule",
            "content": ", ".join(summary.get("world_laws", [])),
            "tags": ["setup"],
            "updated_at": utc_now(),
            "updated_by": updated_by,
        },
        {
            "entry_id": make_id("world"),
            "title": "Zentraler Konflikt",
            "category": "conflict",
            "content": summary.get("central_conflict", ""),
            "tags": ["setup"],
            "updated_at": utc_now(),
            "updated_by": updated_by,
        },
    ]
    factions = summary.get("factions", [])
    if not isinstance(factions, list):
        factions = []
    for faction in factions:
        if not isinstance(faction, dict):
            continue
        world_info_entries.append(
            {
                "entry_id": make_id("world"),
                "title": faction.get("name", "Fraktion"),
                "category": "faction",
                "content": f"Ziel: {faction.get('goal', '')} Methoden: {faction.get('methods', '')}".strip(),
                "tags": ["setup", "faction"],
                "updated_at": utc_now(),
                "updated_by": updated_by,
            }
        )
    boards["world_info"] = world_info_entries

def initialize_dynamic_slots(campaign: Dict[str, Any], player_count: int) -> None:
    player_count = max(1, min(MAX_PLAYERS, int(player_count)))
    campaign["claims"] = {}
    campaign["state"]["characters"] = {}
    for index in range(1, player_count + 1):
        current_slot = slot_id(index)
        campaign["claims"][current_slot] = None
        campaign["state"]["characters"][current_slot] = blank_character_state(current_slot)
        campaign["setup"]["characters"].setdefault(current_slot, default_character_setup_node())

def apply_character_summary_to_state(campaign: Dict[str, Any], slot_name: str) -> None:
    setup_node = campaign["setup"]["characters"][slot_name]
    summary = setup_node["summary"]
    character = campaign["state"]["characters"][slot_name]
    world_time = normalize_world_time(campaign["state"]["meta"])
    age_years = infer_age_years(summary.get("age_bucket", ""))
    character["bio"] = {
        "name": summary.get("display_name", ""),
        "gender": summary.get("gender", ""),
        "age": summary.get("age_bucket", ""),
        "age_years": age_years,
        "age_stage": derive_age_stage(age_years),
        "earth_life": summary.get("earth_life", ""),
        "personality": summary.get("personality_tags", []),
        "background_tags": summary.get("background_tags", []),
        "strength": summary.get("strength", ""),
        "weakness": summary.get("weakness", ""),
        "focus": summary.get("current_focus", ""),
        "goal": summary.get("first_goal", ""),
        "isekai_price": summary.get("isekai_price", ""),
        "earth_items": normalize_creator_item_list(summary.get("earth_items", [])),
        "signature_item": clean_creator_item_name(summary.get("signature_item", "")),
    }
    assignment = summary.get("attribute_assignment")
    if not isinstance(assignment, dict) or not isinstance(assignment.get("weights"), dict):
        assignment = generate_character_attribute_weights(campaign, slot_name, summary)
        summary["attribute_assignment"] = assignment
    weights = normalize_attribute_weight_pool(assignment.get("weights", {}), total=120)
    attributes = level_one_attributes_from_weights(campaign, weights)
    summary["attribute_assignment"] = {
        "weights": weights,
        "source": assignment.get("source", "fallback"),
        "pool_total": 120,
        "level_one_budget": level_one_attribute_budget(campaign),
        "level_one_cap": level_one_attribute_cap(campaign),
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
    character["progression"]["resource_name"] = str((((campaign.get("state") or {}).get("world") or {}).get("settings") or {}).get("resource_name") or "Aether")
    character["progression"]["resource_current"] = int(character.get("res_current", 5) or 5)
    character["progression"]["resource_max"] = int(character.get("res_max", 5) or 5)
    class_start_mode = normalized_eval_text(summary.get("class_start_mode", ""))
    if "ki" in class_start_mode:
        seed = summary.get("class_seed") or summary.get("current_focus") or summary.get("strength") or "Überlebender"
        character["class_current"] = normalize_class_current(
            {
                "id": f"class_{re.sub(r'[^a-z0-9]+', '_', normalized_eval_text(seed)).strip('_') or 'wanderer'}",
                "name": str(seed).strip().title(),
                "rank": "F",
                "level": 1,
                "level_max": 10,
                "xp": 0,
                "xp_next": 100,
                "affinity_tags": [str(summary.get("strength") or "").strip().split("/", 1)[0].lower().replace(" ", "_"), str(summary.get("current_focus") or "").strip().split("/", 1)[0].lower().replace(" ", "_")],
                "description": f"Eine frühe Klasse, geformt aus {summary.get('strength', 'Überleben')} und dem Fokus {summary.get('current_focus', 'Unbekannt')}.",
                "ascension": {"status": "none", "quest_id": None, "requirements": [], "result_hint": None},
            }
        )
    elif "selbst" in class_start_mode or (not class_start_mode and normalized_eval_text(summary.get("class_custom_name", ""))):
        character["class_current"] = normalize_class_current(
            {
                "id": f"class_{re.sub(r'[^a-z0-9]+', '_', normalized_eval_text(summary.get('class_custom_name', '') or 'eigen')).strip('_') or 'eigen'}",
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
    reconcile_creator_inventory_items(campaign["state"], character)
    refresh_skill_progression(character)
    rebuild_character_derived(character, campaign["state"].get("items", {}), world_time)
    reconcile_canonical_resources(character, (((campaign.get("state") or {}).get("world") or {}).get("settings") or {}))
    strip_legacy_shadow_fields(character, (((campaign.get("state") or {}).get("world") or {}).get("settings") or {}))
    if ENABLE_LEGACY_SHADOW_WRITEBACK:
        write_legacy_shadow_fields(character, (((campaign.get("state") or {}).get("world") or {}).get("settings") or {}))
    sync_scars_into_appearance(character)

def is_legacy_campaign(campaign: Dict[str, Any]) -> bool:
    chars = list((campaign.get("state", {}).get("characters") or {}).keys())
    claims = list((campaign.get("claims") or {}).keys())
    if any(name in LEGACY_CHARACTERS for name in chars):
        return True
    if any(name in LEGACY_CHARACTERS for name in claims):
        return True
    setup = campaign.get("setup", {})
    if setup and setup.get("version") == 2:
        return False
    return bool(chars or claims) and not all(is_slot_id(name) for name in chars + claims if name)

def remap_turn_context_slot_names(turn: Dict[str, Any], mapping: Dict[str, str]) -> None:
    if turn.get("actor") in mapping:
        turn["actor"] = mapping[turn["actor"]]
    patch_chars = (turn.get("patch") or {}).get("characters")
    if isinstance(patch_chars, dict):
        turn["patch"]["characters"] = {mapping.get(key, key): value for key, value in patch_chars.items()}
    for state_key in ("state_before", "state_after"):
        state_snapshot = turn.get(state_key) or {}
        chars = state_snapshot.get("characters")
        if isinstance(chars, dict):
            state_snapshot["characters"] = {mapping.get(key, key): value for key, value in chars.items()}
    prompt_context = ((turn.get("prompt_payload") or {}).get("context") or {})
    if prompt_context:
        chars = prompt_context.get("characters")
        if isinstance(chars, dict):
            prompt_context["characters"] = {mapping.get(key, key): value for key, value in chars.items()}
        claims = prompt_context.get("claims")
        if isinstance(claims, dict):
            prompt_context["claims"] = {mapping.get(key, key): value for key, value in claims.items()}
        active = prompt_context.get("active_party")
        if isinstance(active, list):
            prompt_context["active_party"] = [mapping.get(entry, entry) for entry in active]
        display = prompt_context.get("display_party")
        if isinstance(display, list):
            for entry in display:
                if isinstance(entry, dict) and entry.get("slot_id") in mapping:
                    entry["slot_id"] = mapping[entry["slot_id"]]
    for request in turn.get("requests", []):
        if isinstance(request, dict) and request.get("actor") in mapping:
            request["actor"] = mapping[request["actor"]]

def migrate_campaign_to_dynamic_slots(campaign: Dict[str, Any]) -> None:
    mapping = {name: slot_id(index + 1) for index, name in enumerate(LEGACY_CHARACTERS)}
    world_question = WORLD_QUESTION_MAP
    char_question = CHARACTER_QUESTION_MAP
    state = campaign.setdefault("state", deep_copy(INITIAL_STATE))
    old_characters = state.get("characters") or {}
    new_characters: Dict[str, Any] = {}
    old_claims = campaign.get("claims") or {}
    new_claims: Dict[str, Any] = {}
    for index, legacy_name in enumerate(LEGACY_CHARACTERS, start=1):
        new_slot = slot_id(index)
        old_char = deep_copy(old_characters.get(legacy_name) or blank_character_state(new_slot))
        old_char["slot_id"] = new_slot
        new_characters[new_slot] = old_char
        new_claims[new_slot] = old_claims.get(legacy_name)
    state["characters"] = new_characters
    campaign["claims"] = new_claims

    old_setup = campaign.get("setup") or {}
    new_setup = default_setup()
    world_setup = (old_setup.get("world") or {})
    legacy_campaign_length = normalize_campaign_length_choice((((state.get("world") or {}).get("settings") or {}).get("campaign_length")))
    if legacy_campaign_length == "short":
        legacy_campaign_length_label = "Kurz"
    elif legacy_campaign_length == "open":
        legacy_campaign_length_label = "Unbestimmt"
    else:
        legacy_campaign_length_label = "Mittel"
    world_answers = {
        "theme": legacy_select_answer_payload(world_question["theme"], world_setup.get("theme", "")),
        "player_count": {"selected": str(max(1, len([owner for owner in new_claims.values() if owner]) or 1)), "other_text": ""},
        "campaign_length": legacy_select_answer_payload(world_question["campaign_length"], legacy_campaign_length_label),
        "tone": legacy_select_answer_payload(world_question["tone"], world_setup.get("tone", "")),
        "difficulty": legacy_select_answer_payload(world_question["difficulty"], "Brutal"),
        "death_possible": True,
        "monsters_density": legacy_select_answer_payload(world_question["monsters_density"], "Regelmäßig"),
        "resource_scarcity": legacy_select_answer_payload(world_question["resource_scarcity"], "Mittel"),
        "resource_name": legacy_select_answer_payload(
            world_question["resource_name"],
            normalize_resource_name((((state.get("world") or {}).get("settings") or {}).get("resource_name") or "Aether")),
        ),
        "healing_frequency": legacy_select_answer_payload(world_question["healing_frequency"], "Normal"),
        "ruleset": legacy_select_answer_payload(world_question["ruleset"], "Konsequent"),
        "attribute_range": legacy_select_answer_payload(world_question["attribute_range"], "1-10"),
        "outcome_model": legacy_select_answer_payload(world_question["outcome_model"], "Erfolg / Teilerfolg / Misserfolg-mit-Preis"),
        "world_structure": legacy_select_answer_payload(world_question["world_structure"], world_setup.get("world_structure", "")),
        "world_laws": {"selected": [], "other_values": []},
        "central_conflict": str(world_setup.get("conflict", "") or campaign.get("boards", {}).get("plot_essentials", {}).get("current_threat", "")).strip(),
        "factions": "\n".join(
            entry.get("title", "")
            for entry in campaign.get("boards", {}).get("world_info", [])
            if entry.get("category") == "faction"
        ),
        "taboos": str(world_setup.get("special_notes", "")).strip(),
    }
    new_setup["world"]["answers"] = world_answers
    new_setup["world"]["summary"] = build_world_summary({"setup": {"world": {"answers": world_answers}}})
    new_setup["world"]["completed"] = state.get("meta", {}).get("phase") in ("character_setup", "character_setup_open", "adventure", "active", "ready_to_start")

    old_setup_chars = old_setup.get("characters") or {}
    for legacy_name, new_slot in mapping.items():
        old_answers = ((old_setup_chars.get(legacy_name) or {}).get("answers") or {})
        bio = (new_characters[new_slot].get("bio") or {})
        legacy_gender = bio.get("gender") or extract_text_answer(old_answers.get("char_gender"))
        legacy_age = bio.get("age") or extract_text_answer(old_answers.get("char_age"))
        legacy_strength = bio.get("strength") or extract_text_answer(old_answers.get("strength"))
        legacy_weakness = bio.get("weakness") or extract_text_answer(old_answers.get("weakness"))
        legacy_focus = bio.get("focus") or extract_text_answer(old_answers.get("current_focus"))
        legacy_price = bio.get("isekai_price") or extract_text_answer(old_answers.get("isekai_price"))
        legacy_items = bio.get("earth_items") or parse_earth_items(extract_text_answer(old_answers.get("earth_items")))
        current_class = normalize_class_current(new_characters[new_slot].get("class_current"))
        node = default_character_setup_node()
        node["answers"] = {
            "char_name": bio.get("name", ""),
            "char_gender": legacy_select_answer_payload(char_question["char_gender"], legacy_gender),
            "char_age": legacy_select_answer_payload(char_question["char_age"], legacy_age),
            "earth_life": bio.get("earth_life", old_answers.get("earth_life", "")),
            "personality_tags": {"selected": bio.get("personality", []), "other_values": []},
            "strength": legacy_select_answer_payload(char_question["strength"], legacy_strength),
            "weakness": legacy_select_answer_payload(char_question["weakness"], legacy_weakness),
            "class_start_mode": legacy_select_answer_payload(char_question["class_start_mode"], "Erst in der Story"),
            "class_seed": "",
            "class_custom_name": (current_class or {}).get("name", ""),
            "class_custom_description": (current_class or {}).get("description", ""),
            "class_custom_tags": ", ".join((current_class or {}).get("affinity_tags", [])),
            "current_focus": legacy_select_answer_payload(char_question["current_focus"], legacy_focus),
            "first_goal": bio.get("goal", ""),
            "isekai_price": legacy_select_answer_payload(char_question["isekai_price"], legacy_price),
            "earth_items": ", ".join(legacy_items),
            "signature_item": bio.get("signature_item", ""),
        }
        node["summary"] = build_character_summary({"setup": {"characters": {new_slot: node}}}, new_slot)
        node["completed"] = bool(node["summary"].get("display_name")) or state.get("meta", {}).get("phase") in {"adventure", "active"}
        new_setup["characters"][new_slot] = node

    campaign["setup"] = new_setup
    for turn in campaign.get("turns", []):
        remap_turn_context_slot_names(turn, mapping)

    campaign["legacy_migration"] = {
        "original_schema": "fixed_3_slots_v1",
        "migrated_at": utc_now(),
    }

def normalize_campaign(campaign: Dict[str, Any]) -> Dict[str, Any]:
    campaign.setdefault("state", deep_copy(INITIAL_STATE))
    campaign.setdefault("players", {})
    campaign.setdefault("boards", default_boards())
    campaign.setdefault("claims", {})
    campaign.setdefault("turns", [])
    campaign.setdefault("board_revisions", [])
    campaign.setdefault("legacy_migration", None)

    if is_legacy_campaign(campaign):
        migrate_campaign_to_dynamic_slots(campaign)

    state = campaign["state"]
    state.setdefault("meta", deep_copy(INITIAL_STATE["meta"]))
    if state["meta"].get("phase") == "character_creation":
        state["meta"]["phase"] = "character_setup_open"
    if state["meta"].get("phase") == "character_setup":
        state["meta"]["phase"] = "character_setup_open"
    if state["meta"].get("phase") == "adventure":
        state["meta"]["phase"] = "active"
    if state["meta"].get("phase") not in PHASES:
        state["meta"]["phase"] = "lobby"
    existing_intro_state = state["meta"].get("intro_state")
    if isinstance(existing_intro_state, dict):
        normalized_intro_state = default_intro_state()
        normalized_intro_state.update(existing_intro_state)
        existing_intro_state.clear()
        existing_intro_state.update(normalized_intro_state)
        state["meta"]["intro_state"] = existing_intro_state
    else:
        state["meta"]["intro_state"] = default_intro_state()
    state["meta"]["world_time"] = normalize_world_time(state["meta"])
    state.setdefault("world", deep_copy(INITIAL_STATE["world"]))
    state["world"].setdefault("settings", {})
    state["world"]["settings"] = normalize_world_settings(state["world"].get("settings") or {})
    state["world"].setdefault("elements", {})
    state["world"].setdefault("element_relations", {})
    state["world"].setdefault("element_alias_index", {})
    state["world"].setdefault("element_class_paths", {})
    state["world"]["day"] = state["meta"]["world_time"]["day"]
    state["world"]["time"] = state["meta"]["world_time"]["time_of_day"]
    state["world"]["weather"] = state["meta"]["world_time"]["weather"]
    normalize_meta_timing(state["meta"])
    normalize_combat_meta(state["meta"])
    normalize_attribute_influence_meta(state["meta"])
    normalize_extraction_quarantine_meta(state["meta"])
    migrations_meta = normalize_meta_migrations(state["meta"])
    milestone_defaults = milestone_state_for_turn(int(state["meta"].get("turn", 0) or 0), active_pacing_profile(state))
    state["meta"]["last_milestone_turn"] = int(state["meta"].get("last_milestone_turn", milestone_defaults["last"]) or milestone_defaults["last"])
    state["meta"]["next_milestone_turn"] = int(state["meta"].get("next_milestone_turn", milestone_defaults["next"]) or milestone_defaults["next"])
    state.setdefault("map", {"nodes": {}, "edges": []})
    state.setdefault("plotpoints", [])
    state.setdefault("scenes", {})
    state.setdefault("items", {})
    state.setdefault("characters", {})
    state.setdefault("recent_story", [])
    state.setdefault("events", [])
    state.setdefault("codex", {"races": {}, "beasts": {}, "meta": deep_copy(CODEX_DEFAULT_META)})
    state.setdefault("npc_codex", {})
    state.setdefault("npc_alias_index", {})
    normalize_world_codex_structures(state)

    boards = campaign["boards"]
    boards.setdefault("plot_essentials", default_boards()["plot_essentials"])
    boards.setdefault("authors_note", default_boards()["authors_note"])
    boards.setdefault("story_cards", [])
    boards.setdefault("world_info", [])
    boards.setdefault("memory_summary", default_boards()["memory_summary"])
    boards.setdefault("player_diaries", {})
    for player_id, player in (campaign.get("players") or {}).items():
        boards["player_diaries"].setdefault(
            player_id,
            default_player_diary_entry(player_id, player.get("display_name", "")),
        )
        boards["player_diaries"][player_id]["display_name"] = player.get("display_name", "")

    normalize_npc_codex_state(campaign)
    should_seed_npc_codex = not bool(migrations_meta.get("npc_codex_seeded_from_story_cards"))
    if should_seed_npc_codex:
        if not state.get("npc_codex"):
            seed_npc_codex_from_story_cards(campaign)
            normalize_npc_codex_state(campaign)
        migrations_meta["npc_codex_seeded_from_story_cards"] = True

    setup = campaign.setdefault("setup", default_setup())
    if setup.get("version") != 4:
        fallback = default_setup()
        fallback["world"].update(setup.get("world", {}))
        fallback["characters"].update(setup.get("characters", {}))
        setup = campaign["setup"] = fallback
    setup.setdefault("engine", {})
    setup["engine"]["world_catalog_version"] = CATALOG_VERSION
    setup["engine"]["character_catalog_version"] = CATALOG_VERSION
    setup.setdefault("world", default_setup()["world"])
    setup["world"]["question_queue"] = build_world_question_queue()
    setup["world"].setdefault("answers", {})
    setup["world"].setdefault("summary", {})
    setup["world"].setdefault("raw_transcript", [])
    setup["world"].setdefault("question_runtime", {})
    setup.setdefault("characters", {})
    if setup["world"].get("completed"):
        ensure_world_codex_from_setup(state, setup["world"].get("summary") or {})

    effective_world_time = normalize_world_time(state["meta"])
    for slot_name in campaign_slots(campaign):
        state["characters"].setdefault(slot_name, blank_character_state(slot_name))
        state["characters"][slot_name] = normalize_character_state(
            state["characters"][slot_name],
            slot_name,
            state.get("items", {}),
            effective_world_time,
        )
        state["characters"][slot_name]["element_affinities"] = normalize_element_id_list(
            state["characters"][slot_name].get("element_affinities") or [],
            state.get("world") or {},
        )
        state["characters"][slot_name]["element_resistances"] = normalize_element_id_list(
            state["characters"][slot_name].get("element_resistances") or [],
            state.get("world") or {},
        )
        state["characters"][slot_name]["element_weaknesses"] = normalize_element_id_list(
            state["characters"][slot_name].get("element_weaknesses") or [],
            state.get("world") or {},
        )
        normalized_class = normalize_class_current(state["characters"][slot_name].get("class_current"))
        if normalized_class:
            resolved_class_element = resolve_class_element_id(normalized_class, state.get("world") or {})
            if resolved_class_element:
                normalized_class["element_id"] = resolved_class_element
                normalized_class["element_tags"] = list(
                    dict.fromkeys([*(normalized_class.get("element_tags") or []), resolved_class_element])
                )
            state["characters"][slot_name]["class_current"] = normalize_class_current(normalized_class)
        resource_name = resource_name_for_character(state["characters"][slot_name], state["world"].get("settings") or {})
        normalized_skills: Dict[str, Dict[str, Any]] = {}
        for skill_id, skill_value in ((state["characters"][slot_name].get("skills") or {}).items()):
            normalized_skill = normalize_dynamic_skill_state(skill_value, skill_id=str(skill_id), resource_name=resource_name)
            normalized_skill = normalize_skill_elements_for_world(normalized_skill, state.get("world") or {})
            normalized_skills[normalized_skill["id"]] = normalized_skill
        state["characters"][slot_name]["skills"] = normalized_skills
        reconcile_creator_inventory_items(state, state["characters"][slot_name])
        setup["characters"].setdefault(slot_name, default_character_setup_node())
        setup["characters"][slot_name]["question_queue"] = build_character_question_queue()
        setup["characters"][slot_name].setdefault("answers", {})
        setup["characters"][slot_name].setdefault("summary", {})
        setup["characters"][slot_name].setdefault("raw_transcript", [])
        setup["characters"][slot_name].setdefault("question_runtime", {})
        campaign["claims"].setdefault(slot_name, None)

    if setup["world"].get("completed") and not campaign_slots(campaign):
        initialize_dynamic_slots(campaign, int(setup["world"].get("summary", {}).get("player_count") or 1))

    if campaign.get("turns") and any(turn.get("status") == "active" for turn in campaign.get("turns", [])):
        state["meta"]["phase"] = "active"
        if state["meta"]["intro_state"].get("status") in ("idle", "pending", "failed"):
            state["meta"]["intro_state"]["status"] = "generated"
        if not state["meta"]["intro_state"].get("generated_turn_id"):
            state["meta"]["intro_state"]["generated_turn_id"] = active_turns(campaign)[0]["turn_id"]
    elif setup["world"].get("completed"):
        state["meta"]["phase"] = "ready_to_start" if can_start_adventure(campaign) else "character_setup_open"
    else:
        if state["meta"].get("phase") not in {"lobby", "world_setup"}:
            state["meta"]["phase"] = "world_setup"

    # normalize_campaign stays structurally passive by default.
    # Legacy backfill is explicit opt-in only.
    if ENABLE_HEURISTIC_NORMALIZE_BACKFILL:
        run_legacy_normalize_backfill(campaign)
    compute_turn_budget_estimates(state)

    return campaign

def load_campaign(campaign_id: str) -> Dict[str, Any]:
    path = campaign_path(campaign_id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Kampagne nicht gefunden.")
    return normalize_campaign(load_json(path))

def save_campaign(
    campaign: Dict[str, Any],
    *,
    reason: str = "campaign_updated",
    trace_ctx: Optional[Dict[str, Any]] = None,
) -> None:
    try:
        emit_turn_phase_event(trace_ctx, phase="normalize", success=True, extra={"reason": reason})
        campaign = normalize_campaign(campaign)
        emit_turn_phase_event(trace_ctx, phase="normalize", success=True, extra={"reason": reason, "result": "ok"})
    except Exception as exc:
        emit_turn_phase_event(
            trace_ctx,
            phase="normalize",
            success=False,
            error_code=ERROR_CODE_NORMALIZE,
            error_class=exc.__class__.__name__,
            message=str(exc)[:240],
            extra={"reason": reason},
        )
        if trace_ctx is not None:
            raise turn_flow_error(
                error_code=ERROR_CODE_NORMALIZE,
                phase="normalize",
                trace_ctx=trace_ctx,
                exc=exc,
            )
        raise

    campaign["campaign_meta"]["updated_at"] = utc_now()
    campaign_id = campaign["campaign_meta"]["campaign_id"]

    try:
        emit_turn_phase_event(trace_ctx, phase="persist_save", success=True, extra={"reason": reason})
        save_json(campaign_path(campaign_id), campaign)
        emit_turn_phase_event(trace_ctx, phase="persist_save", success=True, extra={"reason": reason, "result": "ok"})
    except Exception as exc:
        emit_turn_phase_event(
            trace_ctx,
            phase="persist_save",
            success=False,
            error_code=ERROR_CODE_PERSISTENCE,
            error_class=exc.__class__.__name__,
            message=str(exc)[:240],
            extra={"reason": reason},
        )
        if trace_ctx is not None:
            raise turn_flow_error(
                error_code=ERROR_CODE_PERSISTENCE,
                phase="persist_save",
                trace_ctx=trace_ctx,
                exc=exc,
            )
        raise

    try:
        emit_turn_phase_event(trace_ctx, phase="sse_broadcast", success=True, extra={"reason": reason})
        live_state_service.broadcast_campaign_sync(campaign_id, reason=reason)
        emit_turn_phase_event(trace_ctx, phase="sse_broadcast", success=True, extra={"reason": reason, "result": "ok"})
    except Exception as exc:
        emit_turn_phase_event(
            trace_ctx,
            phase="sse_broadcast",
            success=False,
            error_code=ERROR_CODE_SSE_BROADCAST,
            error_class=exc.__class__.__name__,
            message=str(exc)[:240],
            extra={"reason": reason},
        )
        if trace_ctx is not None:
            raise turn_flow_error(
                error_code=ERROR_CODE_SSE_BROADCAST,
                phase="sse_broadcast",
                trace_ctx=trace_ctx,
                exc=exc,
            )
        raise

def active_turns(campaign: Dict[str, Any]) -> List[Dict[str, Any]]:
    return campaign_view_serializer.active_turns(campaign)

def is_host(campaign: Dict[str, Any], player_id: Optional[str]) -> bool:
    return campaign_view_serializer.is_host(campaign, player_id)

def is_campaign_player(campaign: Dict[str, Any], player_id: Optional[str]) -> bool:
    return campaign_view_serializer.is_campaign_player(campaign, player_id)

def build_patch_summary(patch: Dict[str, Any]) -> Dict[str, Any]:
    return campaign_view_serializer.build_patch_summary(patch)

def is_continue_story_content(content: str) -> bool:
    normalized = str(content or "").strip()
    return normalized == CONTINUE_STORY_MARKER or normalized.startswith("Weiter.")

def public_turn(turn: Dict[str, Any], campaign: Dict[str, Any], viewer_id: Optional[str]) -> Dict[str, Any]:
    return campaign_view_serializer.public_turn(
        turn,
        campaign,
        viewer_id,
        display_name_for_slot=display_name_for_slot,
        is_slot_id=is_slot_id,
        normalize_requests_payload=normalize_requests_payload,
        blank_patch=blank_patch,
        is_campaign_player_fn=is_campaign_player,
    )

def build_world_question_state(campaign: Dict[str, Any], viewer_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not is_host(campaign, viewer_id):
        return None
    setup_node = campaign["setup"]["world"]
    qid = current_question_id(setup_node)
    if not qid:
        return None
    base_question = WORLD_QUESTION_MAP[qid]
    question = build_question_payload(
        base_question,
        campaign=campaign,
        setup_type="world",
        ai_copy=get_persisted_question_ai_copy(setup_node, qid) or base_question["label"],
        setup_node=setup_node,
    )
    return {
        "question": question,
        "progress": progress_payload(setup_node),
    }

def build_character_question_state(campaign: Dict[str, Any], slot_name: str) -> Optional[Dict[str, Any]]:
    setup_node = campaign["setup"]["characters"].get(slot_name)
    if not setup_node:
        return None
    qid = current_question_id(setup_node)
    if not qid:
        return None
    base_question = CHARACTER_QUESTION_MAP[qid]
    question = build_question_payload(
        base_question,
        campaign=campaign,
        setup_type="character",
        ai_copy=get_persisted_question_ai_copy(setup_node, qid) or base_question["label"],
        slot_name=slot_name,
        setup_node=setup_node,
    )
    return {
        "question": question,
        "progress": progress_payload(setup_node),
    }

def build_viewer_context(campaign: Dict[str, Any], player_id: Optional[str]) -> Dict[str, Any]:
    player = campaign.get("players", {}).get(player_id or "")
    claimed_slot = player_claim(campaign, player_id)
    pending_setup_question = None
    current_phase = str(campaign["state"]["meta"].get("phase") or "")
    if not campaign["setup"]["world"].get("completed", False) and current_phase in {"lobby", "world_setup"}:
        pending_setup_question = build_world_question_state(campaign, player_id)
    elif claimed_slot and current_phase in {"character_setup_open", "ready_to_start"}:
        pending_setup_question = build_character_question_state(campaign, claimed_slot)
    return {
        "player_id": player_id,
        "display_name": player.get("display_name") if player else None,
        "is_host": is_host(campaign, player_id),
        "claimed_slot_id": claimed_slot,
        "claimed_character": claimed_slot,
        "phase": current_phase,
        "needs_world_setup": not campaign["setup"]["world"].get("completed", False),
        "needs_character_setup": (
            current_phase in {"character_setup_open", "ready_to_start"}
            and bool(claimed_slot)
            and not campaign["setup"]["characters"].get(claimed_slot, {}).get("completed", False)
        ),
        "pending_setup_question": pending_setup_question,
    }

def build_setup_runtime(campaign: Dict[str, Any], viewer_id: Optional[str]) -> Dict[str, Any]:
    current_phase = str(campaign["state"]["meta"].get("phase") or "")
    claimed_slot = player_claim(campaign, viewer_id)
    world_node = campaign["setup"]["world"]
    world_question_state = build_world_question_state(campaign, viewer_id)
    world_chapter_key = setup_question_chapter_key("world", (world_question_state or {}).get("question", {}).get("question_id", ""))
    world_chapter_cfg = setup_chapter_config("world").get(world_chapter_key, {})
    world_slots = setup_slot_statuses(campaign)
    world_ready_count = sum(1 for entry in world_slots if entry.get("status") == "ready")
    world_total_count = len(world_slots)
    character_state = build_character_question_state(campaign, claimed_slot) if claimed_slot else None
    character_node = (((campaign.get("setup") or {}).get("characters") or {}).get(claimed_slot or "")) or {}
    char_chapter_key = setup_question_chapter_key("character", (character_state or {}).get("question", {}).get("question_id", ""))
    char_chapter_cfg = setup_chapter_config("character").get(char_chapter_key, {})
    return {
        "phase": current_phase,
        "phase_display": setup_phase_display(current_phase),
        "world": {
            "completed": world_node.get("completed", False),
            "progress": progress_payload(world_node),
            "global_progress": setup_global_progress(world_node),
            "next_question": world_question_state,
            "chapter_key": world_chapter_key,
            "chapter_label": world_chapter_cfg.get("label", "Welt"),
            "chapter_index": list(setup_chapter_config("world").keys()).index(world_chapter_key) + 1 if world_chapter_key in setup_chapter_config("world") else 1,
            "chapter_total": len(setup_chapter_config("world")),
            "chapter_progress": setup_chapter_progress(world_node, "world", world_chapter_key),
            "is_review_step": bool(world_node.get("completed")) or (
                bool((world_question_state or {}).get("progress", {}).get("total"))
                and int((world_question_state or {}).get("progress", {}).get("step", 0) or 0)
                >= int((world_question_state or {}).get("progress", {}).get("total", 0) or 0)
            ),
            "summary_preview": setup_summary_preview(campaign, "world"),
            "slot_statuses": world_slots,
            "ready_counter": {"ready": world_ready_count, "total": world_total_count},
        },
        "claimed_slot_id": claimed_slot,
        "character": (
            {
                **(character_state or {}),
                "global_progress": setup_global_progress(character_node),
                "chapter_key": char_chapter_key,
                "chapter_label": char_chapter_cfg.get("label", "Figur"),
                "chapter_index": list(setup_chapter_config("character").keys()).index(char_chapter_key) + 1 if char_chapter_key in setup_chapter_config("character") else 1,
                "chapter_total": len(setup_chapter_config("character")),
                "chapter_progress": setup_chapter_progress(character_node, "character", char_chapter_key),
                "is_review_step": bool((character_node.get("completed"))) or (
                    bool((character_state or {}).get("progress", {}).get("total"))
                    and int((character_state or {}).get("progress", {}).get("step", 0) or 0)
                    >= int((character_state or {}).get("progress", {}).get("total", 0) or 0)
                ),
                "summary_preview": setup_summary_preview(campaign, "character", claimed_slot),
            }
            if claimed_slot
            else None
        ),
        "slot_statuses": world_slots,
        "ready_counter": {"ready": world_ready_count, "total": world_total_count},
        "is_ready_to_start": current_phase == "ready_to_start",
    }

def filter_private_diary_content(content: Any, viewer_is_owner: bool) -> str:
    return campaign_view_serializer.filter_private_diary_content(content, viewer_is_owner)

def build_public_boards(campaign: Dict[str, Any], viewer_id: Optional[str]) -> Dict[str, Any]:
    return campaign_view_serializer.build_public_boards(
        campaign,
        viewer_id,
        deep_copy=deep_copy,
        filter_private_diary_content_fn=filter_private_diary_content,
    )

def build_campaign_view(campaign: Dict[str, Any], viewer_id: Optional[str]) -> Dict[str, Any]:
    dependencies = campaign_view_serializer.CampaignViewDependencies(
        normalize_campaign=normalize_campaign,
        deep_copy=deep_copy,
        build_setup_runtime=build_setup_runtime,
        available_slots=available_slots,
        active_party=active_party,
        display_name_for_slot=display_name_for_slot,
        normalize_world_time=normalize_world_time,
        build_public_boards=build_public_boards,
        active_turns=active_turns,
        public_turn=public_turn,
        build_party_overview=build_party_overview,
        campaign_slots=campaign_slots,
        public_player=public_player,
        build_viewer_context=build_viewer_context,
        live_snapshot=live_state_service.live_snapshot,
    )
    return campaign_view_serializer.build_campaign_view(campaign, viewer_id, deps=dependencies)

def remember_recent_story(campaign: Dict[str, Any]) -> None:
    campaign["state"]["recent_story"] = [turn["gm_text_display"] for turn in active_turns(campaign)][-20:]

def heuristic_memory_summary(campaign: Dict[str, Any]) -> str:
    turns = active_turns(campaign)
    if not turns:
        return "Noch keine Zusammenfassung vorhanden."
    last_turn = turns[-1]
    actor_name = display_name_for_slot(campaign, last_turn["actor"]) if is_slot_id(last_turn["actor"]) else last_turn["actor"]
    parts = [
        f"Aktueller Stand nach Zug {last_turn['turn_number']}.",
        f"Letzte Aktion von {actor_name} ({last_turn['action_type']}): {last_turn['input_text_display']}",
        f"Letzte GM-Antwort: {last_turn['gm_text_display'][:280]}",
    ]
    return " ".join(parts)

def rebuild_memory_summary(campaign: Dict[str, Any]) -> None:
    turns = active_turns(campaign)
    summary_turn = turns[-1]["turn_number"] if turns else 0
    if not turns:
        campaign["boards"]["memory_summary"] = {
            "content": "Noch keine Zusammenfassung vorhanden.",
            "updated_through_turn": 0,
            "updated_at": utc_now(),
        }
        return

    recent_turns = [
        {
            "turn_number": turn["turn_number"],
            "actor": display_name_for_slot(campaign, turn["actor"]) if is_slot_id(turn["actor"]) else turn["actor"],
            "action_type": turn["action_type"],
            "player": turn["input_text_display"],
            "gm": turn["gm_text_display"],
        }
        for turn in turns[-12:]
    ]
    payload = {
        "campaign": campaign["campaign_meta"]["title"],
        "world_summary": campaign["setup"]["world"].get("summary", {}),
        "characters": {
            slot_name: {
                "display_name": display_name_for_slot(campaign, slot_name),
                "scene_id": data["scene_id"],
                "hp": int(data.get("hp_current", 0) or 0),
                "stamina": int(data.get("sta_current", 0) or 0),
                "resource": int(data.get("res_current", 0) or 0),
                "conditions": compact_conditions(data),
            }
            for slot_name, data in campaign["state"]["characters"].items()
        },
        "recent_turns": recent_turns,
    }
    try:
        content = call_ollama_text(
            MEMORY_SYSTEM_PROMPT,
            "Fasse diese Kampagne kompakt zusammen:\n" + json.dumps(payload, ensure_ascii=False),
        )
    except Exception:
        content = heuristic_memory_summary(campaign)
    campaign["boards"]["memory_summary"] = {
        "content": content or heuristic_memory_summary(campaign),
        "updated_through_turn": summary_turn,
        "updated_at": utc_now(),
    }

def build_context_packet(
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    actor: str,
    action_type: str,
) -> str:
    normalized_characters = {}
    world_settings = (((state.get("world") or {}).get("settings") or {}))
    for slot_name, character in (state.get("characters") or {}).items():
        normalized_characters[slot_name] = normalize_character_state(character, slot_name, state.get("items", {}) or {})
    recent = []
    for turn in active_turns(campaign)[-8:]:
        recent.append(
            {
                "turn_number": turn["turn_number"],
                "actor": turn["actor"],
                "actor_display": display_name_for_slot(campaign, turn["actor"]) if is_slot_id(turn["actor"]) else turn["actor"],
                "action_type": turn["action_type"],
                "player_text": turn["input_text_display"],
                "gm_text": turn["gm_text_display"],
                "requests": turn.get("requests", []),
            }
        )
    packet = {
        "meta": state["meta"],
        "combat": (state.get("meta") or {}).get("combat", {}),
        "attribute_influence": (state.get("meta") or {}).get("attribute_influence", {}),
        "setup": campaign.get("setup", {}),
        "rules_profile": build_rules_profile(campaign),
        "active_party": active_party(campaign),
        "display_party": [
            {"slot_id": slot_name, "display_name": display_name_for_slot(campaign, slot_name)}
            for slot_name in active_party(campaign)
        ],
        "world": state["world"],
        "map": state["map"],
        "plotpoints": state.get("plotpoints", []),
        "scenes": state.get("scenes", {}),
        "characters": normalized_characters,
        "items": state.get("items", {}),
        "world_races": (state.get("world") or {}).get("races", {}),
        "world_beast_types": (state.get("world") or {}).get("beast_types", {}),
        "world_elements": (state.get("world") or {}).get("elements", {}),
        "world_element_relations": (state.get("world") or {}).get("element_relations", {}),
        "world_element_paths": (state.get("world") or {}).get("element_class_paths", {}),
        "world_element_summary": build_world_element_summary(state, limit=24),
        "race_codex_summary": build_race_codex_summary(state, limit=24),
        "beast_codex_summary": build_beast_codex_summary(state, limit=24),
        "npc_codex_summary": build_npc_codex_summary(state, limit=20),
        "npc_codex": (state.get("npc_codex") or {}) if len((state.get("npc_codex") or {})) <= 24 else {},
        "boards": campaign["boards"],
        "recent_turns": recent,
        "claims": campaign.get("claims", {}),
        "actor": actor,
        "action_type": action_type,
    }
    return json.dumps(packet, ensure_ascii=False)

def is_suspicious_story_text(text: str) -> bool:
    if not text:
        return True
    stripped = text.strip()
    if len(stripped) < 40:
        return True
    if stripped.endswith("\\"):
        return True
    if stripped.endswith(("„", '"', "'", "(", "[", "{", ":", ",", ";")):
        return True
    if stripped.count('"') % 2 == 1:
        return True
    if stripped.count("„") != stripped.count("“"):
        return True
    return False

def normalized_eval_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-zA-ZäöüÄÖÜß0-9 ]+", " ", str(text or "").lower())).strip()

def context_state_signature(state: Dict[str, Any]) -> str:
    serialized = json.dumps(state or {}, ensure_ascii=False, sort_keys=True, default=str)
    return hash_secret(serialized)

def strip_markdown_like(text: str) -> str:
    cleaned = str(text or "")
    cleaned = re.sub(r"^\s*#{1,6}\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.replace("**", "").replace("__", "").replace("`", "")
    cleaned = re.sub(r"^\s*[-*]\s+", "• ", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()

def parse_context_intent(question: str) -> Dict[str, str]:
    raw = str(question or "").strip()
    lowered = normalized_eval_text(raw)
    target = ""
    intent = "unknown"
    patterns = [
        ("define", r"(?:^|\b)(?:was ist|was bedeutet|erklaer mir|erklär mir|was ist nochmal)\s+(.+)$"),
        ("who", r"(?:^|\b)(?:wer ist|wer war)\s+(.+)$"),
        ("where", r"(?:^|\b)(?:wo ist|wo befindet sich|wo liegt)\s+(.+)$"),
    ]
    for detected_intent, pattern in patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match:
            intent = detected_intent
            target = match.group(1)
            break
    if not target:
        quoted = re.search(r"[\"“„']([^\"“”„']{2,120})[\"”„']", raw)
        if quoted:
            target = quoted.group(1)
            if intent == "unknown":
                intent = "define"
    if intent == "unknown":
        if any(marker in lowered for marker in ("zusammenfassung", "aktueller stand", "was bisher", "worum geht")):
            intent = "summary"
        elif any(marker in lowered for marker in ("vergleich", "unterschied", "vs ", "gegenüber")):
            intent = "compare"
    target = re.sub(r"\?$", "", str(target or "").strip()).strip(" .,:;!?")
    target = re.sub(r"^(?:ein(?:e|en|em|er)?|der|die|das)\s+", "", target, flags=re.IGNORECASE).strip()
    return {"intent": intent, "target": target}

def build_context_knowledge_index(campaign: Dict[str, Any], state: Dict[str, Any]) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    world_settings = (((state.get("world") or {}).get("settings") or {}))

    def add_entry(entry: Dict[str, Any]) -> None:
        normalized_aliases = []
        for alias in (entry.get("aliases") or []):
            cleaned = str(alias or "").strip()
            if cleaned:
                normalized_aliases.append(cleaned)
        source_rows = []
        for row in (entry.get("sources") or []):
            if not isinstance(row, dict):
                continue
            source_rows.append(
                {
                    "type": str(row.get("type") or "").strip(),
                    "id": str(row.get("id") or "").strip(),
                    "label": str(row.get("label") or "").strip(),
                }
            )
        facts = [str(fact).strip() for fact in (entry.get("facts") or []) if str(fact).strip()]
        title = str(entry.get("title") or "").strip()
        if not title:
            return
        entries.append(
            {
                "type": str(entry.get("type") or "unknown").strip() or "unknown",
                "id": str(entry.get("id") or "").strip(),
                "title": title,
                "aliases": list(dict.fromkeys(normalized_aliases + [title])),
                "facts": facts[:12],
                "sources": source_rows[:8],
            }
        )

    for slot_name in campaign_slots(campaign):
        character = ((state.get("characters") or {}).get(slot_name) or {})
        display_name = display_name_for_slot(campaign, slot_name)
        class_current = normalize_class_current(character.get("class_current"))
        if class_current:
            class_id = str(class_current.get("id") or class_current.get("name") or f"class_{slot_name}")
            add_entry(
                {
                    "type": "class",
                    "id": f"{slot_name}:{class_id}",
                    "title": str(class_current.get("name") or class_id),
                    "aliases": [class_id, class_current.get("name", ""), display_name],
                    "facts": [
                        f"Träger: {display_name}",
                        f"Rang: {class_current.get('rank', 'F')}",
                        f"Level: {class_current.get('level', 1)}/{class_current.get('level_max', 10)}",
                        f"Affinitäten: {', '.join(class_current.get('affinity_tags', [])) or 'Keine'}",
                        f"Beschreibung: {class_current.get('description', '') or 'Keine Beschreibung.'}",
                    ],
                    "sources": [{"type": "class", "id": f"{slot_name}:{class_id}", "label": f"Klasse von {display_name}"}],
                }
            )
        resource_name = resource_name_for_character(character, world_settings)
        for skill_id, skill_value in ((character.get("skills") or {}).items()):
            skill_state = normalize_dynamic_skill_state(
                skill_value,
                skill_id=skill_id,
                skill_name=(skill_value or {}).get("name", skill_id) if isinstance(skill_value, dict) else skill_id,
                resource_name=resource_name,
            )
            add_entry(
                {
                    "type": "skill",
                    "id": f"{slot_name}:{skill_state.get('id', skill_id)}",
                    "title": skill_state.get("name", skill_id),
                    "aliases": [skill_state.get("id", skill_id), skill_state.get("name", skill_id), display_name],
                    "facts": [
                        f"Träger: {display_name}",
                        f"Rang: {skill_state.get('rank', 'F')}",
                        f"Level: {skill_state.get('level', 1)}/{skill_state.get('level_max', 10)}",
                        f"Tags: {', '.join(skill_state.get('tags') or []) or 'Keine'}",
                        f"Beschreibung: {skill_state.get('description', '') or 'Keine Beschreibung.'}",
                    ],
                    "sources": [{"type": "skill", "id": f"{slot_name}:{skill_state.get('id', skill_id)}", "label": f"Skill von {display_name}"}],
                }
            )

    for npc_id, raw_npc in ((state.get("npc_codex") or {}).items()):
        npc = normalize_npc_entry(raw_npc, fallback_npc_id=str(npc_id))
        if not npc:
            continue
        scene_name = scene_name_from_state(state, npc.get("last_seen_scene_id", ""))
        add_entry(
            {
                "type": "npc",
                "id": npc.get("npc_id", str(npc_id)),
                "title": npc.get("name", str(npc_id)),
                "aliases": [npc.get("name", ""), npc.get("npc_id", ""), npc.get("role_hint", ""), npc.get("faction", "")],
                "facts": [
                    f"Rasse: {npc.get('race', 'Unbekannt')}",
                    f"Alter: {npc.get('age', 'Unbekannt')}",
                    f"Level: {npc.get('level', 1)}",
                    f"Ziel: {npc.get('goal', '') or 'Unbekannt'}",
                    f"Fraktion: {npc.get('faction', '') or 'Keine'}",
                    f"Status: {npc.get('status', 'active')}",
                    f"Zuletzt gesehen: {scene_name or 'Unbekannt'}",
                    f"Kurz-Backstory: {npc.get('backstory_short', '') or 'Keine'}",
                ],
                "sources": [{"type": "npc", "id": npc.get("npc_id", str(npc_id)), "label": f"NPC-Codex: {npc.get('name', str(npc_id))}"}],
            }
        )

    race_codex = ((state.get("codex") or {}).get("races") or {}) if isinstance(((state.get("codex") or {}).get("races") or {}), dict) else {}
    for race_id, race_profile in sorted_world_profiles(state, kind=CODEX_KIND_RACE):
        codex_entry = normalize_codex_entry_stable(race_codex.get(race_id), kind=CODEX_KIND_RACE)
        known_facts = codex_entry.get("known_facts") or []
        add_entry(
            {
                "type": "race",
                "id": race_id,
                "title": str((race_profile or {}).get("name") or race_id),
                "aliases": [race_id] + list((race_profile or {}).get("aliases") or []),
                "facts": known_facts if known_facts else [f"Wissensstand: {int(codex_entry.get('knowledge_level', 0) or 0)}/4"],
                "sources": [{"type": "race", "id": race_id, "label": f"Rassenkodex: {str((race_profile or {}).get('name') or race_id)}"}],
            }
        )

    beast_codex = ((state.get("codex") or {}).get("beasts") or {}) if isinstance(((state.get("codex") or {}).get("beasts") or {}), dict) else {}
    for beast_id, beast_profile in sorted_world_profiles(state, kind=CODEX_KIND_BEAST):
        codex_entry = normalize_codex_entry_stable(beast_codex.get(beast_id), kind=CODEX_KIND_BEAST)
        known_facts = codex_entry.get("known_facts") or []
        add_entry(
            {
                "type": "beast",
                "id": beast_id,
                "title": str((beast_profile or {}).get("name") or beast_id),
                "aliases": [beast_id] + list((beast_profile or {}).get("aliases") or []),
                "facts": known_facts if known_facts else [f"Wissensstand: {int(codex_entry.get('knowledge_level', 0) or 0)}/4"],
                "sources": [{"type": "beast", "id": beast_id, "label": f"Bestienkodex: {str((beast_profile or {}).get('name') or beast_id)}"}],
            }
        )

    for plotpoint in (state.get("plotpoints") or []):
        if not isinstance(plotpoint, dict):
            continue
        plot_id = str(plotpoint.get("id") or "").strip()
        title = str(plotpoint.get("title") or plot_id).strip()
        if not title:
            continue
        add_entry(
            {
                "type": "plotpoint",
                "id": plot_id,
                "title": title,
                "aliases": [plot_id, title, plotpoint.get("type", ""), plotpoint.get("owner", "")],
                "facts": [
                    f"Typ: {plotpoint.get('type', 'story')}",
                    f"Status: {plotpoint.get('status', 'active')}",
                    f"Owner: {plotpoint.get('owner') or 'Kein Owner'}",
                    f"Notizen: {plotpoint.get('notes', '') or 'Keine'}",
                    f"Requirements: {', '.join(plotpoint.get('requirements') or []) or 'Keine'}",
                ],
                "sources": [{"type": "plotpoint", "id": plot_id or title, "label": f"Plotpoint: {title}"}],
            }
        )

    for item_id, raw_item in ((state.get("items") or {}).items()):
        item = ensure_item_shape(item_id, raw_item if isinstance(raw_item, dict) else {})
        add_entry(
            {
                "type": "item",
                "id": item_id,
                "title": item.get("name", item_id),
                "aliases": [item_id, item.get("name", ""), item.get("slot", "")],
                "facts": [
                    f"Seltenheit: {item.get('rarity', 'common')}",
                    f"Slot: {item.get('slot', '') or 'Kein Slot'}",
                    f"Beschreibung: {item.get('description', '') or 'Keine Beschreibung.'}",
                    f"Tags: {', '.join(item.get('tags') or []) or 'Keine'}",
                ],
                "sources": [{"type": "item", "id": item_id, "label": f"Item: {item.get('name', item_id)}"}],
            }
        )

    for scene_id, scene in ((state.get("scenes") or {}).items()):
        if not isinstance(scene, dict):
            continue
        scene_name = str(scene.get("name") or scene_id).strip()
        add_entry(
            {
                "type": "scene",
                "id": scene_id,
                "title": scene_name,
                "aliases": [scene_id, scene_name],
                "facts": [
                    f"Gefahr: {scene.get('danger', 1)}",
                    f"Notizen: {scene.get('notes', '') or 'Keine'}",
                ],
                "sources": [{"type": "scene", "id": scene_id, "label": f"Ort: {scene_name}"}],
            }
        )
    for scene_id, node in (((state.get("map") or {}).get("nodes") or {}).items()):
        node_name = str((node or {}).get("name") or scene_id).strip()
        add_entry(
            {
                "type": "scene",
                "id": scene_id,
                "title": node_name,
                "aliases": [scene_id, node_name],
                "facts": [
                    f"Gefahr: {int((node or {}).get('danger', 1) or 1)}",
                    f"Typ: {str((node or {}).get('type') or 'location')}",
                    f"Entdeckt: {'Ja' if (node or {}).get('discovered', True) else 'Nein'}",
                ],
                "sources": [{"type": "scene", "id": scene_id, "label": f"Karte: {node_name}"}],
            }
        )

    for faction_entry in (campaign.get("boards", {}).get("world_info") or []):
        if not isinstance(faction_entry, dict):
            continue
        if str(faction_entry.get("category") or "").strip().lower() != "faction":
            continue
        faction_id = str(faction_entry.get("entry_id") or canonical_scene_id(str(faction_entry.get("title") or "faction"))).strip()
        title = str(faction_entry.get("title") or faction_id).strip()
        add_entry(
            {
                "type": "faction",
                "id": faction_id,
                "title": title,
                "aliases": [title, faction_id],
                "facts": [f"Beschreibung: {str(faction_entry.get('content') or '').strip() or 'Keine'}"],
                "sources": [{"type": "faction", "id": faction_id, "label": f"World Info: {title}"}],
            }
        )

    return entries

def resolve_context_target(index: List[Dict[str, Any]], target: str) -> Dict[str, Any]:
    normalized_target = normalize_npc_alias(target)
    if not normalized_target:
        return {"status": "not_in_canon", "entry": None, "confidence": "low", "matches": [], "suggestions": []}
    exact_matches: List[Dict[str, Any]] = []
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for entry in index:
        aliases = [normalize_npc_alias(alias) for alias in ([entry.get("title")] + list(entry.get("aliases") or []))]
        aliases = [alias for alias in aliases if alias]
        if normalized_target in aliases:
            exact_matches.append(entry)
            continue
        best = 0.0
        for alias in aliases:
            best = max(best, SequenceMatcher(None, normalized_target, alias).ratio())
        if best > 0:
            scored.append((best, entry))
    if len(exact_matches) == 1:
        return {"status": "found", "entry": exact_matches[0], "confidence": "high", "matches": exact_matches, "suggestions": []}
    if len(exact_matches) > 1:
        suggestions = [entry.get("title", "") for entry in exact_matches[:6] if entry.get("title")]
        return {"status": "ambiguous", "entry": None, "confidence": "medium", "matches": exact_matches, "suggestions": suggestions}
    scored.sort(key=lambda row: row[0], reverse=True)
    if scored and scored[0][0] >= 0.9:
        top_score = scored[0][0]
        close = [entry for score, entry in scored if abs(top_score - score) <= 0.02 and score >= 0.88]
        if len(close) == 1:
            confidence = "high" if top_score >= 0.96 else "medium"
            return {"status": "found", "entry": close[0], "confidence": confidence, "matches": [close[0]], "suggestions": []}
        suggestions = [entry.get("title", "") for entry in close[:6] if entry.get("title")]
        return {"status": "ambiguous", "entry": None, "confidence": "low", "matches": close, "suggestions": suggestions}
    suggestions = [entry.get("title", "") for score, entry in scored if score >= 0.62 and entry.get("title")][:6]
    return {"status": "not_in_canon", "entry": None, "confidence": "low", "matches": [], "suggestions": list(dict.fromkeys(suggestions))}

def build_context_result_payload(
    *,
    status: str,
    intent: str,
    target: str,
    confidence: str,
    entity_type: str,
    entity_id: str,
    title: str,
    explanation: str,
    facts: Optional[List[str]] = None,
    sources: Optional[List[Dict[str, str]]] = None,
    suggestions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "status": status if status in {"found", "not_in_canon", "ambiguous"} else "not_in_canon",
        "intent": intent if intent in {"define", "who", "where", "summary", "compare", "unknown"} else "unknown",
        "target": str(target or "").strip(),
        "confidence": confidence if confidence in {"high", "medium", "low"} else "low",
        "entity_type": str(entity_type or "unknown"),
        "entity_id": str(entity_id or ""),
        "title": str(title or "").strip(),
        "explanation": strip_markdown_like(explanation),
        "facts": [strip_markdown_like(fact) for fact in (facts or []) if str(fact or "").strip()],
        "sources": [
            {
                "type": str(entry.get("type") or "").strip(),
                "id": str(entry.get("id") or "").strip(),
                "label": strip_markdown_like(str(entry.get("label") or "").strip()),
            }
            for entry in (sources or [])
            if isinstance(entry, dict) and str(entry.get("type") or "").strip() and str(entry.get("id") or "").strip()
        ],
        "suggestions": [strip_markdown_like(suggestion) for suggestion in (suggestions or []) if str(suggestion or "").strip()],
    }

def deterministic_context_result_from_entry(intent: str, target: str, entry: Dict[str, Any], confidence: str) -> Dict[str, Any]:
    title = str(entry.get("title") or target or "Kanon-Eintrag").strip()
    facts = [str(fact).strip() for fact in (entry.get("facts") or []) if str(fact).strip()]
    if intent == "where":
        explanation = (
            f"Im aktuellen Kanon ist „{title}“ als relevanter Eintrag erfasst. "
            "Der letzte bekannte Ortsbezug steht in den gefundenen Fakten und Quellen."
        )
    elif intent == "who":
        explanation = (
            f"„{title}“ ist im aktuellen Kanon als Figur oder Referenz vorhanden. "
            "Hier sind die bestätigten Eckdaten aus dem Zustand."
        )
    else:
        explanation = (
            f"Im aktuellen Kanon bedeutet „{title}“ Folgendes. "
            "Die Antwort basiert auf den gespeicherten Zustandsdaten dieser Kampagne."
        )
    return build_context_result_payload(
        status="found",
        intent=intent,
        target=target,
        confidence=confidence,
        entity_type=str(entry.get("type") or "unknown"),
        entity_id=str(entry.get("id") or ""),
        title=title,
        explanation=explanation,
        facts=facts[:8],
        sources=entry.get("sources") or [],
        suggestions=[],
    )

def context_meta_drift_detected(result: Dict[str, Any]) -> bool:
    merged = normalized_eval_text(
        f"{result.get('title', '')}\n{result.get('explanation', '')}\n{' '.join(result.get('facts') or [])}"
    )
    return any(marker in merged for marker in CONTEXT_META_DRIFT_MARKERS)

def build_reduced_context_snippets(index: List[Dict[str, Any]], *, target: str = "", limit: int = 12) -> List[Dict[str, Any]]:
    normalized_target = normalize_npc_alias(target)
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for entry in index:
        base_score = 0.2
        if normalized_target:
            aliases = [normalize_npc_alias(alias) for alias in ([entry.get("title")] + list(entry.get("aliases") or []))]
            aliases = [alias for alias in aliases if alias]
            similarity = max((SequenceMatcher(None, normalized_target, alias).ratio() for alias in aliases), default=0.0)
            base_score += similarity
        if entry.get("type") in {"npc", "class", "skill", "plotpoint"}:
            base_score += 0.15
        scored.append((base_score, entry))
    scored.sort(key=lambda row: row[0], reverse=True)
    snippets: List[Dict[str, Any]] = []
    for _, entry in scored[: max(1, int(limit or 1))]:
        snippets.append(
            {
                "type": entry.get("type"),
                "id": entry.get("id"),
                "title": entry.get("title"),
                "facts": list(entry.get("facts") or [])[:4],
                "sources": list(entry.get("sources") or [])[:2],
            }
        )
    return snippets

def build_context_result_via_llm(question: str, intent: str, target: str, snippets: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    user_prompt = (
        "KONTEXTFRAGE:\n"
        + str(question or "")
        + "\n\nRETRIEVAL_SNIPPETS(JSON):\n"
        + json.dumps(snippets, ensure_ascii=False)
        + "\n\nANTWORTREGELN:\n"
        + "- Nutze ausschließlich Fakten aus RETRIEVAL_SNIPPETS.\n"
        + "- Wenn nicht genug Informationen vorliegen, status=not_in_canon oder ambiguous.\n"
        + "- Kein Markdown, kein Meta über Textanalyse."
    )
    try:
        payload = call_ollama_schema(
            CONTEXT_ASSISTANT_SYSTEM_PROMPT,
            user_prompt,
            CONTEXT_RESPONSE_SCHEMA,
            timeout=90,
            temperature=0.2,
        )
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    normalized_result = build_context_result_payload(
        status=str(payload.get("status") or "not_in_canon"),
        intent=str(payload.get("intent") or intent),
        target=str(payload.get("target") or target),
        confidence=str(payload.get("confidence") or "low"),
        entity_type=str(payload.get("entity_type") or "unknown"),
        entity_id=str(payload.get("entity_id") or ""),
        title=str(payload.get("title") or (target or "Kontext")),
        explanation=str(payload.get("explanation") or ""),
        facts=payload.get("facts") if isinstance(payload.get("facts"), list) else [],
        sources=payload.get("sources") if isinstance(payload.get("sources"), list) else [],
        suggestions=payload.get("suggestions") if isinstance(payload.get("suggestions"), list) else [],
    )
    if context_meta_drift_detected(normalized_result):
        return None
    return normalized_result

def extract_story_target_evidence(campaign: Dict[str, Any], target: str, *, max_hits: int = 6) -> Dict[str, Any]:
    normalized_target = normalize_npc_alias(target)
    if not normalized_target:
        return {"facts": [], "sources": []}
    token_set = {token for token in normalized_target.split() if len(token) >= 3}
    facts: List[str] = []
    sources: List[Dict[str, str]] = []
    seen_sentences: set[str] = set()
    turns = list(active_turns(campaign))[-24:]
    for turn in reversed(turns):
        turn_id = str(turn.get("turn_id") or "")
        turn_number = int(turn.get("turn_number") or 0)
        for field_name, label in (("gm_text_display", "GM"), ("input_text_display", "Spieler")):
            text_block = str(turn.get(field_name) or "")
            if not text_block:
                continue
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", text_block):
                clean_sentence = str(sentence or "").strip()
                if len(clean_sentence) < 12:
                    continue
                normalized_sentence = normalize_npc_alias(clean_sentence)
                if not normalized_sentence:
                    continue
                direct_hit = normalized_target in normalized_sentence
                token_hit = bool(token_set) and sum(1 for token in token_set if token in normalized_sentence) >= max(1, min(2, len(token_set)))
                if not direct_hit and not token_hit:
                    continue
                signature = normalized_sentence[:220]
                if signature in seen_sentences:
                    continue
                seen_sentences.add(signature)
                facts.append(clean_sentence)
                sources.append(
                    {
                        "type": "turn",
                        "id": turn_id or f"turn_{turn_number}",
                        "label": f"Turn {turn_number} ({label})",
                    }
                )
                if len(facts) >= max_hits:
                    return {"facts": facts, "sources": sources}
    return {"facts": facts, "sources": sources}

def context_result_to_answer_text(result: Dict[str, Any]) -> str:
    status = str(result.get("status") or "not_in_canon")
    title = str(result.get("title") or result.get("target") or "Kontext").strip() or "Kontext"
    explanation = strip_markdown_like(str(result.get("explanation") or "").strip())
    facts = [strip_markdown_like(str(entry or "").strip()) for entry in (result.get("facts") or []) if str(entry or "").strip()]
    suggestions = [strip_markdown_like(str(entry or "").strip()) for entry in (result.get("suggestions") or []) if str(entry or "").strip()]
    sources = [strip_markdown_like(str((entry or {}).get("label") or "").strip()) for entry in (result.get("sources") or []) if isinstance(entry, dict)]
    sources = [entry for entry in sources if entry]

    if status == "found":
        lines = [explanation or f"Im aktuellen Kanon ist „{title}“ eindeutig hinterlegt."]
        if facts:
            lines.append("Fakten: " + "; ".join(facts[:6]))
        if sources:
            lines.append("Gefunden in: " + ", ".join(sources[:4]))
        return "\n\n".join(lines).strip()

    if status == "ambiguous":
        lines = [f"Der Begriff „{title}“ ist mehrdeutig im aktuellen Kanon."]
        if suggestions:
            lines.append("Meintest du: " + ", ".join(suggestions[:6]))
        return "\n\n".join(lines).strip()

    lines = [f"Der Begriff „{title}“ ist im aktuellen Kanon nicht hinterlegt."]
    if suggestions:
        lines.append("Ähnliche Begriffe: " + ", ".join(suggestions[:6]))
    return "\n\n".join(lines).strip()

def clean_auto_ability_name(raw_name: str) -> str:
    name = str(raw_name or "").strip().strip(".,:;!?\"“”„' ")
    name = re.sub(r"^(?:die|der|das|ein|eine|einen)\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"^(?:sein(?:e|en|em|er)?|ihr(?:e|en|em|er)?|mein(?:e|en|em|er)?|dein(?:e|en|em|er)?)\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"^(?:alte|alter|altes|alten|neue|neuer|neues|neuen|frühere|fruehere|früheren|frueheren)\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+(?:und|aber|doch|wobei|wodurch|als|während)\b.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+(?:wieder|erneut|zurück|zurueck)$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+", " ", name).strip(" -")
    normalized = normalized_eval_text(name)
    if not name or normalized in ABILITY_UNLOCK_GENERIC_NAMES:
        return ""
    if normalized in UNIVERSAL_SKILL_LIKE_NAMES:
        return ""
    word_count = len(name.split())
    if word_count > 6 or len(name) < 3:
        return ""
    if not re.search(r"[A-Za-zÄÖÜäöüß]", name):
        return ""
    return name

def clean_auto_item_name(raw_name: str) -> str:
    name = str(raw_name or "").replace("\n", " ").strip().strip(".,:;!?\"“”„' ")
    name = re.sub(r"^\s*\d+[\.\)]\s*", "", name)
    name = re.sub(r"^(?:die|der|das|ein|eine|einen|einem)\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"^(?:mein(?:e|en|em|er)?|dein(?:e|en|em|er)?|sein(?:e|en|em|er)?|ihr(?:e|en|em|er)?)\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+aus\s+der\s+scheide\b.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+vor\s+(?:mich|ihn|sie|ihm|ihr|sich|uns|euch)\b.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+(?:und|aber|doch|wobei|wodurch|als|während)\b.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\([^)]{0,120}\)", "", name)
    lowered = f" {normalized_eval_text(name)} "
    for marker in ITEM_DETAIL_CLAUSE_MARKERS:
        idx = lowered.find(marker)
        if idx > 6:
            name = name[: idx - 1].strip()
            break
    name = re.sub(r"\s+", " ", name).strip(" -")
    normalized = normalized_eval_text(name)
    if not name or normalized in AUTO_ITEM_GENERIC_NAMES:
        return ""
    if len(name) < 3:
        return ""
    words = name.split()
    if len(words) > 7:
        name = " ".join(words[:7]).strip()
        normalized = normalized_eval_text(name)
    if not re.search(r"[A-Za-zÄÖÜäöüß]", name):
        return ""
    if normalized in AUTO_ITEM_GENERIC_NAMES:
        return ""
    return name[:80].strip(" ,-.")

def actor_relevant_story_sentences(story_text: str, actor_display: str) -> List[str]:
    actor_name = normalized_eval_text(actor_display)
    relevant: List[str] = []
    actor_subject_active = False
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", str(story_text or "")):
        sentence = sentence.strip()
        if not sentence:
            continue
        normalized_sentence = normalized_eval_text(sentence)
        starts_pronoun = normalized_sentence.startswith(("er ", "sie ", "es ", "ihn ", "ihm ", "ihr "))
        starts_first_person = normalized_sentence.startswith(
            ("ich ", "mich ", "mir ", "mein ", "meine ", "meinen ", "meinem ", "meiner ")
        )
        if starts_first_person:
            actor_subject_active = True
            relevant.append(sentence)
            continue
        if actor_name and sentence_mentions_actor_name(sentence, actor_display):
            actor_subject_active = True
            relevant.append(sentence)
            continue
        if starts_pronoun and actor_subject_active:
            relevant.append(sentence)
            continue
        if actor_subject_active and normalized_sentence.startswith(
            ("dann ", "danach ", "darauf ", "anschließend ", "anschliessend ", "nun ", "jetzt ")
        ):
            relevant.append(sentence)
            continue
        actor_subject_active = False
    return relevant

def infer_item_slot_from_text(item_name: str, sentence: str) -> str:
    lowered_name = normalized_eval_text(item_name)
    lowered_sentence = normalized_eval_text(sentence)
    if any(keyword in lowered_name for keyword in ITEM_OFFHAND_KEYWORDS):
        return "offhand"
    if any(keyword in lowered_name for keyword in ITEM_CHEST_KEYWORDS):
        return "chest"
    if any(keyword in lowered_name for keyword in ITEM_TRINKET_KEYWORDS):
        return "trinket"
    if any(keyword in lowered_name for keyword in ITEM_WEAPON_KEYWORDS):
        return "weapon"
    if any(keyword in lowered_sentence for keyword in ITEM_OFFHAND_KEYWORDS):
        return "offhand"
    if any(keyword in lowered_sentence for keyword in ITEM_CHEST_KEYWORDS):
        return "chest"
    if any(keyword in lowered_sentence for keyword in ITEM_TRINKET_KEYWORDS):
        return "trinket"
    if any(keyword in lowered_sentence for keyword in ITEM_WEAPON_KEYWORDS):
        return "weapon"
    if any(marker in lowered_sentence for marker in (" in der hand", " schwingt ", " zieht ", " fuehrt ", " führt ")):
        return "weapon"
    return ""

def build_auto_item_stub(item_name: str, sentence: str) -> Dict[str, Any]:
    lowered = normalized_eval_text(f"{item_name} {sentence}")
    slot = infer_item_slot_from_text(item_name, sentence)
    tags = ["story_auto", "auto_item"]
    weapon_profile: Dict[str, Any] = {}
    if slot == "weapon":
        tags.append("weapon")
        category = "ranged" if any(marker in lowered for marker in ("bogen", "armbrust")) else "melee"
        scaling_stat = "dex" if category == "ranged" else "str"
        if any(marker in lowered for marker in ("stab", "rune", "fokus", "orb")):
            scaling_stat = "int"
        weapon_profile = {"category": category, "scaling_stat": scaling_stat, "damage_min": 1, "damage_max": 3, "attack_bonus": 0}
    elif slot == "offhand":
        tags.append("offhand")
    elif slot == "chest":
        tags.append("armor")
    elif slot == "trinket":
        tags.append("trinket")
    return {"slot": slot, "tags": list(dict.fromkeys(tags)), "weapon_profile": weapon_profile}

def clean_creator_item_name(raw_name: str) -> str:
    name = summarize_creator_item_name(raw_name)
    name = str(name or "").strip().strip(".,:;!?\"“”„' ")
    name = re.sub(r"^(?:die|der|das|ein|eine|einen|einem)\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+", " ", name).strip(" -")
    if len(name) < 3:
        return ""
    return name[:140]

def item_id_from_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", normalized_eval_text(name)).strip("-")
    slug = slug[:36] or make_id("item")
    return f"item_{slug}"

def materialize_inventory_item(
    state: Dict[str, Any],
    character: Dict[str, Any],
    item_name: str,
    *,
    source_tag: str,
    item_id: Optional[str] = None,
) -> Optional[str]:
    clean_name = (
        clean_creator_item_name(item_name)
        if source_tag in {"signature_item", "earth_origin"}
        else clean_auto_item_name(item_name)
    )
    if not clean_name:
        return None
    items_db = state.setdefault("items", {})
    inventory = character.setdefault("inventory", {})
    inventory_items = inventory.setdefault("items", [])
    existing_ids = {entry.get("item_id") for entry in list_inventory_items(character)}
    known_names = {
        normalized_eval_text((items_db.get(existing_id, {}) or {}).get("name", ""))
        for existing_id in existing_ids
        if existing_id
    }
    normalized_name = normalized_eval_text(clean_name)
    if normalized_name in known_names:
        return None

    target_item_id = item_id or item_id_from_name(clean_name)
    suffix = 2
    while target_item_id in items_db and normalized_eval_text((items_db.get(target_item_id, {}) or {}).get("name", "")) != normalized_name:
        target_item_id = f"{item_id_from_name(clean_name)}-{suffix}"
        suffix += 1

    items_db[target_item_id] = ensure_item_shape(
        target_item_id,
        {
            "name": clean_name[0].upper() + clean_name[1:] if clean_name else clean_name,
            "rarity": "common",
            "slot": "",
            "weight": 1,
            "stackable": False,
            "max_stack": 1,
            "weapon_profile": {},
            "modifiers": [],
            "effects": [],
            "durability": {"current": 100, "max": 100},
            "cursed": False,
            "curse_text": "",
            "tags": [source_tag],
        },
    )
    if target_item_id not in existing_ids:
        inventory_items.append({"item_id": target_item_id, "stack": 1})
    return target_item_id

def normalize_creator_item_list(value: Any) -> List[str]:
    if isinstance(value, list):
        joined = "\n".join(str(entry or "") for entry in value if str(entry or "").strip())
        return parse_earth_items(joined)
    return parse_earth_items(str(value or ""))

def reconcile_creator_inventory_items(state: Dict[str, Any], character: Dict[str, Any]) -> None:
    items_db = state.setdefault("items", {})
    inventory = character.setdefault("inventory", {})
    inventory_items = inventory.setdefault("items", [])
    creator_item_ids = {
        entry.get("item_id")
        for entry in inventory_items
        if entry.get("item_id") and any(
            tag in {"earth_origin", "signature_item"}
            for tag in ((items_db.get(entry.get("item_id"), {}) or {}).get("tags") or [])
        )
    }
    if creator_item_ids:
        inventory["items"] = [entry for entry in inventory_items if entry.get("item_id") not in creator_item_ids]

    bio = character.setdefault("bio", {})
    bio["earth_items"] = normalize_creator_item_list(bio.get("earth_items", []))
    bio["signature_item"] = clean_creator_item_name(bio.get("signature_item", ""))

    materialize_inventory_item(state, character, bio.get("signature_item", ""), source_tag="signature_item")
    for earth_item in bio.get("earth_items", []) or []:
        materialize_inventory_item(state, character, earth_item, source_tag="earth_origin")

def infer_auto_skill_tags(text: str) -> List[str]:
    lowered = normalized_eval_text(text)
    tags: List[str] = []
    if any(marker in lowered for marker in ("magie", "zauber", "rune", "fluch", "aether", "mana")):
        tags.append("magie")
    if any(marker in lowered for marker in ("schatten", "dunkel")):
        tags.append("schatten")
    if any(marker in lowered for marker in ("feuer", "brand")):
        tags.append("feuer")
    if any(marker in lowered for marker in ("körper", "hauter", "ausdauer", "regeneration")):
        tags.append("körper")
    if any(marker in lowered for marker in ("sinn", "instinkt", "blick", "wahrnehm")):
        tags.append("sinn")
    if any(marker in lowered for marker in ("waffe", "klinge", "schwert", "kampf")):
        tags.append("kampf")
    return tags or ["allgemein"]

def infer_auto_class_tags(text: str) -> List[str]:
    lowered = normalized_eval_text(text)
    tags: List[str] = []
    if any(marker in lowered for marker in ("schatten", "nacht", "dunkel")):
        tags.append("schatten")
    if any(marker in lowered for marker in ("rune", "sigille", "glyph")):
        tags.append("rune")
    if any(marker in lowered for marker in ("heilig", "licht", "paladin")):
        tags.append("heilig")
    if any(marker in lowered for marker in ("klinge", "schwert", "krieger", "kämpfer", "kampf")):
        tags.append("kampf")
    if any(marker in lowered for marker in ("arkan", "magie", "zauber", "mana", "aether", "qi")):
        tags.append("magie")
    if any(marker in lowered for marker in ("blut", "opfer")):
        tags.append("blut")
    return list(dict.fromkeys(tags or ["allgemein"]))

def normalize_class_rank_text(value: str) -> str:
    text = normalized_eval_text(value).replace("-", " ")
    match = re.search(r"\b([fedcbas])\s*rang\b", text) or re.search(r"\b([fedcbas])\b", text)
    if not match:
        return "F"
    return str(match.group(1) or "F").upper()

def clean_auto_class_name(name: str) -> str:
    text = str(name or "").strip(" .,:;!?\"“”„'()[]{}")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s*\(([A-FS])\s*-?\s*Rang\)\s*$", "", text, flags=re.IGNORECASE).strip()
    if text.startswith("des "):
        text = text[4:].strip()
    if text.startswith("der "):
        text = text[4:].strip()
    if text.startswith("des "):
        text = text[4:].strip()
    if len(text) > 4 and text.endswith("s") and not text.endswith(("ss", "us", "is")):
        text = text[:-1]
    return text.strip()

def extract_auto_class_change(text: str, actor_display: str) -> Optional[Dict[str, Any]]:
    content = str(text or "").strip()
    if not content:
        return None
    actor_name = re.escape(actor_display)
    subject_pattern = rf"(?:\b{actor_name}\b|\b(?:er|sie)\b)"
    class_name_pattern = r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9'’\-]+(?:\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9'’\-]+){0,3})"
    rank_pattern = r"(?:\s*\(([A-FS])\s*-?\s*Rang\))?"
    patterns = [
        rf"{subject_pattern}[^.!?\n]*?\bwird(?:\s+wie\s+einst)?(?:\s+wieder)?\s+zur Klasse des\s+{class_name_pattern}{rank_pattern}",
        rf"{subject_pattern}[^.!?\n]*?\bwird(?:\s+wie\s+einst)?(?:\s+wieder)?\s+zum\s+{class_name_pattern}{rank_pattern}",
        rf"{subject_pattern}[^.!?\n]*?\bist jetzt(?:\s+wieder)?\s+(?:ein|eine)\s+{class_name_pattern}{rank_pattern}",
        rf"{subject_pattern}[^.!?\n]*?\berlangt die Klasse\s+{class_name_pattern}{rank_pattern}",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        class_name = clean_auto_class_name(match.group(1) or "")
        if not class_name:
            continue
        rank = normalize_class_rank_text(match.group(2) or "")
        class_id = f"class_{re.sub(r'[^a-z0-9]+', '_', normalized_eval_text(class_name)).strip('_') or 'unknown'}"
        return {
            "id": class_id,
            "name": class_name,
            "rank": rank,
            "level": 1,
            "level_max": 10,
            "xp": 0,
            "xp_next": 100,
            "affinity_tags": infer_auto_class_tags(class_name + " " + content),
            "description": first_sentences(content, 2)[:220],
            "ascension": {
                "status": "none",
                "quest_id": None,
                "requirements": [],
                "result_hint": None,
            },
        }
    return None

def extract_auto_learned_abilities(story_text: str, actor_display: str) -> List[Dict[str, Any]]:
    actor_name = normalized_eval_text(actor_display)
    candidates: List[Dict[str, Any]] = []
    seen = set()

    def add_candidate(name: str, sentence: str) -> bool:
        normalized_name = normalized_eval_text(name)
        if not name or normalized_name in seen:
            return False
        seen.add(normalized_name)
        candidates.append(
            {
                "name": name,
                "description": sentence[:220].strip(),
                "type": "passive" if normalized_name in UNIVERSAL_SKILL_LIKE_NAMES else "active",
                "tags": list(dict.fromkeys(["story_auto", "auto_unlock", *infer_auto_skill_tags(sentence)])),
            }
        )
        return len(candidates) >= 2

    sentence_parts = re.split(r"(?<=[.!?])\s+|\n+", str(story_text or ""))
    for sentence in sentence_parts:
        sentence = sentence.strip()
        if not sentence:
            continue
        normalized_sentence = normalized_eval_text(sentence)
        if actor_name and not sentence_mentions_actor_name(sentence, actor_display) and not normalized_sentence.startswith(("er ", "sie ", "es ")):
            continue
        if not any(
            cue in normalized_sentence
            for cue in (
                "erlernt",
                "erlent",
                "wiedererlernt",
                "lernt",
                "meistert",
                "beherrscht",
                "schaltet",
                "erhält",
                "entwickelt",
                "entfesselt",
                "erweckt",
                "erwacht",
                "reaktiviert",
                "kann wieder",
                "wieder in sich",
                "manifestiert",
                "entsteht",
                "hervorgeht",
                "formt sich",
            )
        ):
            continue
        direct_magic_match = re.search(r"\b([A-ZÄÖÜa-zäöüß][A-Za-zÄÖÜäöüß\-]{2,40}magie)\b", sentence, flags=re.IGNORECASE)
        if direct_magic_match:
            for magic_name in split_extracted_skill_names(direct_magic_match.group(1)):
                if add_candidate(magic_name, sentence):
                    return candidates
        for explicit_match in re.findall(
            r"(?:technik|zauber|ritual|kunst|fähigkeit|faehigkeit)\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9\- ]{2,60})",
            sentence,
            flags=re.IGNORECASE,
        ):
            for name in split_extracted_skill_names(explicit_match):
                if add_candidate(name, sentence):
                    return candidates
        for emergent_match in re.findall(
            r"(?:technik|rittertechnik|kerntechnik|kunst|haltung|form)\s*(?:[–—:-]\s*|entsteht\s*(?:als|zu|wie)?\s*|wird\s*(?:zu|als)\s*)[„\"']?([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9\- ]{2,60})[\"”']?",
            sentence,
            flags=re.IGNORECASE,
        ):
            for name in split_extracted_skill_names(emergent_match):
                if add_candidate(name, sentence):
                    return candidates
        for quoted_match in re.findall(r"[„\"']([^\"“”']{3,60})[\"”']", sentence):
            if not any(keyword in normalized_sentence for keyword in ("technik", "rittertechnik", "kerntechnik", "kunst", "haltung")):
                continue
            for name in split_extracted_skill_names(quoted_match):
                if add_candidate(name, sentence):
                    return candidates
        for pattern in ABILITY_UNLOCK_TRIGGER_PATTERNS:
            for match in pattern.findall(sentence):
                for name in split_extracted_skill_names(match):
                    if add_candidate(name, sentence):
                        return candidates
    filtered: List[Dict[str, Any]] = []
    for candidate in candidates:
        candidate_norm = normalized_eval_text(candidate.get("name", ""))
        if any(
            candidate_norm
            and candidate_norm != normalized_eval_text(other.get("name", ""))
            and normalized_eval_text(other.get("name", "")).startswith(candidate_norm)
            for other in candidates
        ):
            continue
        filtered.append(candidate)
    return filtered

def extract_auto_story_item_events(story_text: str, actor_display: str) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    by_name: Dict[str, Dict[str, Any]] = {}
    for sentence in actor_relevant_story_sentences(story_text, actor_display):
        for pattern in AUTO_ITEM_ACQUIRE_PATTERNS:
            for match in pattern.findall(sentence):
                item_name = clean_auto_item_name(match)
                normalized_name = normalized_eval_text(item_name)
                if not item_name or not normalized_name:
                    continue
                if normalized_name not in by_name:
                    event = {"name": item_name, "mode": "acquire", "sentence": sentence}
                    by_name[normalized_name] = event
                    events.append(event)
                if len(events) >= 3:
                    return events
        for pattern in AUTO_ITEM_EQUIP_PATTERNS:
            for match in pattern.findall(sentence):
                item_name = clean_auto_item_name(match)
                normalized_name = normalized_eval_text(item_name)
                if not item_name or not normalized_name:
                    continue
                if normalized_name in by_name:
                    by_name[normalized_name]["mode"] = "equip"
                    by_name[normalized_name]["sentence"] = sentence
                    continue
                event = {"name": item_name, "mode": "equip", "sentence": sentence}
                by_name[normalized_name] = event
                events.append(event)
                if len(events) >= 3:
                    return events
    return events

def extract_auto_story_items(story_text: str, actor_display: str) -> List[str]:
    return [event.get("name", "") for event in extract_auto_story_item_events(story_text, actor_display) if event.get("name")]

def story_sentences_for_actor(story_text: str, actor_display: str) -> List[str]:
    actor_name = normalized_eval_text(actor_display)
    relevant: List[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", str(story_text or "")):
        sentence = sentence.strip()
        if not sentence:
            continue
        normalized_sentence = normalized_eval_text(sentence)
        if sentence_mentions_actor_name(sentence, actor_display):
            relevant.append(sentence)
            continue
        if normalized_sentence.startswith(("er ", "sie ", "es ")):
            relevant.append(sentence)
    return relevant

def build_turn_journal_notes(
    campaign: Dict[str, Any],
    actor: str,
    story_text: str,
    *,
    seed_text: str = "",
) -> List[Dict[str, Any]]:
    actor_display = display_name_for_slot(campaign, actor)
    notes: List[Dict[str, Any]] = []
    seen = set()
    turn_number = int((campaign.get("state", {}).get("meta", {}) or {}).get("turn", 0) or 0) + 1
    source_texts = [str(story_text or "").strip()]
    if seed_text:
        source_texts.append(str(seed_text or "").strip())

    for source_text in source_texts:
        if not source_text:
            continue
        relevant_sentences = story_sentences_for_actor(source_text, actor_display)[:5]
        for sentence in relevant_sentences:
            normalized_sentence = normalized_eval_text(sentence)
            if not normalized_sentence:
                continue
            if any(cue in normalized_sentence for cue in STORY_ACTION_CUES):
                text = sentence[:240].strip()
                key = ("action", normalized_eval_text(text))
                if key not in seen:
                    seen.add(key)
                    notes.append(
                        {
                            "id": make_id("journal"),
                            "kind": "action",
                            "turn_number": turn_number,
                            "text": f"Handlung: {text}",
                        }
                    )
                    break

        learned_names = [entry.get("name", "") for entry in extract_auto_learned_abilities(source_text, actor_display)]
        if learned_names:
            text = "Lernen: " + ", ".join(dict.fromkeys([name for name in learned_names if name]))
            key = ("learn", normalized_eval_text(text))
            if key not in seen:
                seen.add(key)
                notes.append(
                    {
                        "id": make_id("journal"),
                        "kind": "learning",
                        "turn_number": turn_number,
                        "text": text,
                    }
                )
        else:
            for sentence in story_sentences_for_actor(source_text, actor_display):
                normalized_sentence = normalized_eval_text(sentence)
                if any(cue in normalized_sentence for cue in STORY_LEARN_CUES):
                    text = sentence[:240].strip()
                    key = ("learn", normalized_eval_text(text))
                    if key not in seen:
                        seen.add(key)
                        notes.append(
                            {
                                "id": make_id("journal"),
                                "kind": "learning",
                                "turn_number": turn_number,
                                "text": f"Lernen: {text}",
                            }
                        )
                    break

        for sentence in story_sentences_for_actor(source_text, actor_display):
            normalized_sentence = normalized_eval_text(sentence)
            if any(cue in normalized_sentence for cue in STORY_EXPLORE_CUES):
                text = sentence[:240].strip()
                key = ("explore", normalized_eval_text(text))
                if key not in seen:
                    seen.add(key)
                    notes.append(
                        {
                            "id": make_id("journal"),
                            "kind": "exploration",
                            "turn_number": turn_number,
                            "text": f"Erkundung: {text}",
                        }
                    )
                break
    return notes[:4]

def inject_turn_story_journal(
    campaign: Dict[str, Any],
    working_state: Dict[str, Any],
    actor: str,
    story_text: str,
    patch: Dict[str, Any],
    *,
    seed_text: str = "",
) -> Dict[str, Any]:
    if actor not in (working_state.get("characters") or {}):
        return patch
    notes = build_turn_journal_notes(campaign, actor, story_text, seed_text=seed_text)
    if not notes:
        return patch
    target_patch = patch.setdefault("characters", {}).setdefault(actor, {})
    journal_add = target_patch.setdefault("journal_add", {})
    journal_add.setdefault("notes", [])
    existing = {
        normalized_eval_text((entry or {}).get("text", ""))
        for entry in (journal_add.get("notes") or [])
        if isinstance(entry, dict)
    }
    for entry in notes:
        normalized_text = normalized_eval_text(entry.get("text", ""))
        if not normalized_text or normalized_text in existing:
            continue
        existing.add(normalized_text)
        journal_add["notes"].append(entry)
    return patch

def inject_story_unlock_abilities(
    campaign: Dict[str, Any],
    working_state: Dict[str, Any],
    actor: str,
    story_text: str,
    patch: Dict[str, Any],
    *,
    seed_text: str = "",
) -> Dict[str, Any]:
    if actor not in (working_state.get("characters") or {}):
        return patch
    actor_display = display_name_for_slot(campaign, actor)
    candidates = extract_auto_learned_abilities(story_text, actor_display)
    if seed_text:
        known = {normalized_eval_text(entry.get("name", "")) for entry in candidates}
        for candidate in extract_auto_learned_abilities(seed_text, actor_display):
            if normalized_eval_text(candidate.get("name", "")) not in known:
                candidates.append(candidate)
                known.add(normalized_eval_text(candidate.get("name", "")))
    if not candidates:
        return patch

    character = (working_state.get("characters", {}).get(actor, {}) or {})
    resource_name = resource_name_for_character(character, ((working_state.get("world") or {}).get("settings") or {}))
    existing_names = {
        normalized_eval_text((entry or {}).get("name", ""))
        for entry in ((character.get("skills") or {}).values())
        if isinstance(entry, dict) and entry.get("name")
    }
    target_patch = patch.setdefault("characters", {}).setdefault(actor, {})
    existing_names.update(
        normalized_eval_text((skill or {}).get("name", ""))
        for skill in ((target_patch.get("skills_set") or {}).values())
        if isinstance(skill, dict) and skill.get("name")
    )
    target_patch.setdefault("skills_set", {})

    for candidate in candidates:
        normalized_name = normalized_eval_text(candidate["name"])
        if not normalized_name or normalized_name in existing_names:
            continue
        existing_names.add(normalized_name)
        skill_id = skill_id_from_name(candidate["name"])
        target_patch["skills_set"][skill_id] = normalize_dynamic_skill_state(
            {
                "id": skill_id,
                "name": candidate["name"],
                "rank": "F",
                "level": 1,
                "level_max": 10,
                "tags": candidate["tags"],
                "description": candidate["description"] or f"{actor_display} hat {candidate['name']} im Abenteuer erlernt.",
                "cost": {"resource": resource_name, "amount": 1} if "magie" in candidate["tags"] else None,
                "price": None,
                "cooldown_turns": None,
                "unlocked_from": "Story",
                "synergy_notes": None,
            },
            resource_name=resource_name,
        )
    return patch

def materialize_character_ability(
    character: Dict[str, Any],
    slot_name: str,
    ability_name: str,
    *,
    description: str,
    ability_type: str = "active",
    source: str = "story_auto",
) -> bool:
    clean_name = clean_auto_ability_name(ability_name)
    if not clean_name:
        return False
    resource_name = resource_name_for_character(character)
    existing_names = {
        normalized_eval_text((skill or {}).get("name", ""))
        for skill in ((character.get("skills") or {}).values())
        if isinstance(skill, dict)
    }
    if normalized_eval_text(clean_name) in existing_names:
        return False
    skill_id = skill_id_from_name(clean_name)
    character.setdefault("skills", {})[skill_id] = normalize_dynamic_skill_state(
        {
            "id": skill_id,
            "name": clean_name,
            "rank": "F",
            "level": 1,
            "level_max": 10,
            "tags": list(dict.fromkeys(["story_auto", "auto_unlock", *(["magie"] if ability_type == "active" else [])])),
            "description": (description or f"{clean_name} wurde in der Geschichte freigeschaltet.")[:220],
            "cost": {"resource": resource_name, "amount": 1} if ability_type == "active" else None,
            "price": None,
            "cooldown_turns": None,
            "unlocked_from": source or "Story",
            "synergy_notes": None,
        },
        resource_name=resource_name,
        unlocked_from=source or "Story",
    )
    return True

def inject_story_items(
    campaign: Dict[str, Any],
    working_state: Dict[str, Any],
    actor: str,
    story_text: str,
    patch: Dict[str, Any],
) -> Dict[str, Any]:
    if actor not in (working_state.get("characters") or {}):
        return patch
    actor_display = display_name_for_slot(campaign, actor)
    events = extract_auto_story_item_events(story_text, actor_display)
    if not events:
        return patch

    items_new = patch.setdefault("items_new", {})
    target_patch = patch.setdefault("characters", {}).setdefault(actor, {})
    target_patch.setdefault("inventory_add", [])
    target_patch.setdefault("equipment_set", {})
    state_items = working_state.get("items", {}) or {}
    character = (working_state.get("characters", {}) or {}).get(actor, {})
    existing_ids = {entry.get("item_id") for entry in list_inventory_items(character)} | set(iter_equipped_item_ids(character))
    existing_names = {
        normalized_eval_text((state_items.get(item_id, {}) or {}).get("name", ""))
        for item_id in existing_ids
        if item_id
    }
    existing_names.update(
        normalized_eval_text((item or {}).get("name", ""))
        for item in items_new.values()
        if isinstance(item, dict) and item.get("name")
    )

    for event in events:
        item_name = str(event.get("name") or "").strip()
        if not item_name:
            continue
        normalized_name = normalized_eval_text(item_name)
        if not normalized_name or normalized_name in existing_names:
            existing_item_id = next(
                (
                    item_id
                    for item_id, item in {**state_items, **items_new}.items()
                    if normalized_eval_text((item or {}).get("name", "")) == normalized_name
                ),
                "",
            )
            if existing_item_id and str(event.get("mode") or "") == "equip":
                item_stub = build_auto_item_stub(item_name, str(event.get("sentence") or ""))
                equip_slot = item_stub.get("slot") or "weapon"
                target_patch["equipment_set"].setdefault(equip_slot, existing_item_id)
            continue
        existing_names.add(normalized_name)
        item_id = item_id_from_name(item_name)
        suffix = 2
        while item_id in state_items or item_id in items_new:
            known = state_items.get(item_id) or items_new.get(item_id) or {}
            if normalized_eval_text(known.get("name", "")) == normalized_name:
                break
            item_id = f"{item_id_from_name(item_name)}-{suffix}"
            suffix += 1
        item_stub = build_auto_item_stub(item_name, str(event.get("sentence") or ""))
        items_new[item_id] = ensure_item_shape(
            item_id,
            {
                "name": item_name[0].upper() + item_name[1:] if item_name else item_name,
                "rarity": "common",
                "slot": item_stub.get("slot", ""),
                "weight": 1,
                "stackable": False,
                "max_stack": 1,
                "weapon_profile": item_stub.get("weapon_profile", {}),
                "modifiers": [],
                "effects": [],
                "durability": {"current": 100, "max": 100},
                "cursed": False,
                "curse_text": "",
                "tags": item_stub.get("tags", ["story_auto", "auto_item"]),
            },
        )
        if item_id not in target_patch["inventory_add"]:
            target_patch["inventory_add"].append(item_id)
        if str(event.get("mode") or "") == "equip":
            equip_slot = item_stub.get("slot") or "weapon"
            target_patch["equipment_set"].setdefault(equip_slot, item_id)
    if not target_patch.get("equipment_set"):
        target_patch.pop("equipment_set", None)
    return patch

def inject_story_injuries(
    campaign: Dict[str, Any],
    working_state: Dict[str, Any],
    actor: str,
    story_text: str,
    patch: Dict[str, Any],
    *,
    seed_text: str = "",
) -> Dict[str, Any]:
    if actor not in (working_state.get("characters") or {}):
        return patch
    actor_display = display_name_for_slot(campaign, actor)
    candidates = extract_auto_story_injuries(story_text, actor_display)
    if seed_text:
        known = {normalized_eval_text(entry.get("title", "")) for entry in candidates}
        for candidate in extract_auto_story_injuries(seed_text, actor_display):
            normalized_title = normalized_eval_text(candidate.get("title", ""))
            if normalized_title and normalized_title not in known:
                known.add(normalized_title)
                candidates.append(candidate)
    if not candidates:
        return patch
    character = (working_state.get("characters", {}).get(actor) or {})
    existing_titles = {
        normalized_eval_text((entry or {}).get("title", ""))
        for entry in (character.get("injuries") or [])
        if isinstance(entry, dict)
    }
    target_patch = patch.setdefault("characters", {}).setdefault(actor, {})
    target_patch.setdefault("injuries_add", [])
    existing_titles.update(
        normalized_eval_text((entry or {}).get("title", ""))
        for entry in (target_patch.get("injuries_add") or [])
        if isinstance(entry, dict)
    )
    next_turn = int((working_state.get("meta", {}) or {}).get("turn", 0) or 0)
    for candidate in candidates:
        normalized_title = normalized_eval_text(candidate.get("title", ""))
        if not normalized_title or normalized_title in existing_titles:
            continue
        existing_titles.add(normalized_title)
        injury_payload = deep_copy(candidate)
        injury_payload["created_turn"] = next_turn
        target_patch["injuries_add"].append(injury_payload)
    return patch

def materialize_story_items_from_turn_history(campaign: Dict[str, Any]) -> None:
    state = campaign.get("state", {}) or {}
    characters = state.get("characters", {}) or {}
    if not characters:
        return
    recent_turns = active_turns(campaign)[-12:]
    for turn in recent_turns:
        slot_name = turn.get("actor")
        if slot_name not in characters:
            continue
        character = characters.get(slot_name) or {}
        actor_display = display_name_for_slot(campaign, slot_name)
        for source_text in (
            turn.get("gm_text_display", ""),
            turn.get("input_text_display", "") if turn.get("action_type") in {"story", "canon"} else "",
        ):
            for event in extract_auto_story_item_events(source_text, actor_display):
                item_id = materialize_inventory_item(state, character, event.get("name", ""), source_tag="story_auto")
                if not item_id:
                    continue
                if str(event.get("mode") or "") != "equip":
                    continue
                item_stub = build_auto_item_stub(str(event.get("name") or ""), str(event.get("sentence") or ""))
                equip_slot = item_stub.get("slot") or "weapon"
                character.setdefault("equipment", {})[equip_slot] = item_id

def materialize_story_abilities_from_turn_history(campaign: Dict[str, Any]) -> None:
    state = campaign.get("state", {}) or {}
    characters = state.get("characters", {}) or {}
    if not characters:
        return
    recent_turns = active_turns(campaign)[-12:]
    for turn in recent_turns:
        slot_name = turn.get("actor")
        if slot_name not in characters:
            continue
        character = characters[slot_name]
        actor_display = display_name_for_slot(campaign, slot_name)
        seen = set()
        for source_text in (
            turn.get("gm_text_display", ""),
            turn.get("input_text_display", "") if turn.get("action_type") == "story" else "",
            turn.get("input_text_raw", "") if turn.get("action_type") == "story" else "",
        ):
            for candidate in extract_auto_learned_abilities(source_text, actor_display):
                normalized_name = normalized_eval_text(candidate.get("name", ""))
                if not normalized_name or normalized_name in seen:
                    continue
                seen.add(normalized_name)
                materialize_character_ability(
                    character,
                    slot_name,
                    candidate.get("name", ""),
                    description=candidate.get("description", ""),
                    ability_type=candidate.get("type", "active"),
                    source="story_auto_history",
                )

def run_legacy_normalize_backfill(campaign: Dict[str, Any]) -> None:
    """Optional legacy heuristic backfill path. Disabled by default."""
    materialize_story_items_from_turn_history(campaign)
    materialize_story_abilities_from_turn_history(campaign)
    reconcile_scene_ids_with_story(campaign)

def apply_world_time_advance(state: Dict[str, Any], delta_days: int, delta_time_of_day: Optional[str] = None) -> None:
    state.setdefault("meta", {})
    world_time = normalize_world_time(state["meta"])
    world_time["absolute_day"] = max(1, int(world_time.get("absolute_day", 1) or 1) + int(delta_days or 0))
    if delta_time_of_day:
        world_time["time_of_day"] = str(delta_time_of_day)
    world_time = normalize_world_time({"world_time": world_time})
    state["meta"]["world_time"] = world_time
    state.setdefault("world", {})
    state["world"]["day"] = world_time["day"]
    state["world"]["time"] = world_time["time_of_day"]
    state["world"]["weather"] = world_time["weather"]

def log_board_revision(
    campaign: Dict[str, Any],
    *,
    board: str,
    op: str,
    updated_by: Optional[str],
    previous: Any,
    current: Any,
    item_id: Optional[str] = None,
) -> None:
    campaign.setdefault("board_revisions", []).append(
        {
            "revision_id": make_id("boardrev"),
            "board": board,
            "op": op,
            "item_id": item_id,
            "updated_by": updated_by,
            "updated_at": utc_now(),
            "previous": previous,
            "current": current,
        }
    )

def intro_state(campaign: Dict[str, Any]) -> Dict[str, Any]:
    return campaign.setdefault("state", {}).setdefault("meta", {}).setdefault("intro_state", default_intro_state())

def can_start_adventure(campaign: Dict[str, Any]) -> bool:
    if not campaign["setup"]["world"].get("completed"):
        return False
    required_slots = expected_setup_slots(campaign)
    setup_chars = (campaign.get("setup", {}).get("characters") or {})
    claims = campaign.get("claims", {}) or {}
    if not required_slots:
        return False
    for slot_name in required_slots:
        if not claims.get(slot_name):
            return False
        if not (setup_chars.get(slot_name) or {}).get("completed"):
            return False
    return True

def try_generate_adventure_intro(campaign: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    normalize_campaign(campaign)
    intro = intro_state(campaign)
    if active_turns(campaign):
        intro["status"] = "generated"
        if not intro.get("generated_turn_id"):
            intro["generated_turn_id"] = active_turns(campaign)[0]["turn_id"]
        intro["last_error"] = ""
        return None
    if not can_start_adventure(campaign):
        return None

    completed_slots = active_party(campaign)
    primary_actor = completed_slots[0]
    names = [display_name_for_slot(campaign, slot_name) for slot_name in completed_slots]
    intro["status"] = "pending"
    intro["last_attempt_at"] = utc_now()
    intro["last_error"] = ""
    try:
        turn = create_turn_record(
            campaign=campaign,
            actor=primary_actor,
            player_id=campaign["claims"].get(primary_actor),
            action_type="story",
            content=(
                "Das Welt-Setup und die Charaktererstellung sind abgeschlossen. "
                f"Die aktiven Spielerfiguren dieses Runs sind: {', '.join(names)}. "
                "Eröffne jetzt die Kampagne filmisch auf Basis des Setups, der aktiven Charaktere und des Worldbuildings. "
                "Nutze ausschließlich diese aktive Party, setze die erste konkrete Szene und führe ohne ungebaute Slots in die Geschichte."
            ),
        )
    except HTTPException as exc:
        intro["status"] = "failed"
        intro["last_error"] = str(exc.detail)
        return None
    except Exception as exc:
        intro["status"] = "failed"
        intro["last_error"] = str(exc)
        return None
    intro["status"] = "generated"
    intro["generated_turn_id"] = turn["turn_id"]
    intro["last_error"] = ""
    return turn

def maybe_start_adventure(campaign: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not campaign["setup"]["world"].get("completed"):
        campaign["state"]["meta"]["phase"] = "world_setup"
        return None
    if not can_start_adventure(campaign):
        campaign["state"]["meta"]["phase"] = "character_setup_open"
        return None
    campaign["state"]["meta"]["phase"] = "ready_to_start"
    turn = try_generate_adventure_intro(campaign)
    if active_turns(campaign):
        campaign["state"]["meta"]["phase"] = "active"
    return turn

def new_player(display_name: str) -> Dict[str, str]:
    return {
        "player_id": make_id("player"),
        "player_token": secrets.token_urlsafe(24),
        "display_name": display_name.strip(),
    }

def create_campaign_record(
    title: str,
    display_name: str,
    *,
    legacy_state: Optional[Dict[str, Any]] = None,
    imported_turns: Optional[List[Dict[str, Any]]] = None,
    legacy_flag: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    identity = new_player(display_name or "Host")
    join_code = make_join_code()
    now = utc_now()
    state = deep_copy(legacy_state if legacy_state is not None else INITIAL_STATE)
    state.setdefault("characters", {})
    campaign_id = make_id("camp")
    campaign = {
        "campaign_meta": {
            "campaign_id": campaign_id,
            "title": title.strip() or "Neue Aelunor-Kampagne",
            "join_code_hash": hash_secret(join_code),
            "host_player_id": identity["player_id"],
            "created_at": now,
            "updated_at": now,
            "status": "active",
        },
        "players": {
            identity["player_id"]: {
                "display_name": identity["display_name"],
                "player_token_hash": hash_secret(identity["player_token"]),
                "joined_at": now,
                "last_seen_at": now,
            }
        },
        "claims": {},
        "state": state,
        "turns": imported_turns or [],
        "boards": default_boards(identity["player_id"]),
        "setup": default_setup(),
        "board_revisions": [],
        "legacy_migration": legacy_flag,
    }
    campaign.setdefault("state", {}).setdefault("meta", {})["phase"] = "lobby"
    normalize_campaign(campaign)
    first_world_qid = current_question_id(campaign["setup"]["world"])
    if first_world_qid:
        ensure_question_ai_copy(campaign, setup_type="world", question_id=first_world_qid)
    remember_recent_story(campaign)
    rebuild_memory_summary(campaign)
    save_campaign(campaign)
    return {
        "campaign": campaign,
        "join_code": join_code,
        "player_id": identity["player_id"],
        "player_token": identity["player_token"],
    }

def ensure_campaign_storage() -> None:
    ensure_data_dirs()
    if list_campaign_ids():
        return
    if not os.path.exists(LEGACY_STATE_PATH):
        return
    legacy_state = load_json(LEGACY_STATE_PATH)
    now = utc_now()
    imported_turns = []
    for index, story in enumerate(legacy_state.get("recent_story", []), start=1):
        snapshot = deep_copy(legacy_state)
        imported_turns.append(
            {
                "turn_id": make_id("turn"),
                "turn_number": index,
                "status": "active",
                "actor": "SYSTEM",
                "player_id": None,
                "action_type": "story",
                "input_text_raw": "Importierte Story",
                "input_text_display": "Importierte Story",
                "gm_text_raw": story,
                "gm_text_display": story,
                "requests": [],
                "patch": blank_patch(),
                "state_before": snapshot,
                "state_after": snapshot,
                "retry_of_turn_id": None,
                "edited_at": None,
                "created_at": now,
                "updated_at": now,
                "edit_history": [],
                "prompt_payload": {"imported": True},
            }
        )
    create_campaign_record(
        "Legacy Campaign",
        "Legacy Host",
        legacy_state=legacy_state,
        imported_turns=imported_turns,
        legacy_flag={"source": "state.json", "migrated_at": now},
    )

def find_campaign_by_join_code(join_code: str) -> Optional[Dict[str, Any]]:
    join_hash = hash_secret(join_code.strip().upper())
    for campaign_id in list_campaign_ids():
        path = campaign_path(campaign_id)
        try:
            with open(path, "r", encoding="utf-8") as f:
                if join_hash not in f.read():
                    continue
        except OSError:
            continue

        campaign = load_campaign(campaign_id)
        if campaign.get("campaign_meta", {}).get("join_code_hash") == join_hash:
            return campaign
    return None

def touch_player(campaign: Dict[str, Any], player_id: str) -> None:
    player = campaign["players"].get(player_id)
    if player:
        player["last_seen_at"] = utc_now()

def authenticate_player(
    campaign: Dict[str, Any],
    player_id: Optional[str],
    player_token: Optional[str],
    *,
    required: bool = True,
) -> Optional[Dict[str, Any]]:
    if not player_id or not player_token:
        if required:
            raise HTTPException(status_code=401, detail="Session fehlt oder ist unvollständig.")
        return None
    player = campaign.get("players", {}).get(player_id)
    if not player:
        raise HTTPException(status_code=401, detail="Unbekannter Spieler.")
    if hash_secret(player_token) != player.get("player_token_hash"):
        raise HTTPException(status_code=401, detail="Ungültiger Spieler-Token.")
    touch_player(campaign, player_id)
    return player

def require_host(campaign: Dict[str, Any], player_id: Optional[str]) -> None:
    if not is_host(campaign, player_id):
        raise HTTPException(status_code=403, detail="Nur der Host darf diese Aktion ausführen.")

def require_claim(campaign: Dict[str, Any], player_id: str, actor: str) -> None:
    claimed_player_id = campaign["claims"].get(actor)
    if not claimed_player_id:
        raise HTTPException(status_code=403, detail="Dieser Slot ist nicht geclaimt.")
    if claimed_player_id != player_id:
        raise HTTPException(status_code=403, detail="Du darfst nur deinen geclaimten Slot spielen.")

