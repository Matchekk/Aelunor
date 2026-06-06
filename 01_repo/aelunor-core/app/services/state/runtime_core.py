import hashlib
import json
import math
import os
import random
import re
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple

from fastapi import HTTPException
from app.helpers import setup_helpers
from app.services.setup.answers import (
    extract_text_answer,
    legacy_select_answer_payload,
    load_setup_catalog,
    parse_earth_items,
    parse_factions,
    parse_lines,
    split_creator_item_blocks,
    summarize_creator_item_name,
)
from app.services.setup.flow import (
    answered_count,
    build_character_question_queue,
    build_world_question_queue,
    current_question_id,
    default_setup,
    progress_payload,
    setup_chapter_config,
    setup_chapter_progress,
    setup_global_progress,
    setup_phase_display,
    setup_question_chapter_key,
    setup_question_is_applicable,
)
from app.services.setup import ai_copy as setup_ai_copy
from app.services.setup import attributes as setup_attributes
from app.services.setup.attributes import (
    allocate_weighted_attributes,
    fallback_character_attribute_weights,
    level_one_attribute_budget,
    level_one_attribute_cap,
    level_one_attributes_from_weights,
    normalize_attribute_weight_pool,
    parse_attribute_range,
    world_attribute_scale,
)
from app.services.setup import finalization as setup_finalization
from app.services.setup import payloads as setup_payloads
from app.services.setup import randomizer as setup_randomizer
from app.services.setup import summaries as setup_summaries
from app.adapters.llm import OllamaAdapter, OllamaSettings
from app.adapters.ollama_config import (
    OLLAMA_ADAPTER,
    OLLAMA_MODEL,
    OLLAMA_NUM_CTX,
    OLLAMA_REPEAT_LAST_N,
    OLLAMA_REPEAT_PENALTY,
    OLLAMA_SEED,
    OLLAMA_TEMPERATURE,
    OLLAMA_TIMEOUT_SEC,
    OLLAMA_URL,
)
from app.repositories.campaign_repository import CampaignRepository
from app.serializers import campaign_view as campaign_view_serializer

from app.catalogs.runtime_catalogs import (
    CANON_EXTRACTOR_SCHEMA,
    CATALOG_VERSION,
    CHARACTER_FORM_CATALOG,
    CHARACTER_QUESTION_MAP,
    INITIAL_STATE,
    PROGRESSION_EXTRACTOR_SCHEMA,
    RESPONSE_SCHEMA,
    SETUP_CATALOG,
    WORLD_FORM_CATALOG,
    WORLD_QUESTION_MAP,
)
from app.config.attributes import (
    ATTRIBUTE_INFLUENCE_DISTRIBUTION,
    ATTRIBUTE_INFLUENCE_STRENGTH,
)
from app.config.combat import (
    COMBAT_END_HINTS,
    COMBAT_NARRATIVE_HINTS,
)
from app.config.canon import (
    CANON_CHARACTER_FIELDS,
    CANON_GATE_ACTIVE_DOMAINS,
    CANON_GATE_DOMAINS_SUPPORTED,
)
from app.config.codex import (
    BEAST_BLOCKS_BY_LEVEL,
    BEAST_CODEX_BLOCK_ORDER,
    CODEX_BEAST_TRIGGER_ABILITY,
    CODEX_BEAST_TRIGGER_COMBAT,
    CODEX_BEAST_TRIGGER_DEFEAT,
    CODEX_DEFAULT_META,
    CODEX_KIND_BEAST,
    CODEX_KIND_RACE,
    CODEX_KNOWLEDGE_LEVEL_MAX,
    CODEX_KNOWLEDGE_LEVEL_MIN,
    CODEX_RACE_TRIGGER_CONTACT,
    CODEX_RACE_TRIGGER_LORE,
    NPC_STATUS_ALLOWED,
    RACE_BLOCKS_BY_LEVEL,
    RACE_CODEX_BLOCK_ORDER,
)
from app.config.elements import (
    ELEMENT_CLASS_PATH_MAX,
    ELEMENT_CLASS_PATH_MIN,
    ELEMENT_CLASS_PATH_RANKS,
    ELEMENT_CORE_NAMES,
    ELEMENT_GENERATED_NAMES_FALLBACK,
    ELEMENT_RELATION_SCORE,
    ELEMENT_RELATIONS,
    ELEMENT_SIMILARITY_BLACKLIST,
    ELEMENT_TOTAL_COUNT,
)
from app.config.errors import (
    ERROR_CODE_EXTRACTOR,
    ERROR_CODE_JSON_REPAIR,
    ERROR_CODE_NARRATOR_RESPONSE,
    ERROR_CODE_NORMALIZE,
    ERROR_CODE_PATCH_APPLY,
    ERROR_CODE_PATCH_SANITIZE,
    ERROR_CODE_PERSISTENCE,
    ERROR_CODE_SCHEMA_VALIDATION,
    ERROR_CODE_SSE_BROADCAST,
    ERROR_CODE_TURN_INTERNAL,
    TURN_ERROR_USER_MESSAGES,
)
from app.config.feature_flags import (
    ENABLE_HEURISTIC_NORMALIZE_BACKFILL,
    ENABLE_LEGACY_SHADOW_WRITEBACK,
)
from app.config.injuries import (
    INJURY_HEALING_STAGES,
    INJURY_SEVERITIES,
)
from app.config.migrations import (
    LEGACY_SHADOW_FIELDS,
    MIGRATION_ONLY_FIELDS,
)
from app.config.progression import (
    ATTRIBUTE_KEYS,
    CLASS_ASCENSION_STATUSES,
    DEFAULT_DYNAMIC_SKILL_LEVEL_MAX,
    DEFAULT_NUMERIC_SKILL_DELTA_XP,
    FIRST_SKILL_FORCE_PROBABILITY,
    LEGACY_ROLE_CLASS_MAP,
    LEGACY_SKILL_NAME_MAP,
    LEGACY_SKILL_TAGS,
    PROGRESSION_CLAIM_TYPES,
    PROGRESSION_DENSITY_CAP_MILESTONE,
    PROGRESSION_DENSITY_CAP_NON_MILESTONE,
    PROGRESSION_EVENT_BASE_XP,
    PROGRESSION_EVENT_PRIORITY,
    PROGRESSION_EVENT_SEVERITIES,
    PROGRESSION_EVENT_SEVERITY_MULTIPLIER,
    PROGRESSION_EVENT_TYPES,
    PROGRESSION_EXTRACTOR_CONFIDENCE_ORDER,
    PROGRESSION_EXTRACTOR_CONFIDENCE_SCORE,
    PROGRESSION_EXTRACTOR_CONFIDENCE_THRESHOLDS,
    PROGRESSION_SET_DIRECT_KEYS,
    RESOURCE_KEYS,
    RESISTANCE_KEYS,
    SKILL_ATTRIBUTE_MAP,
    SKILL_EVOLUTIONS,
    SKILL_FUSIONS,
    SKILL_KEYS,
    SKILL_OUTCOME_XP,
    SKILL_PATHS,
    SKILL_RANK_ORDER,
    SKILL_RANK_THRESHOLDS,
    SKILL_RANKS,
)
from app.config.runtime import (
    ACTION_TYPES,
    AI_LATENCY_CLAMP,
    CAMPAIGN_LENGTHS,
    CONTINUE_STORY_MARKER,
    EXTRACTION_QUARANTINE_DEFAULT_MAX,
    EXTRACTION_REASON_AMBIGUOUS_CLASS,
    EXTRACTION_REASON_CONFLICT_WITH_LLM,
    EXTRACTION_REASON_DUPLICATE,
    EXTRACTION_REASON_ENV_OBJECT,
    EXTRACTION_REASON_GENERIC_LOCATION,
    EXTRACTION_REASON_LOW_CONFIDENCE,
    EXTRACTION_REASON_MISSING_ACQUIRE,
    EXTRACTION_REASON_VERB_STYLE_SKILL,
    LEGACY_CHARACTERS,
    MAX_PLAYERS,
    MAX_STORY_COMPRESS_ATTEMPTS,
    MAX_TURN_MODEL_ATTEMPTS,
    MIN_STORY_REWRITE_ATTEMPTS,
    PACING_PROFILE_DEFAULTS,
    PHASES,
    PLAYER_LATENCY_CLAMP,
    TARGET_TURNS_DEFAULTS,
    TIMING_DEFAULTS,
    TIMING_EMA_ALPHA,
)
from app.config.setup import (
    CHAR_SETUP_CHAPTERS,
    LEGACY_SELECT_ALIASES,
    WORLD_SETUP_CHAPTERS,
)
from app.core.ids import (
    SLOT_PREFIX,
    deep_copy,
    hash_secret,
    make_id,
    utc_now,
)
from app.core.paths import (
    CAMPAIGNS_DIR,
    DATA_DIR,
    LEGACY_STATE_PATH,
    ensure_storage_dirs,
)
from app.prompts.system_prompts import (
    CANON_EXTRACTOR_JSON_CONTRACT,
    CANON_EXTRACTOR_SYSTEM_PROMPT,
    CHARACTER_ATTRIBUTE_SYSTEM_PROMPT,
    CONTEXT_ASSISTANT_SYSTEM_PROMPT,
    MANIFESTATION_SKILL_NAME_SYSTEM_PROMPT,
    MEMORY_SYSTEM_PROMPT,
    NPC_EXTRACTOR_JSON_CONTRACT,
    NPC_EXTRACTOR_SYSTEM_PROMPT,
    PROGRESSION_EXTRACTOR_JSON_CONTRACT,
    PROGRESSION_EXTRACTOR_SYSTEM_PROMPT,
    SETUP_QUESTION_SYSTEM_PROMPT,
    SETUP_RANDOM_SYSTEM_PROMPT,
    TURN_RESPONSE_JSON_CONTRACT,
)
from app.schemas.llm import (
    CHARACTER_ATTRIBUTE_SCHEMA,
    ELEMENT_GENERATOR_SCHEMA,
    MANIFESTATION_SKILL_NAME_SCHEMA,
    NPC_EXTRACTOR_SCHEMA,
    SETUP_RANDOM_SCHEMA,
)
from app.text.patterns import (
    ABILITY_UNLOCK_GENERIC_NAMES,
    ABILITY_UNLOCK_TRIGGER_PATTERNS,
    ACTION_STOPWORDS,
    AUTO_INJURY_PATTERNS,
    AUTO_ITEM_ACQUIRE_PATTERNS,
    AUTO_ITEM_EQUIP_PATTERNS,
    AUTO_ITEM_GENERIC_NAMES,
    ENGLISH_LANGUAGE_MARKERS,
    EQUIPMENT_CANONICAL_SLOTS,
    EQUIPMENT_SLOT_ALIASES,
    GERMAN_LANGUAGE_MARKERS,
    ITEM_CHEST_KEYWORDS,
    ITEM_DETAIL_CLAUSE_MARKERS,
    ITEM_OFFHAND_KEYWORDS,
    ITEM_TRINKET_KEYWORDS,
    ITEM_WEAPON_KEYWORDS,
    MANIFESTATION_COST_CUES,
    MANIFESTATION_EFFECT_CUES,
    MANIFESTATION_MOTIF_GROUPS,
    MANIFESTATION_STRONG_CUES,
    MANIFESTATION_TACTICAL_CUES,
    MANIFESTATION_WORLD_REACTION_CUES,
    NPC_GENERIC_NAME_TOKENS,
    PROGRESSION_CLAIM_CUES,
    SKILL_MANIFESTATION_NAME_STOPWORDS,
    SKILL_MANIFESTATION_NAME_TOKEN_BLACKLIST,
    SKILL_MANIFESTATION_VERB_BLACKLIST,
    STORY_ACTION_CUES,
    STORY_EXPLORE_CUES,
    STORY_LEARN_CUES,
    UNIVERSAL_SKILL_LIKE_NAMES,
)
from app.services.patch_payloads import (
    merge_character_patch_update,
    merge_patch_payloads,
    normalize_patch_payload,
    normalize_patch_semantics,
)
from app.services.boards.plotpoints import (
    normalize_event_entry,
    normalize_plotpoint_entry,
    normalize_plotpoint_update_entry,
)
from app.services.turn.output_normalization import (
    normalize_model_output_payload,
    normalize_request_entry,
    normalize_request_option_text,
    normalize_requests_payload,
)
from app.services.campaigns import lifecycle as campaign_lifecycle
from app.services.campaigns import normalization as campaign_normalization
from app.services.campaigns import persistence as campaign_persistence
from app.services.campaigns import state_shape as campaign_state_shape
from app.services.campaigns import views as campaign_views
from app.services import memory as memory_service
from app.services.migrations import campaign_slots as campaign_slot_migration
from app.services import live_state_service as _default_live_state_service
from app.services.canon import extractor as _canon_extractor_service
from app.services.canon import gate as _canon_gate_service
from app.services.canon import npc_extractor as _npc_extractor_service
from app.services.canon import patch_gate as _canon_patch_gate_service
from app.services.canon import progression_gate as _progression_gate_service
from app.services.extraction import abilities as _extraction_abilities
from app.services.extraction import classes as _extraction_classes
from app.services.extraction import heuristics as _extraction_heuristics
from app.services.extraction import injuries as _extraction_injuries
from app.services.extraction import items as _extraction_items
from app.services.extraction import quarantine as _extraction_quarantine
from app.services.progression import application as _progression_application_service
from app.services.progression import classes as _progression_classes_service
from app.services.progression import manifestation as _progression_manifestation_service
from app.services.progression import skills as _progression_skills_service
from app.services.turn_engine import emit_turn_phase_event, turn_flow_error
from app.services.llm.json_repair import (
    extract_json_payload,
    first_balanced_json_object,
    is_turn_response_schema,
    ollama_format_fallback_needed,
    repair_truncated_json_object,
    schema_fallback_instruction,
    strip_json_fences,
)
from app.services.state.dependencies import StateEngineDependencies
from app.services.state_basics import (
    blank_patch,
    is_slot_id,
    make_join_code,
    ordered_slots as _ordered_slots,
    slot_id as _slot_id,
    slot_index as _slot_index,
)
from app.services.characters.defaults import blank_character_state
from app.services.characters import appearance_state as _appearance_state_module
from app.services.characters.appearance_state import (
    age_character_if_needed,
    build_age_modifiers,
    build_class_visuals,
    build_corruption_visuals,
    build_faction_visuals,
    build_stat_based_appearance,
    corruption_bucket,
    derive_age_stage,
    infer_age_years,
    normalize_age_fields,
    normalize_appearance_state,
)
from app.services.characters.appearance_summary import (
    build_appearance_summary_full,
    build_appearance_summary_short,
    rebuild_character_appearance,
)
from app.services.characters import resource_maxima as _resource_maxima_module
from app.services.characters import resources as _character_resources_module
from app.services.characters.resource_maxima import (
    calculate_base_resource_maxima,
    calculate_bonus_resource_maxima,
    ensure_character_modifier_shape,
    item_modifier_value,
    item_weight,
    iter_equipped_item_ids,
    list_inventory_items,
    migrate_legacy_resource_bonus_modifiers,
    modifier_resource_key,
    rebuild_resource_maxima,
)
from app.services.characters import derived_stats as _derived_stats
from app.services.characters.derived_stats import (
    calculate_armor,
    calculate_carry_limit,
    calculate_carry_weight,
    calculate_defense,
    calculate_derived_bonus,
    calculate_initiative,
    calculate_resistances,
    calculate_skill_modifier_bonus,
)
from app.services.characters.resources import (
    build_compat_resources_view,
    canonical_resource_deltas_from_update,
    canonical_resource_field_name,
    canonical_resources_set_from_payload,
    ingest_legacy_resources_into_canonical,
    legacy_misc_resource_deltas_from_update,
    legacy_misc_resources_set_from_payload,
    reconcile_canonical_resources,
    resource_delta_payload,
    resource_name_for_character,
    strip_legacy_resource_shadows,
    strip_legacy_shadow_fields,
    sync_canonical_resources,
    write_legacy_shadow_fields,
)
from app.services.world.collections import stable_sorted_mapping
from app.services.world.element_profiles import (
    default_element_profile as _default_element_profile,
    element_id_from_name as _element_id_from_name,
    normalize_element_profile as _normalize_element_profile,
)
from app.services.world.element_relations import (
    apply_element_anchor_relation_rules as _apply_element_anchor_relation_rules,
    build_element_alias_index as _build_element_alias_index,
    build_default_element_relations as _build_default_element_relations,
    element_pair_rule_ids as _element_pair_rule_ids,
    element_sort_key as _element_sort_key,
    generate_element_relations as _generate_element_relations,
    get_element_relation as _get_element_relation,
    normalize_element_relation as _normalize_element_relation,
    normalize_element_relations as _normalize_element_relations,
    relation_sort_value as _relation_sort_value,
    reflect_element_relation_profile_fields as _reflect_element_relation_profile_fields,
    resolve_element_relation as _resolve_element_relation,
    set_element_relation as _set_element_relation_impl,
)
from app.services.world.element_generation import (
    candidate_from_fallback_element as _candidate_from_fallback_element,
    generate_world_element_profiles as _generate_world_element_profiles,
    generate_world_elements_fallback as _generate_world_elements_fallback,
    generate_world_elements_with_llm as _generate_world_elements_with_llm,
    generated_element_too_similar as _generated_element_too_similar,
    theme_flavor as _theme_flavor,
    theme_flavor_options as _theme_flavor_options,
)
from app.services.world.element_ids import (
    normalize_element_id_list as _normalize_element_id_list,
)
from app.services.world.element_skills import (
    normalize_skill_elements_for_world as _normalize_skill_elements_for_world,
)
from app.services.world.element_class_paths import (
    generate_element_class_paths as _generate_element_class_paths,
    next_element_path_name as _next_element_path_name,
    normalize_class_path_rank_node as _normalize_class_path_rank_node,
    normalize_element_class_paths as _normalize_element_class_paths,
    resolve_class_element_id as _resolve_class_element_id,
    resolve_class_path_rank_node as _resolve_class_path_rank_node,
)
from app.services.world.element_entities import (
    element_matchup_multiplier as _element_matchup_multiplier,
    entity_element_profile_for_character as _entity_element_profile_for_character,
    entity_element_profile_for_npc as _entity_element_profile_for_npc,
)
from app.services.world.math_utils import clamp
from app.services.world.naming import (
    fantasy_syllables_for_anchor,
    generate_unique_fantasy_name as _generate_unique_fantasy_name,
    generate_world_name as _generate_world_name,
    pick_world_theme_anchor as _pick_world_theme_anchor,
    strip_name_parenthetical,
)
from app.services.world.npc import npc_id_from_name, normalize_npc_alias
from app.services.world.species_profiles import (
    beast_id_from_name as _beast_id_from_name,
    default_beast_profile as _default_beast_profile,
    default_race_profile as _default_race_profile,
    normalize_beast_profile as _normalize_beast_profile,
    normalize_race_profile as _normalize_race_profile,
    race_id_from_name as _race_id_from_name,
)
from app.services.world.species_generation import (
    generate_world_beast_profiles as _generate_world_beast_profiles,
    generate_world_race_profiles as _generate_world_race_profiles,
)
from app.services.world.progression import (
    default_class_current,
    next_character_xp_for_level,
    normalize_class_current,
    normalize_resource_name,
)
from app.services.world.text_normalization import first_sentences, normalized_eval_text
from app.services.items.inventory import (
    ensure_item_shape,
    infer_item_slot_from_definition,
    item_by_id,
    item_matches_equipment_slot,
    normalize_equipment_slot_key,
    normalize_equipment_update_payload,
)
from app.services.context import (
    build_context_knowledge_index,
    build_context_result_payload,
    build_context_result_via_llm,
    build_reduced_context_snippets,
    context_meta_drift_detected,
    context_result_to_answer_text,
    context_state_signature,
    deterministic_context_result_from_entry,
    parse_context_intent,
    resolve_context_target,
    strip_markdown_like,
)

# -- Codex-Subsystem (ausgelagert nach app/services/world/codex.py) --
from app.services.world.codex import (
    normalize_codex_entry_stable,
    normalize_codex_alias_text,
    strip_codex_name_prefix,
    codex_block_order,
    codex_blocks_for_level,
    merge_known_facts_stable,
    stable_sorted_unique_strings,
    codex_facts_for_blocks,
    world_codex_sort_key,
    normalize_world_codex_structures,
    build_world_alias_indexes,
    build_world_exact_name_index,
    resolve_codex_entity_ids,
    build_entity_alias_variants,
    safe_last_token_variants,
    default_npc_entry,
    normalize_npc_entry,
    normalize_npc_codex_state,
    seed_npc_codex_from_story_cards,
    default_race_codex_entry,
    default_beast_codex_entry,
    race_profile_block_facts,
    beast_profile_block_facts,
    codex_seed_for_state,
    ensure_world_codex_from_setup,
)
from app.services.world.codex_triggers import (
    apply_codex_triggers,
    collect_beast_observed_abilities,
    collect_codex_triggers,
    contains_any_normalized_token,
)
from app.services.world.attribute_influence import (
    apply_attribute_bias_to_patch as _apply_attribute_bias_to_patch,
    apply_attribute_bias_to_resolution as _apply_attribute_bias_to_resolution,
    compose_attribute_prompt_hints as _compose_attribute_prompt_hints,
    compute_attribute_bias as _compute_attribute_bias,
    default_attribute_influence_meta as _default_attribute_influence_meta,
    derive_attribute_relevance as _derive_attribute_relevance,
    normalize_attribute_influence_meta as _normalize_attribute_influence_meta,
    scale_negative_delta as _scale_negative_delta_helper,
)
from app.services.world.appearance import (
    appearance_event_id,
    default_appearance_profile,
    format_appearance_message,
    record_appearance_change,
)
from app.services.characters.appearance_changes import sync_appearance_changes
from app.services.world.state_defaults import (
    default_character_modifiers,
    default_intro_state,
    default_world_time,
)
from app.services.world.world_settings import (
    active_pacing_profile as _active_pacing_profile,
    build_pacing_instruction_block as _build_pacing_instruction_block,
    compute_turn_budget_estimates as _compute_turn_budget_estimates,
    default_campaign_length_settings as _default_campaign_length_settings,
    milestone_state_for_turn as _milestone_state_for_turn,
    normalize_meta_timing as _normalize_meta_timing,
    normalize_world_settings as _normalize_world_settings,
    update_turn_timing_ema as _update_turn_timing_ema,
)
from app.services.world.skill_costs import (
    apply_skill_cost_deltas_to_patch as _apply_skill_cost_deltas_to_patch,
    infer_skill_cost_deltas_from_text as _infer_skill_cost_deltas_from_text,
    normalize_skill_cost as _normalize_skill_cost,
)
from app.services.world.skill_ranks import (
    next_skill_xp_for_level as _next_skill_xp_for_level,
    normalize_skill_rank as _normalize_skill_rank,
    skill_rank_for_level as _skill_rank_for_level,
)
from app.services.world.skill_state import (
    normalize_power_rating as _normalize_power_rating,
    normalize_cooldown_turns as _normalize_cooldown_turns,
    normalize_growth_potential as _normalize_growth_potential,
    normalize_optional_lower_text as _normalize_optional_lower_text,
    normalize_optional_strings as _normalize_optional_strings,
    normalize_optional_text as _normalize_optional_text,
    normalize_optional_unique_strings as _normalize_optional_unique_strings,
    normalize_skill_element_fields as _normalize_skill_element_fields,
    normalize_skill_progression_fields as _normalize_skill_progression_fields,
)
from app.services.world.scene import (
    canonical_scene_id,
    clean_scene_name,
    extract_descriptive_scene_name,
    extract_scene_candidates,
    is_generic_scene_identifier,
    is_plausible_scene_name,
)
from app.services.world.combat import (
    apply_combat_scaling_to_patch as _apply_combat_scaling_to_patch,
    build_combat_scaling_context as _build_combat_scaling_context,
    compute_character_combat_score as _compute_character_combat_score,
    compute_npc_combat_score as _compute_npc_combat_score,
    default_combat_meta as _default_combat_meta,
    infer_combat_context as _infer_combat_context,
    normalize_combat_meta as _normalize_combat_meta,
    patch_has_combat_signal as _patch_has_combat_signal,
    skill_rank_power_weight as _skill_rank_power_weight,
    update_combat_meta_after_turn as _update_combat_meta_after_turn,
)

_CONFIGURED = False
_STATE_ENGINE_DEPS = StateEngineDependencies(
    ollama_adapter=OLLAMA_ADAPTER,
    live_state_service=_default_live_state_service,
)


def _legacy_config_snapshot(extra: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    snapshot = {
        name: value
        for name, value in globals().items()
        if not name.startswith("__") and name not in {"configure", "configure_dependencies"}
    }
    if extra:
        snapshot.update(dict(extra))
    return snapshot


def _configure_extractor_service_ports() -> None:
    _extraction_abilities.configure(
        skill_id_from_name=_progression_skills_service.skill_id_from_name,
        normalize_dynamic_skill_state=_progression_skills_service.normalize_dynamic_skill_state,
    )
    _extraction_heuristics.configure(
        skill_id_from_name=_progression_skills_service.skill_id_from_name,
        skill_rank_sort_value=_progression_skills_service.skill_rank_sort_value,
        normalize_dynamic_skill_state=_progression_skills_service.normalize_dynamic_skill_state,
    )
    _canon_extractor_service.configure(call_ollama_schema=call_ollama_schema)
    _npc_extractor_service.configure(
        call_ollama_schema=call_ollama_schema,
        class_rank_sort_value=_progression_classes_service.class_rank_sort_value,
        normalize_skill_store=_progression_skills_service.normalize_skill_store,
        normalize_dynamic_skill_state=_progression_skills_service.normalize_dynamic_skill_state,
        merge_dynamic_skill=_progression_skills_service.merge_dynamic_skill,
    )


def _configure_progression_service_ports() -> None:
    _progression_manifestation_service.configure(
        call_ollama_schema=call_ollama_schema,
        ollama_temperature=OLLAMA_TEMPERATURE,
    )
    _progression_application_service.configure(
        blank_character_state=blank_character_state,
        normalize_world_time=normalize_world_time,
        sync_appearance_changes=sync_appearance_changes,
    )


def _configure_canon_gate_service_ports() -> None:
    from app.services import turn_engine as _turn_engine

    _progression_gate_service.configure(
        active_pacing_profile=active_pacing_profile,
        build_extractor_context_packet=build_extractor_context_packet,
        call_ollama_schema=call_ollama_schema,
        milestone_state_for_turn=milestone_state_for_turn,
        normalize_dynamic_skill_state=_progression_skills_service.normalize_dynamic_skill_state,
    )
    _canon_patch_gate_service.configure(
        apply_patch=_turn_engine.apply_patch,
        attribute_cap_for_campaign=attribute_cap_for_campaign,
        emit_turn_phase_event=emit_turn_phase_event,
        sanitize_patch=_turn_engine.sanitize_patch,
        validate_patch=_turn_engine.validate_patch,
    )
    _canon_gate_service.configure(emit_turn_phase_event=emit_turn_phase_event)


def configure_dependencies(deps: StateEngineDependencies) -> None:
    """Configure explicit runtime ports for the state engine."""
    global _CONFIGURED, _STATE_ENGINE_DEPS
    _STATE_ENGINE_DEPS = _STATE_ENGINE_DEPS.merged(deps)
    configured_globals = _legacy_config_snapshot()

    # Subsysteme mitinitialisieren
    from app.services.world import codex as _codex_module
    from app.services.world import injury_state as _injury_state_module
    from app.services.world import npc as _npc_module
    from app.services.world import progression as _progression_module
    _appearance_state_module.configure(configured_globals)
    _character_resources_module.configure(configured_globals)
    _resource_maxima_module.configure(configured_globals)
    _npc_module.configure(configured_globals)
    _progression_module.configure(configured_globals)
    _codex_module.configure(configured_globals)
    _configure_progression_service_ports()
    _configure_extractor_service_ports()
    _configure_canon_gate_service_ports()
    for _name in (
        "deep_copy",
        "make_id",
        "INJURY_SEVERITIES",
        "INJURY_HEALING_STAGES",
    ):
        if _name in globals():
            setattr(_injury_state_module, _name, globals()[_name])

    _CONFIGURED = True


def configure(main_globals: Mapping[str, Any] | StateEngineDependencies) -> None:
    """Legacy adapter for older callers.

    The mapping form intentionally no longer performs ``globals().update``.
    It extracts explicit runtime ports and forwards a bounded snapshot to the
    few legacy submodules that still expose configure().
    """
    if isinstance(main_globals, StateEngineDependencies):
        configure_dependencies(main_globals)
        return
    deps = StateEngineDependencies.from_mapping(main_globals)
    configure_dependencies(deps)

# Public state-engine facade kept intentionally small. Domain helpers live in
# their target modules; runtime_symbols() is the temporary app-internal bridge.
EXPORTED_SYMBOLS = [
    'public_turn', 'build_campaign_view',
]

# Temporary app-internal bridge for runtime consumers that still accept a
# globals-style mapping: router dependency factories, turn patch sanitizer/
# validator configuration, and the turn record pipeline. This is deliberately
# not the public API; remove entries as those consumers gain explicit ports.
_STATE_ENGINE_RUNTIME_SYMBOLS = (
    'ACTION_STOPWORDS',
    'ATTRIBUTE_KEYS',
    'CANON_EXTRACTOR_SYSTEM_PROMPT',
    'CHARACTER_QUESTION_MAP',
    'DEFAULT_DYNAMIC_SKILL_LEVEL_MAX',
    'DEFAULT_NUMERIC_SKILL_DELTA_XP',
    'ENABLE_LEGACY_SHADOW_WRITEBACK',
    'ERROR_CODE_EXTRACTOR',
    'ERROR_CODE_JSON_REPAIR',
    'ERROR_CODE_NARRATOR_RESPONSE',
    'ERROR_CODE_PATCH_APPLY',
    'ERROR_CODE_PATCH_SANITIZE',
    'ERROR_CODE_SCHEMA_VALIDATION',
    'ERROR_CODE_TURN_INTERNAL',
    'INJURY_HEALING_STAGES',
    'INJURY_SEVERITIES',
    'MAX_STORY_COMPRESS_ATTEMPTS',
    'MAX_TURN_MODEL_ATTEMPTS',
    'MIN_STORY_REWRITE_ATTEMPTS',
    'OLLAMA_REPEAT_PENALTY',
    'OLLAMA_TEMPERATURE',
    'PACING_PROFILE_DEFAULTS',
    'PROGRESSION_SET_DIRECT_KEYS',
    'TARGET_TURNS_DEFAULTS',
    'TURN_ERROR_USER_MESSAGES',
    'TURN_RESPONSE_JSON_CONTRACT',
    'UNIVERSAL_SKILL_LIKE_NAMES',
    'WORLD_QUESTION_MAP',
    # Turn engine still reads these campaign helpers through the transition bridge.
    'active_party',
    'active_turns',
    'append_character_change_events',
    'apply_attribute_bias_to_patch',
    'apply_attribute_bias_to_resolution',
    'apply_character_summary_to_state',
    'apply_combat_scaling_to_patch',
    'apply_random_setup_preview',
    'apply_skill_cost_deltas_to_patch',
    'apply_world_summary_to_boards',
    'apply_world_time_advance',
    'attribute_cap_for_campaign',
    'blank_patch',
    'build_character_question_state',
    'build_character_summary',
    'build_combat_scaling_context',
    'build_context_knowledge_index',
    'build_context_packet',
    'build_context_result_payload',
    'build_context_result_via_llm',
    'build_patch_summary',
    'build_random_setup_preview',
    'build_reduced_context_snippets',
    'build_skill_system_requests',
    'build_world_question_state',
    'build_world_summary',
    'campaign_slots',
    'canonical_resource_deltas_from_update',
    'canonical_resources_set_from_payload',
    'clamp',
    'class_rank_sort_value',
    'clean_auto_item_name',
    'clean_creator_item_name',
    'clean_scene_name',
    'compose_attribute_prompt_hints',
    'compute_attribute_bias',
    'context_result_to_answer_text',
    'context_state_signature',
    'current_question_id',
    'deep_copy',
    'default_class_current',
    'derive_attribute_relevance',
    'deterministic_context_result_from_entry',
    'display_name_for_slot',
    'effective_skill_progress_multiplier',
    'emit_turn_phase_event',
    'ensure_character_progression_core',
    'ensure_class_rank_core_skills',
    'ensure_item_shape',
    'ensure_progression_shape',
    'ensure_question_ai_copy',
    'extract_story_target_evidence',
    'finalize_character_setup',
    'finalize_world_setup',
    'hash_secret',
    'infer_combat_context',
    'infer_item_slot_from_definition',
    'infer_skill_cost_deltas_from_text',
    'is_continue_story_content',
    'is_generic_scene_identifier',
    'is_plausible_scene_name',
    'is_skill_manifestation_name_plausible',
    'is_slot_id',
    'is_suspicious_story_text',
    'item_matches_equipment_slot',
    'legacy_misc_resource_deltas_from_update',
    'legacy_misc_resources_set_from_payload',
    'make_id',
    'merge_dynamic_skill',
    'merge_patch_payloads',
    'next_skill_xp_for_level',
    'normalize_ability_state',
    'normalize_class_current',
    'normalize_dynamic_skill_state',
    'normalize_equipment_slot_key',
    'normalize_equipment_update_payload',
    'normalize_event_entry',
    'normalize_injury_state',
    'normalize_model_output_payload',
    'normalize_patch_semantics',
    'normalize_plotpoint_entry',
    'normalize_plotpoint_update_entry',
    'normalize_progression_event_list',
    'normalize_requests_payload',
    'normalize_scar_state',
    'normalize_skill_elements_for_world',
    'normalize_skill_rank',
    'normalize_skill_store',
    'normalize_world_settings',
    'normalize_world_time',
    'normalized_eval_text',
    'parse_context_intent',
    'progress_payload',
    'rebuild_all_character_derived',
    'rebuild_character_derived',
    'rebuild_memory_summary',
    'reconcile_canonical_resources',
    'remember_recent_story',
    'resolve_class_element_id',
    'resolve_context_target',
    'resolve_injury_healing',
    'resource_name_for_character',
    'skill_id_from_name',
    'slot_index',
    'store_setup_answer',
    'strip_legacy_shadow_fields',
    'sync_scars_into_appearance',
    'try_generate_adventure_intro',
    'update_combat_meta_after_turn',
    'utc_now',
    'validate_answer_payload',
    'write_legacy_shadow_fields',
)
def runtime_symbols() -> Dict[str, Any]:
    return {name: globals()[name] for name in _STATE_ENGINE_RUNTIME_SYMBOLS if name in globals()}

def slot_id(index: int) -> str:
    return _slot_id(index, slot_prefix=SLOT_PREFIX)

def slot_index(value: str) -> int:
    return _slot_index(value, slot_prefix=SLOT_PREFIX)

def ordered_slots(keys: List[str]) -> List[str]:
    return _ordered_slots(keys, slot_prefix=SLOT_PREFIX)

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

def generate_world_elements_with_llm(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    return _generate_world_elements_with_llm(
        summary,
        call_ollama_schema=call_ollama_schema,
        element_generator_schema=ELEMENT_GENERATOR_SCHEMA,
    )

def generate_world_element_profiles(summary: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return _generate_world_element_profiles(
        summary,
        element_total_count=ELEMENT_TOTAL_COUNT,
        element_id_from_name=element_id_from_name,
        normalize_element_profile=normalize_element_profile,
        default_element_profile=default_element_profile,
        normalize_codex_alias_text=normalize_codex_alias_text,
        generate_world_elements_with_llm=generate_world_elements_with_llm,
        generate_world_elements_fallback=generate_world_elements_fallback,
        generated_element_too_similar=generated_element_too_similar,
        stable_sorted_mapping=stable_sorted_mapping,
        element_sort_key=element_sort_key,
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
    _reflect_element_relation_profile_fields(
        world["elements"],
        world.get("element_relations") or {},
        normalize_element_relation=normalize_element_relation,
    )
    world["elements"] = stable_sorted_mapping(world["elements"], key_fn=element_sort_key)

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

from app.services.world.injury_state import (
    default_injury_state,
    default_scar_state,
    normalize_injury_state,
    normalize_scar_state,
)

def skill_rank_for_level(*args: Any, **kwargs: Any):
    return _progression_skills_service.skill_rank_for_level(*args, **kwargs)


def next_skill_xp_for_level(*args: Any, **kwargs: Any):
    return _progression_skills_service.next_skill_xp_for_level(*args, **kwargs)


def next_class_xp_for_level(*args: Any, **kwargs: Any):
    return _progression_classes_service.next_class_xp_for_level(*args, **kwargs)


def normalize_ability_state(*args: Any, **kwargs: Any):
    return _progression_skills_service.normalize_ability_state(*args, **kwargs)


def skill_id_from_name(*args: Any, **kwargs: Any):
    return _progression_skills_service.skill_id_from_name(*args, **kwargs)


def display_skill_name_from_id(*args: Any, **kwargs: Any):
    return _progression_skills_service.display_skill_name_from_id(*args, **kwargs)


clean_extracted_skill_name = _extraction_abilities.clean_extracted_skill_name

split_extracted_skill_names = _extraction_abilities.split_extracted_skill_names

def infer_skill_name_from_description(*args: Any, **kwargs: Any):
    return _progression_skills_service.infer_skill_name_from_description(*args, **kwargs)


def normalize_skill_store(*args: Any, **kwargs: Any):
    return _progression_skills_service.normalize_skill_store(*args, **kwargs)


def dynamic_skill_default(*args: Any, **kwargs: Any):
    return _progression_skills_service.dynamic_skill_default(*args, **kwargs)


def normalize_skill_rank(*args: Any, **kwargs: Any):
    return _progression_skills_service.normalize_skill_rank(*args, **kwargs)


def normalize_dynamic_skill_state(*args: Any, **kwargs: Any):
    return _progression_skills_service.normalize_dynamic_skill_state(*args, **kwargs)


def merge_dynamic_skill(*args: Any, **kwargs: Any):
    return _progression_skills_service.merge_dynamic_skill(*args, **kwargs)


def skill_rank_sort_value(*args: Any, **kwargs: Any):
    return _progression_skills_service.skill_rank_sort_value(*args, **kwargs)


def extract_skill_entries_for_character(*args: Any, **kwargs: Any):
    return _progression_skills_service.extract_skill_entries_for_character(*args, **kwargs)


def build_skill_fusion_hints(*args: Any, **kwargs: Any):
    return _progression_skills_service.build_skill_fusion_hints(*args, **kwargs)


def class_rank_sort_value(*args: Any, **kwargs: Any):
    return _progression_classes_service.class_rank_sort_value(*args, **kwargs)


def class_affinity_match(*args: Any, **kwargs: Any):
    return _progression_skills_service.class_affinity_match(*args, **kwargs)


sentence_mentions_actor_name = _extraction_items.sentence_mentions_actor_name

def effective_skill_progress_multiplier(*args: Any, **kwargs: Any):
    return _progression_skills_service.effective_skill_progress_multiplier(*args, **kwargs)


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
        skill = _progression_skills_service.normalize_skill_state(skill_name, skills.get(skill_name))
        if int(skill.get("level", 0) or 0) != 1:
            return False
        if int(skill.get("xp", 0) or 0) != 0:
            return False
        if skill.get("path") or skill.get("evolutions") or skill.get("fusion_candidates"):
            return False
    return True

def default_boards(player_id: Optional[str] = None) -> Dict[str, Any]:
    return campaign_lifecycle.default_boards(player_id)

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

def append_character_change_events(*args: Any, **kwargs: Any):
    return _progression_application_service.append_character_change_events(*args, **kwargs)


def calculate_attack_rating(character: Dict[str, Any], hand: str, items_db: Dict[str, Any]) -> int:
    return _derived_stats.calculate_attack_rating(
        character,
        hand,
        items_db,
        skill_level_value=_progression_skills_service.skill_level_value,
    )


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
    return _derived_stats.skill_effective_bonus(
        character,
        skill_name,
        items_db,
        normalize_skill_state=_progression_skills_service.normalize_skill_state,
        default_skill_state=_progression_skills_service.default_skill_state,
    )

def ensure_progression_shape(*args: Any, **kwargs: Any):
    return _progression_skills_service.ensure_progression_shape(*args, **kwargs)


def ensure_character_progression_core(*args: Any, **kwargs: Any):
    return _progression_skills_service.ensure_character_progression_core(*args, **kwargs)


def normalize_progression_event_severity(*args: Any, **kwargs: Any):
    return _progression_gate_service.normalize_progression_event_severity(*args, **kwargs)


def normalize_progression_event(*args: Any, **kwargs: Any):
    return _progression_gate_service.normalize_progression_event(*args, **kwargs)


def is_skill_manifestation_name_plausible(*args: Any, **kwargs: Any):
    return _progression_gate_service.is_skill_manifestation_name_plausible(*args, **kwargs)


def canonicalize_manifested_skill_payload(*args: Any, **kwargs: Any):
    return _progression_manifestation_service.canonicalize_manifested_skill_payload(*args, **kwargs)


def ensure_class_rank_core_skills(*args: Any, **kwargs: Any):
    return _progression_classes_service.ensure_class_rank_core_skills(*args, **kwargs)


def refresh_skill_progression(*args: Any, **kwargs: Any):
    return _progression_skills_service.refresh_skill_progression(*args, **kwargs)


def normalize_progression_event_list(*args: Any, **kwargs: Any):
    return _progression_gate_service.normalize_progression_event_list(*args, **kwargs)


def progression_event_priority(*args: Any, **kwargs: Any):
    return _progression_gate_service.progression_event_priority(*args, **kwargs)


def _event_origin(*args: Any, **kwargs: Any):
    return _progression_gate_service._event_origin(*args, **kwargs)


def reduce_progression_event_density(*args: Any, **kwargs: Any):
    return _progression_gate_service.reduce_progression_event_density(*args, **kwargs)


def patch_has_explicit_skill_progression_for_actor(*args: Any, **kwargs: Any):
    return _progression_gate_service.patch_has_explicit_skill_progression_for_actor(*args, **kwargs)


def normalize_progression_claim_type(*args: Any, **kwargs: Any):
    return _progression_gate_service.normalize_progression_claim_type(*args, **kwargs)


def progression_claim_text_for_actor(*args: Any, **kwargs: Any):
    return _progression_gate_service.progression_claim_text_for_actor(*args, **kwargs)


def detect_progression_claim_types(*args: Any, **kwargs: Any):
    return _progression_gate_service.detect_progression_claim_types(*args, **kwargs)


def progression_claim_coverage_for_actor_patch(*args: Any, **kwargs: Any):
    return _progression_gate_service.progression_claim_coverage_for_actor_patch(*args, **kwargs)


def normalized_progression_claims(*args: Any, **kwargs: Any):
    return _progression_gate_service.normalized_progression_claims(*args, **kwargs)


def progression_missing_claim_types(*args: Any, **kwargs: Any):
    return _progression_gate_service.progression_missing_claim_types(*args, **kwargs)


def normalize_progression_extractor_character_patch(*args: Any, **kwargs: Any):
    return _progression_gate_service.normalize_progression_extractor_character_patch(*args, **kwargs)


def progression_event_dedupe_key(*args: Any, **kwargs: Any):
    return _progression_gate_service.progression_event_dedupe_key(*args, **kwargs)


def merge_progression_patch_additive(*args: Any, **kwargs: Any):
    return _progression_gate_service.merge_progression_patch_additive(*args, **kwargs)


def evaluate_progression_extractor_confidence(*args: Any, **kwargs: Any):
    return _progression_gate_service.evaluate_progression_extractor_confidence(*args, **kwargs)


def call_progression_canon_extractor(*args: Any, **kwargs: Any):
    return _progression_gate_service.call_progression_canon_extractor(*args, **kwargs)


def run_canon_gate(*args: Any, **kwargs: Any):
    return _canon_gate_service.run_canon_gate(*args, **kwargs)


def apply_progression_events(*args: Any, **kwargs: Any):
    return _progression_application_service.apply_progression_events(*args, **kwargs)


def build_skill_system_requests(*args: Any, **kwargs: Any):
    return _progression_application_service.build_skill_system_requests(*args, **kwargs)


def apply_skill_events(*args: Any, **kwargs: Any):
    return _progression_skills_service.apply_skill_events(*args, **kwargs)


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
        merged["class_current"] = _progression_classes_service.migrate_legacy_role_to_class(legacy_role_text)
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
    return _default_campaign_length_settings(
        deep_copy=deep_copy,
        target_turns_defaults=TARGET_TURNS_DEFAULTS,
        pacing_profile_defaults=PACING_PROFILE_DEFAULTS,
    )

def default_meta_timing() -> Dict[str, Any]:
    return deep_copy(TIMING_DEFAULTS)

def clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value)))

def default_combat_meta() -> Dict[str, Any]:
    return _default_combat_meta(utc_now=utc_now)

def default_attribute_influence_meta() -> Dict[str, Any]:
    return _default_attribute_influence_meta()

default_extraction_quarantine = _extraction_quarantine.default_extraction_quarantine

normalize_extraction_quarantine_meta = _extraction_quarantine.normalize_extraction_quarantine_meta

def normalize_meta_migrations(meta: Dict[str, Any]) -> Dict[str, Any]:
    raw = meta.get("migrations")
    migrations = deep_copy(raw) if isinstance(raw, dict) else {}
    migrations["npc_codex_seeded_from_story_cards"] = bool(migrations.get("npc_codex_seeded_from_story_cards", False))
    meta["migrations"] = migrations
    return migrations

def normalize_world_settings(world_settings: Any) -> Dict[str, Any]:
    return _normalize_world_settings(
        world_settings,
        deep_copy=deep_copy,
        default_campaign_length_settings=default_campaign_length_settings,
        normalize_resource_name=normalize_resource_name,
        clamp_float=clamp_float,
        campaign_lengths=CAMPAIGN_LENGTHS,
    )

def normalize_meta_timing(meta: Dict[str, Any]) -> Dict[str, Any]:
    return _normalize_meta_timing(
        meta,
        deep_copy=deep_copy,
        default_meta_timing=default_meta_timing,
    )

def normalize_combat_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    return _normalize_combat_meta(
        meta,
        default_combat_meta=default_combat_meta,
        deep_copy=deep_copy,
        action_types=ACTION_TYPES,
        utc_now=utc_now,
    )

def normalize_attribute_influence_meta(meta: Dict[str, Any]) -> Dict[str, Any]:
    return _normalize_attribute_influence_meta(
        meta,
        default_attribute_influence_meta=default_attribute_influence_meta,
        deep_copy=deep_copy,
        attribute_keys=ATTRIBUTE_KEYS,
        clamp_float=clamp_float,
    )

def active_pacing_profile(state: Dict[str, Any]) -> Dict[str, Any]:
    return _active_pacing_profile(
        state,
        normalize_world_settings=normalize_world_settings,
        deep_copy=deep_copy,
        campaign_lengths=CAMPAIGN_LENGTHS,
        pacing_profile_defaults=PACING_PROFILE_DEFAULTS,
    )

def compute_turn_budget_estimates(state: Dict[str, Any]) -> Dict[str, Any]:
    return _compute_turn_budget_estimates(
        state,
        normalize_meta_timing=normalize_meta_timing,
        normalize_world_settings=normalize_world_settings,
        target_turns_defaults=TARGET_TURNS_DEFAULTS,
        timing_defaults=TIMING_DEFAULTS,
    )

def update_turn_timing_ema(state: Dict[str, Any], request_ts: float, response_ts: float) -> Dict[str, Any]:
    return _update_turn_timing_ema(
        state,
        request_ts,
        response_ts,
        normalize_meta_timing=normalize_meta_timing,
        clamp_float=clamp_float,
        ai_latency_clamp=AI_LATENCY_CLAMP,
        player_latency_clamp=PLAYER_LATENCY_CLAMP,
        timing_ema_alpha=TIMING_EMA_ALPHA,
        timing_defaults=TIMING_DEFAULTS,
    )

def milestone_state_for_turn(turn_number: int, profile: Dict[str, Any]) -> Dict[str, int | bool]:
    return _milestone_state_for_turn(turn_number, profile)

def build_pacing_instruction_block(state: Dict[str, Any]) -> Dict[str, Any]:
    return _build_pacing_instruction_block(
        state,
        active_pacing_profile=active_pacing_profile,
        milestone_state_for_turn=milestone_state_for_turn,
    )

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
    return _derive_attribute_relevance(
        state,
        actor,
        action_type,
        text,
        combat_context,
        normalized_eval_text=normalized_eval_text,
        hash_unit_interval=_hash_unit_interval,
        attribute_keys=ATTRIBUTE_KEYS,
        attribute_influence_distribution=ATTRIBUTE_INFLUENCE_DISTRIBUTION,
    )

def compute_attribute_bias(profile: Dict[str, Any], character: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
    return _compute_attribute_bias(
        profile,
        character,
        world_settings,
        attribute_keys=ATTRIBUTE_KEYS,
        attribute_influence_strength=ATTRIBUTE_INFLUENCE_STRENGTH,
        clamp=clamp,
        clamp_float=clamp_float,
    )

def compose_attribute_prompt_hints(profile: Dict[str, Any], bias: Dict[str, float]) -> str:
    return _compose_attribute_prompt_hints(profile, bias)

def apply_attribute_bias_to_resolution(resolution: Dict[str, Any], numeric_bias: Dict[str, float]) -> Dict[str, Any]:
    return _apply_attribute_bias_to_resolution(
        resolution,
        numeric_bias,
        deep_copy=deep_copy,
    )

def _scale_negative_delta(value: int, multiplier: float) -> int:
    return _scale_negative_delta_helper(value, multiplier)

def apply_attribute_bias_to_patch(
    patch: Dict[str, Any],
    actor: str,
    numeric_bias: Dict[str, float],
) -> tuple[Dict[str, Any], Dict[str, int]]:
    return _apply_attribute_bias_to_patch(
        patch,
        actor,
        numeric_bias,
        deep_copy=deep_copy,
        blank_patch=blank_patch,
    )

def infer_skill_cost_deltas_from_text(
    state: Dict[str, Any],
    actor: str,
    action_type: str,
    source_text: str,
    *,
    combat_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return _infer_skill_cost_deltas_from_text(
        state,
        actor,
        action_type,
        source_text,
        combat_context=combat_context,
        resource_name_for_character=resource_name_for_character,
        normalized_eval_text=normalized_eval_text,
        normalize_dynamic_skill_state=normalize_dynamic_skill_state,
    )

def apply_skill_cost_deltas_to_patch(patch: Dict[str, Any], actor: str, delta_payload: Dict[str, Any]) -> Dict[str, Any]:
    return _apply_skill_cost_deltas_to_patch(
        patch,
        actor,
        delta_payload,
        deep_copy=deep_copy,
        blank_patch=blank_patch,
    )

def skill_rank_power_weight(rank: str) -> int:
    return _skill_rank_power_weight(rank, normalize_skill_rank=normalize_skill_rank)

def entity_element_profile_for_character(character: Dict[str, Any], world: Dict[str, Any]) -> Dict[str, List[str]]:
    return _entity_element_profile_for_character(
        character,
        world,
        normalize_class_current=normalize_class_current,
        resolve_class_element_id=resolve_class_element_id,
        normalize_element_id_list=normalize_element_id_list,
    )

def entity_element_profile_for_npc(npc_entry: Dict[str, Any], world: Dict[str, Any]) -> Dict[str, List[str]]:
    return _entity_element_profile_for_npc(
        npc_entry,
        world,
        normalize_class_current=normalize_class_current,
        resolve_class_element_id=resolve_class_element_id,
        normalize_element_id_list=normalize_element_id_list,
    )

def element_matchup_multiplier(world: Dict[str, Any], attacker_profile: Dict[str, List[str]], defender_profile: Dict[str, List[str]]) -> float:
    return _element_matchup_multiplier(
        world,
        attacker_profile,
        defender_profile,
        resolve_element_relation=resolve_element_relation,
        element_relation_score=ELEMENT_RELATION_SCORE,
    )

def compute_character_combat_score(character: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> int:
    return _compute_character_combat_score(
        character,
        world_settings,
        normalize_class_current=normalize_class_current,
        skill_rank_power_weight=skill_rank_power_weight,
        normalize_dynamic_skill_state=normalize_dynamic_skill_state,
        resource_name_for_character=resource_name_for_character,
        normalize_injury_state=normalize_injury_state,
    )

def compute_npc_combat_score(npc_entry: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> int:
    return _compute_npc_combat_score(
        npc_entry,
        world_settings,
        normalize_class_current=normalize_class_current,
        skill_rank_power_weight=skill_rank_power_weight,
        normalize_dynamic_skill_state=normalize_dynamic_skill_state,
        normalize_resource_name=normalize_resource_name,
    )

def build_combat_scaling_context(state: Dict[str, Any], actor: str) -> Dict[str, Any]:
    return _build_combat_scaling_context(
        state,
        actor,
        compute_character_combat_score=compute_character_combat_score,
        compute_npc_combat_score=compute_npc_combat_score,
        entity_element_profile_for_character=entity_element_profile_for_character,
        entity_element_profile_for_npc=entity_element_profile_for_npc,
        element_matchup_multiplier=element_matchup_multiplier,
        sorted_npc_codex_entries=sorted_npc_codex_entries,
    )

def apply_combat_scaling_to_patch(
    patch: Dict[str, Any],
    *,
    actor: str,
    combat_context: Dict[str, Any],
    scaling_context: Dict[str, Any],
    action_type: str,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    return _apply_combat_scaling_to_patch(
        patch,
        actor=actor,
        combat_context=combat_context,
        scaling_context=scaling_context,
        action_type=action_type,
        deep_copy=deep_copy,
        blank_patch=blank_patch,
    )

def infer_combat_context(
    state: Dict[str, Any],
    actor: str,
    action_type: str,
    text: str,
) -> Dict[str, Any]:
    return _infer_combat_context(
        state,
        actor,
        action_type,
        text,
        normalized_eval_text=normalized_eval_text,
        normalize_combat_meta=normalize_combat_meta,
        combat_narrative_hints=COMBAT_NARRATIVE_HINTS,
    )

def patch_has_combat_signal(patch: Dict[str, Any]) -> bool:
    return _patch_has_combat_signal(patch)

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
    return _update_combat_meta_after_turn(
        state,
        actor=actor,
        action_type=action_type,
        input_text=input_text,
        story_text=story_text,
        patch=patch,
        combat_context=combat_context,
        resolution_summary=resolution_summary,
        normalize_combat_meta=normalize_combat_meta,
        utc_now=utc_now,
        normalized_eval_text=normalized_eval_text,
        patch_has_combat_signal=patch_has_combat_signal,
        combat_narrative_hints=COMBAT_NARRATIVE_HINTS,
        combat_end_hints=COMBAT_END_HINTS,
        make_id=make_id,
        first_sentences=first_sentences,
        deep_copy=deep_copy,
    )

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

def generate_character_attribute_weights(campaign: Dict[str, Any], slot_name: str, summary: Dict[str, Any]) -> Dict[str, Any]:
    return setup_attributes.generate_character_attribute_weights(
        campaign, slot_name, summary, call_ollama_schema=call_ollama_schema
    )

def default_character_setup_node() -> Dict[str, Any]:
    return campaign_state_shape.default_character_setup_node(
        build_character_question_queue=build_character_question_queue,
    )

def campaign_repository() -> CampaignRepository:
    return campaign_persistence.resolve_campaign_repository(
        configured=_STATE_ENGINE_DEPS.campaign_repository,
        data_dir=DATA_DIR,
        campaigns_dir=CAMPAIGNS_DIR,
    )

def save_json(path: str, payload: Dict[str, Any]) -> None:
    campaign_persistence.save_json(campaign_repository(), path, payload)

def load_json(path: str) -> Dict[str, Any]:
    return campaign_persistence.load_json(campaign_repository(), path)

def campaign_path(campaign_id: str) -> str:
    return campaign_persistence.campaign_path(campaign_repository(), campaign_id)

def list_campaign_ids() -> List[str]:
    return campaign_persistence.list_campaign_ids(campaign_repository())

def attribute_cap_for_campaign(campaign: Dict[str, Any]) -> int:
    return max(1, int(world_attribute_scale(campaign)["max"] or 10))

campaign_slots = campaign_views.campaign_slots
display_name_for_slot = campaign_views.display_name_for_slot
active_party = campaign_views.active_party

def _campaign_view_ports() -> campaign_views.CampaignViewPorts:
    live_state = _STATE_ENGINE_DEPS.live_state_service or _default_live_state_service
    return campaign_views.CampaignViewPorts(
        normalize_campaign=normalize_campaign,
        deep_copy=deep_copy,
        derive_scene_name=derive_scene_name,
        normalize_character_state=normalize_character_state,
        blank_character_state=blank_character_state,
        normalize_class_current=normalize_class_current,
        next_character_xp_for_level=next_character_xp_for_level,
        resource_name_for_character=resource_name_for_character,
        clamp=clamp,
        normalize_world_time=normalize_world_time,
        build_world_question_state=build_world_question_state,
        build_character_question_state=build_character_question_state,
        progress_payload=progress_payload,
        setup_global_progress=setup_global_progress,
        setup_chapter_config=setup_chapter_config,
        setup_question_chapter_key=setup_question_chapter_key,
        setup_chapter_progress=setup_chapter_progress,
        setup_phase_display=setup_phase_display,
        setup_summary_preview=campaign_views.setup_summary_preview,
        normalize_requests_payload=normalize_requests_payload,
        blank_patch=blank_patch,
        public_turn=public_turn,
        live_snapshot=live_state.live_snapshot,
    )

compact_conditions = campaign_views.compact_conditions

def ollama_request_seed() -> Optional[int]:
    return ollama_adapter().request_seed()

def ollama_adapter() -> OllamaAdapter:
    configured = _STATE_ENGINE_DEPS.ollama_adapter
    if isinstance(configured, OllamaAdapter):
        return configured
    return OllamaAdapter(
        OllamaSettings(
            url=OLLAMA_URL,
            model=OLLAMA_MODEL,
            timeout_sec=OLLAMA_TIMEOUT_SEC,
            seed=OLLAMA_SEED,
            temperature=OLLAMA_TEMPERATURE,
            num_ctx=OLLAMA_NUM_CTX,
            repeat_penalty=OLLAMA_REPEAT_PENALTY,
            repeat_last_n=OLLAMA_REPEAT_LAST_N,
        )
    )

def call_ollama_text(system: str, user: str) -> str:
    return ollama_adapter().chat(
        system,
        user,
        timeout=max(30, OLLAMA_TIMEOUT_SEC),
        temperature=0.35,
        num_ctx=4096,
    )

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

infer_injury_severity = _extraction_injuries.infer_injury_severity

infer_injury_effects = _extraction_injuries.infer_injury_effects

clean_auto_injury_title = _extraction_injuries.clean_auto_injury_title

extract_auto_story_injuries = _extraction_injuries.extract_auto_story_injuries

def sorted_npc_codex_entries(*args: Any, **kwargs: Any):
    return _canon_extractor_service.sorted_npc_codex_entries(*args, **kwargs)

def build_npc_codex_summary(*args: Any, **kwargs: Any):
    return _canon_extractor_service.build_npc_codex_summary(*args, **kwargs)

def sorted_world_profiles(*args: Any, **kwargs: Any):
    return _canon_extractor_service.sorted_world_profiles(*args, **kwargs)

def build_race_codex_summary(*args: Any, **kwargs: Any):
    return _canon_extractor_service.build_race_codex_summary(*args, **kwargs)

def build_beast_codex_summary(*args: Any, **kwargs: Any):
    return _canon_extractor_service.build_beast_codex_summary(*args, **kwargs)

def build_world_element_summary(*args: Any, **kwargs: Any):
    return _canon_extractor_service.build_world_element_summary(*args, **kwargs)

def build_extractor_context_packet(*args: Any, **kwargs: Any):
    return _canon_extractor_service.build_extractor_context_packet(*args, **kwargs)

def normalize_extractor_output_patch(*args: Any, **kwargs: Any):
    return _canon_extractor_service.normalize_extractor_output_patch(*args, **kwargs)

resolve_extractor_conflicts = _extraction_heuristics.resolve_extractor_conflicts

make_extraction_candidate = _extraction_heuristics.make_extraction_candidate

candidate_status_rank = _extraction_heuristics.candidate_status_rank

item_name_in_character_inventory = _extraction_heuristics.item_name_in_character_inventory

extract_environment_item_mentions = _extraction_heuristics.extract_environment_item_mentions

build_heuristic_candidates = _extraction_heuristics.build_heuristic_candidates

classify_heuristic_candidate = _extraction_heuristics.classify_heuristic_candidate

split_candidates = _extraction_heuristics.split_candidates

append_extraction_quarantine = _extraction_quarantine.append_extraction_quarantine

safe_candidates_to_patch = _extraction_heuristics.safe_candidates_to_patch

merge_safe_patch_additive = _extraction_heuristics.merge_safe_patch_additive

def call_canon_extractor(*args: Any, **kwargs: Any):
    return _canon_extractor_service.call_canon_extractor(*args, **kwargs)

def scene_name_from_state(*args: Any, **kwargs: Any):
    return _npc_extractor_service.scene_name_from_state(*args, **kwargs)

def existing_pc_aliases(*args: Any, **kwargs: Any):
    return _npc_extractor_service.existing_pc_aliases(*args, **kwargs)

def is_generic_npc_name(*args: Any, **kwargs: Any):
    return _npc_extractor_service.is_generic_npc_name(*args, **kwargs)

def resolve_npc_scene_hint(*args: Any, **kwargs: Any):
    return _npc_extractor_service.resolve_npc_scene_hint(*args, **kwargs)

def best_matching_npc_id(*args: Any, **kwargs: Any):
    return _npc_extractor_service.best_matching_npc_id(*args, **kwargs)

def npc_relevance_score(*args: Any, **kwargs: Any):
    return _npc_extractor_service.npc_relevance_score(*args, **kwargs)

def pick_more_specific_text(*args: Any, **kwargs: Any):
    return _npc_extractor_service.pick_more_specific_text(*args, **kwargs)

def apply_npc_upserts(*args: Any, **kwargs: Any):
    return _npc_extractor_service.apply_npc_upserts(*args, **kwargs)

def build_npc_extractor_context_packet(*args: Any, **kwargs: Any):
    return _npc_extractor_service.build_npc_extractor_context_packet(*args, **kwargs)

def call_npc_extractor(*args: Any, **kwargs: Any):
    return _npc_extractor_service.call_npc_extractor(*args, **kwargs)

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
    try:
        return ollama_adapter().chat(
            system,
            user,
            format_schema=format_schema,
            timeout=request_timeout,
            temperature=temperature,
            repeat_penalty=repeat_penalty,
        )
    except RuntimeError as exc:
        message = str(exc)
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
        raise

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

def setup_ai_copy_dependencies() -> setup_ai_copy.SetupAiCopyDependencies:
    from app.services import turn_engine as _turn_engine

    return setup_ai_copy.SetupAiCopyDependencies(
        call_ollama_text=call_ollama_text,
        display_name_for_slot=display_name_for_slot,
        looks_non_german_text=_turn_engine.looks_non_german_text,
        utc_now=utc_now,
    )

def setup_payload_dependencies() -> setup_payloads.SetupPayloadDependencies:
    return setup_payloads.SetupPayloadDependencies(
        deep_copy=deep_copy,
        display_name_for_slot=display_name_for_slot,
        extract_text_answer=extract_text_answer,
        is_host=is_host,
        current_question_id=current_question_id,
        progress_payload=progress_payload,
        normalize_campaign_length_choice=normalize_campaign_length_choice,
        normalize_ruleset_choice=normalize_ruleset_choice,
    )

def setup_summary_state_dependencies() -> setup_summaries.CharacterSummaryStateDependencies:
    return setup_summaries.CharacterSummaryStateDependencies(
        clean_creator_item_name=clean_creator_item_name,
        derive_age_stage=derive_age_stage,
        enable_legacy_shadow_writeback=ENABLE_LEGACY_SHADOW_WRITEBACK,
        generate_character_attribute_weights=generate_character_attribute_weights,
        infer_age_years=infer_age_years,
        level_one_attribute_budget=level_one_attribute_budget,
        level_one_attribute_cap=level_one_attribute_cap,
        level_one_attributes_from_weights=level_one_attributes_from_weights,
        normalize_attribute_weight_pool=normalize_attribute_weight_pool,
        normalize_class_current=normalize_class_current,
        normalize_creator_item_list=normalize_creator_item_list,
        normalize_world_time=normalize_world_time,
        normalized_eval_text=normalized_eval_text,
        reconcile_canonical_resources=reconcile_canonical_resources,
        reconcile_creator_inventory_items=reconcile_creator_inventory_items,
        rebuild_character_derived=rebuild_character_derived,
        refresh_skill_progression=refresh_skill_progression,
        strip_legacy_shadow_fields=strip_legacy_shadow_fields,
        sync_scars_into_appearance=sync_scars_into_appearance,
        write_legacy_shadow_fields=write_legacy_shadow_fields,
    )

def clean_setup_ai_copy(text: str) -> str:
    return setup_ai_copy.clean_setup_ai_copy(text)

def is_bad_setup_ai_copy(text: str) -> bool:
    return setup_ai_copy.is_bad_setup_ai_copy(text)

def generate_setup_ai_copy(campaign: Dict[str, Any], question: Dict[str, Any], *, setup_type: str, slot_name: Optional[str] = None) -> str:
    return setup_ai_copy.generate_setup_ai_copy(campaign, question, setup_type=setup_type, slot_name=slot_name, deps=setup_ai_copy_dependencies())

def get_persisted_question_ai_copy(setup_node: Dict[str, Any], question_id: str) -> str:
    return setup_ai_copy.get_persisted_question_ai_copy(setup_node, question_id)

def store_question_ai_copy(setup_node: Dict[str, Any], question_id: str, ai_copy: str, source: str) -> str:
    return setup_ai_copy.store_question_ai_copy(setup_node, question_id, ai_copy, source, deps=setup_ai_copy_dependencies())

def ensure_question_ai_copy(campaign: Dict[str, Any], *, setup_type: str, question_id: str, slot_name: Optional[str] = None) -> str:
    return setup_ai_copy.ensure_question_ai_copy(campaign, setup_type=setup_type, question_id=question_id, slot_name=slot_name, deps=setup_ai_copy_dependencies())

def build_setup_option_context(campaign: Dict[str, Any], *, setup_type: str, slot_name: Optional[str] = None, setup_node: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    return setup_payloads.build_setup_option_context(campaign, setup_type=setup_type, slot_name=slot_name, setup_node=setup_node, deps=setup_payload_dependencies())

def append_context_hint(base: str, hint: str) -> str:
    return setup_payloads.append_context_hint(base, hint)

def dynamic_option_description(question_id: str, option: str, context: Dict[str, str]) -> str:
    return setup_payloads.dynamic_option_description(question_id, option, context)

def dynamic_other_hint(question: Dict[str, Any], context: Dict[str, str]) -> str:
    return setup_payloads.dynamic_other_hint(question, context)

def build_dynamic_option_entries(question: Dict[str, Any], *, context: Dict[str, str]) -> List[Dict[str, str]]:
    return setup_payloads.build_dynamic_option_entries(question, context=context)

def build_question_payload(question: Dict[str, Any], *, campaign: Dict[str, Any], setup_type: str, ai_copy: str, slot_name: Optional[str] = None, setup_node: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return setup_payloads.build_question_payload(question, campaign=campaign, setup_type=setup_type, ai_copy=ai_copy, slot_name=slot_name, setup_node=setup_node, deps=setup_payload_dependencies())

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
    return setup_randomizer.validate_answer_payload(question, answer)

def fallback_random_text(question_id: str, *, setup_type: str, campaign: Dict[str, Any], slot_name: Optional[str] = None) -> str:
    return setup_randomizer.fallback_random_text(question_id, setup_type=setup_type, campaign=campaign, slot_name=slot_name, deps=setup_helper_dependencies())

def fallback_random_answer_payload(campaign: Dict[str, Any], question: Dict[str, Any], *, setup_type: str, slot_name: Optional[str] = None) -> Dict[str, Any]:
    return setup_randomizer.fallback_random_answer_payload(campaign, question, setup_type=setup_type, slot_name=slot_name, deps=setup_helper_dependencies())

def generate_random_setup_answer(campaign: Dict[str, Any], question: Dict[str, Any], *, setup_type: str, slot_name: Optional[str] = None, setup_node: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return setup_randomizer.generate_random_setup_answer(campaign, question, setup_type=setup_type, slot_name=slot_name, setup_node=setup_node, deps=setup_helper_dependencies())

def store_setup_answer(setup_node: Dict[str, Any], question: Dict[str, Any], stored: Any, *, player_id: Optional[str], source: str = "manual") -> None:
    return setup_randomizer.store_setup_answer(setup_node, question, stored, player_id=player_id, source=source, deps=setup_helper_dependencies())

def setup_answer_to_input_payload(question: Dict[str, Any], stored: Any) -> Dict[str, Any]:
    return setup_randomizer.setup_answer_to_input_payload(question, stored)

def setup_answer_preview_text(question: Dict[str, Any], stored: Any) -> str:
    return setup_randomizer.setup_answer_preview_text(question, stored)

def build_random_setup_preview(campaign: Dict[str, Any], setup_node: Dict[str, Any], question_map: Dict[str, Dict[str, Any]], *, setup_type: str, player_id: Optional[str], slot_name: Optional[str] = None, mode: str, question_id: Optional[str] = None, preview_answers: Optional[List["SetupAnswerIn"]] = None) -> List[Dict[str, Any]]:
    return setup_randomizer.build_random_setup_preview(campaign, setup_node, question_map, setup_type=setup_type, player_id=player_id, slot_name=slot_name, mode=mode, question_id=question_id, preview_answers=preview_answers, deps=setup_helper_dependencies())

def apply_random_setup_preview(campaign: Dict[str, Any], setup_node: Dict[str, Any], question_map: Dict[str, Dict[str, Any]], preview_answers: List["SetupAnswerIn"], *, player_id: Optional[str]) -> int:
    return setup_randomizer.apply_random_setup_preview(campaign, setup_node, question_map, preview_answers, player_id=player_id, deps=setup_helper_dependencies())

def finalize_world_setup(campaign: Dict[str, Any], player_id: Optional[str]) -> None:
    setup_finalization.finalize_world_setup(campaign, player_id, deps=setup_helper_dependencies())

def finalize_character_setup(campaign: Dict[str, Any], slot_name: str) -> Optional[Dict[str, Any]]:
    return setup_finalization.finalize_character_setup(campaign, slot_name, deps=setup_helper_dependencies())

def build_world_summary(campaign: Dict[str, Any]) -> Dict[str, Any]:
    return setup_summaries.build_world_summary(campaign, deps=setup_helper_dependencies())

def build_character_summary(campaign: Dict[str, Any], slot_name: str) -> Dict[str, Any]:
    return setup_summaries.build_character_summary(campaign, slot_name, deps=setup_helper_dependencies())

def apply_world_summary_to_boards(campaign: Dict[str, Any], updated_by: Optional[str]) -> None:
    campaign_state_shape.apply_world_summary_to_boards(
        campaign,
        updated_by,
        ports=campaign_state_shape.WorldSummaryBoardPorts(
            make_id=make_id,
            utc_now=utc_now,
        ),
    )


def initialize_dynamic_slots(campaign: Dict[str, Any], player_count: int) -> None:
    campaign_state_shape.initialize_dynamic_slots(
        campaign,
        player_count,
        ports=campaign_state_shape.DynamicSlotPorts(
            slot_id=slot_id,
            blank_character_state=blank_character_state,
            default_character_setup_node=default_character_setup_node,
        ),
    )


def apply_character_summary_to_state(campaign: Dict[str, Any], slot_name: str) -> None:
    setup_summaries.apply_character_summary_to_state(campaign, slot_name, deps=setup_summary_state_dependencies())

def _campaign_slot_migration_ports() -> campaign_slot_migration.CampaignSlotMigrationPorts:
    return campaign_slot_migration.CampaignSlotMigrationPorts(
        slot_id=slot_id,
        deep_copy=deep_copy,
        blank_character_state=blank_character_state,
        default_setup=default_setup,
        normalize_campaign_length_choice=normalize_campaign_length_choice,
        legacy_select_answer_payload=legacy_select_answer_payload,
        normalize_resource_name=normalize_resource_name,
        build_world_summary=build_world_summary,
        extract_text_answer=extract_text_answer,
        parse_earth_items=parse_earth_items,
        normalize_class_current=normalize_class_current,
        default_character_setup_node=default_character_setup_node,
        build_character_summary=build_character_summary,
    )

def _campaign_normalization_ports() -> campaign_normalization.CampaignNormalizationPorts:
    return campaign_normalization.CampaignNormalizationPorts(
        deep_copy=deep_copy,
        initial_state=INITIAL_STATE,
        is_legacy_campaign=campaign_slot_migration.is_legacy_campaign,
        migrate_campaign_to_dynamic_slots=lambda campaign: campaign_slot_migration.migrate_campaign_to_dynamic_slots(
            campaign,
            ports=_campaign_slot_migration_ports(),
        ),
        default_intro_state=default_intro_state,
        default_setup=default_setup,
        default_character_setup_node=default_character_setup_node,
        build_world_question_queue=build_world_question_queue,
        build_character_question_queue=build_character_question_queue,
        normalize_world_time=normalize_world_time,
        normalize_world_settings=normalize_world_settings,
        normalize_meta_timing=normalize_meta_timing,
        normalize_combat_meta=normalize_combat_meta,
        normalize_attribute_influence_meta=normalize_attribute_influence_meta,
        normalize_extraction_quarantine_meta=normalize_extraction_quarantine_meta,
        normalize_meta_migrations=normalize_meta_migrations,
        active_pacing_profile=active_pacing_profile,
        milestone_state_for_turn=milestone_state_for_turn,
        normalize_world_codex_structures=normalize_world_codex_structures,
        normalize_npc_codex_state=normalize_npc_codex_state,
        seed_npc_codex_from_story_cards=seed_npc_codex_from_story_cards,
        ensure_world_codex_from_setup=ensure_world_codex_from_setup,
        blank_character_state=blank_character_state,
        normalize_character_state=normalize_character_state,
        normalize_element_id_list=normalize_element_id_list,
        normalize_class_current=normalize_class_current,
        resolve_class_element_id=resolve_class_element_id,
        resource_name_for_character=resource_name_for_character,
        normalize_dynamic_skill_state=normalize_dynamic_skill_state,
        normalize_skill_elements_for_world=normalize_skill_elements_for_world,
        reconcile_creator_inventory_items=reconcile_creator_inventory_items,
        initialize_dynamic_slots=initialize_dynamic_slots,
        run_legacy_normalize_backfill=run_legacy_normalize_backfill,
        compute_turn_budget_estimates=compute_turn_budget_estimates,
    )

def normalize_campaign(campaign: Dict[str, Any]) -> Dict[str, Any]:
    return campaign_normalization.normalize_campaign(campaign, ports=_campaign_normalization_ports())

def load_campaign(campaign_id: str) -> Dict[str, Any]:
    return campaign_persistence.load_campaign(
        campaign_id,
        ports=campaign_persistence.CampaignLoadPorts(
            repository=campaign_repository(),
            normalize_campaign=normalize_campaign,
        ),
    )

def save_campaign(
    campaign: Dict[str, Any],
    *,
    reason: str = "campaign_updated",
    trace_ctx: Optional[Dict[str, Any]] = None,
) -> None:
    campaign_persistence.save_campaign(
        campaign,
        reason=reason,
        trace_ctx=trace_ctx,
        ports=campaign_persistence.CampaignSavePorts(
            repository=campaign_repository(),
            normalize_campaign=normalize_campaign,
            utc_now=utc_now,
            emit_turn_phase_event=emit_turn_phase_event,
            turn_flow_error=turn_flow_error,
            live_state_service=_STATE_ENGINE_DEPS.live_state_service or _default_live_state_service,
            logger=_STATE_ENGINE_DEPS.logger,
        ),
    )

def active_turns(campaign: Dict[str, Any]) -> List[Dict[str, Any]]:
    return campaign_views.active_turns(campaign)

def is_host(campaign: Dict[str, Any], player_id: Optional[str]) -> bool:
    return campaign_views.is_host(campaign, player_id)

def is_campaign_player(campaign: Dict[str, Any], player_id: Optional[str]) -> bool:
    return campaign_views.is_campaign_player(campaign, player_id)

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
    return setup_payloads.build_world_question_state(campaign, viewer_id, deps=setup_payload_dependencies())

def build_character_question_state(campaign: Dict[str, Any], slot_name: str) -> Optional[Dict[str, Any]]:
    return setup_payloads.build_character_question_state(campaign, slot_name, deps=setup_payload_dependencies())

def build_viewer_context(campaign: Dict[str, Any], player_id: Optional[str]) -> Dict[str, Any]:
    return campaign_views.build_viewer_context(campaign, player_id, ports=_campaign_view_ports())

def build_setup_runtime(campaign: Dict[str, Any], viewer_id: Optional[str]) -> Dict[str, Any]:
    return campaign_views.build_setup_runtime(campaign, viewer_id, ports=_campaign_view_ports())

def build_campaign_view(campaign: Dict[str, Any], viewer_id: Optional[str]) -> Dict[str, Any]:
    return campaign_views.build_campaign_view(campaign, viewer_id, ports=_campaign_view_ports())

def _memory_ports() -> memory_service.MemoryPorts:
    return memory_service.MemoryPorts(
        active_turns=active_turns,
        active_party=active_party,
        display_name_for_slot=display_name_for_slot,
        is_slot_id=is_slot_id,
        blank_patch=blank_patch,
        canonical_scene_id=canonical_scene_id,
        derive_scene_name=derive_scene_name,
        extract_descriptive_scene_name=extract_descriptive_scene_name,
        extract_scene_candidates=extract_scene_candidates,
        is_generic_scene_identifier=is_generic_scene_identifier,
        normalized_eval_text=normalized_eval_text,
        compact_conditions=compact_conditions,
        normalize_character_state=normalize_character_state,
        world_attribute_scale=world_attribute_scale,
        element_core_names=list(ELEMENT_CORE_NAMES),
        build_world_element_summary=build_world_element_summary,
        build_race_codex_summary=build_race_codex_summary,
        build_beast_codex_summary=build_beast_codex_summary,
        build_npc_codex_summary=build_npc_codex_summary,
        call_ollama_text=call_ollama_text,
        utc_now=utc_now,
    )

def remember_recent_story(campaign: Dict[str, Any]) -> None:
    memory_service.remember_recent_story(campaign, ports=_memory_ports())

def rebuild_memory_summary(campaign: Dict[str, Any]) -> None:
    memory_service.rebuild_memory_summary(campaign, ports=_memory_ports())

def build_context_packet(
    campaign: Dict[str, Any],
    state: Dict[str, Any],
    actor: str,
    action_type: str,
) -> str:
    return memory_service.build_context_packet(campaign, state, actor, action_type, ports=_memory_ports())

is_suspicious_story_text = _extraction_heuristics.is_suspicious_story_text

extract_story_target_evidence = _extraction_heuristics.extract_story_target_evidence

clean_auto_ability_name = _extraction_abilities.clean_auto_ability_name

clean_auto_item_name = _extraction_items.clean_auto_item_name

actor_relevant_story_sentences = _extraction_items.actor_relevant_story_sentences

infer_item_slot_from_text = _extraction_items.infer_item_slot_from_text

build_auto_item_stub = _extraction_items.build_auto_item_stub

clean_creator_item_name = _extraction_items.clean_creator_item_name

item_id_from_name = _extraction_items.item_id_from_name

materialize_inventory_item = _extraction_items.materialize_inventory_item

normalize_creator_item_list = _extraction_items.normalize_creator_item_list

reconcile_creator_inventory_items = _extraction_items.reconcile_creator_inventory_items

infer_auto_skill_tags = _extraction_abilities.infer_auto_skill_tags

infer_auto_class_tags = _extraction_classes.infer_auto_class_tags

normalize_class_rank_text = _extraction_classes.normalize_class_rank_text

clean_auto_class_name = _extraction_classes.clean_auto_class_name

extract_auto_class_change = _extraction_classes.extract_auto_class_change

extract_auto_learned_abilities = _extraction_abilities.extract_auto_learned_abilities

extract_auto_story_item_events = _extraction_items.extract_auto_story_item_events

extract_auto_story_items = _extraction_items.extract_auto_story_items

story_sentences_for_actor = _extraction_abilities.story_sentences_for_actor

build_turn_journal_notes = _extraction_abilities.build_turn_journal_notes

inject_turn_story_journal = _extraction_abilities.inject_turn_story_journal

inject_story_unlock_abilities = _extraction_abilities.inject_story_unlock_abilities

materialize_character_ability = _extraction_abilities.materialize_character_ability

inject_story_items = _extraction_items.inject_story_items

inject_story_injuries = _extraction_injuries.inject_story_injuries

materialize_story_items_from_turn_history = _extraction_items.materialize_story_items_from_turn_history

materialize_story_abilities_from_turn_history = _extraction_abilities.materialize_story_abilities_from_turn_history

def run_legacy_normalize_backfill(campaign: Dict[str, Any]) -> None:
    """Optional legacy heuristic backfill path. Disabled by default."""
    materialize_story_items_from_turn_history(campaign)
    materialize_story_abilities_from_turn_history(campaign)
    memory_service.reconcile_scene_ids_with_story(campaign, ports=_memory_ports())

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

def intro_state(campaign: Dict[str, Any]) -> Dict[str, Any]:
    return campaign_lifecycle.intro_state(campaign)

def can_start_adventure(campaign: Dict[str, Any]) -> bool:
    return campaign_lifecycle.can_start_adventure(campaign)

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
    return campaign_lifecycle.new_player(display_name)

def create_campaign_record(
    title: str,
    display_name: str,
    *,
    legacy_state: Optional[Dict[str, Any]] = None,
    imported_turns: Optional[List[Dict[str, Any]]] = None,
    legacy_flag: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return campaign_lifecycle.create_campaign_record(
        title,
        display_name,
        legacy_state=legacy_state,
        imported_turns=imported_turns,
        legacy_flag=legacy_flag,
        ports=campaign_lifecycle.CampaignCreatePorts(
            make_join_code=make_join_code,
            deep_copy=deep_copy,
            initial_state=INITIAL_STATE,
            default_boards=default_boards,
            default_setup=default_setup,
            normalize_campaign=normalize_campaign,
            current_question_id=current_question_id,
            ensure_question_ai_copy=ensure_question_ai_copy,
            remember_recent_story=remember_recent_story,
            rebuild_memory_summary=rebuild_memory_summary,
            save_campaign=save_campaign,
        ),
    )

def ensure_campaign_storage() -> None:
    campaign_lifecycle.ensure_campaign_storage(
        ports=campaign_lifecycle.CampaignStoragePorts(
            data_dir=DATA_DIR,
            campaigns_dir=CAMPAIGNS_DIR,
            legacy_state_path=LEGACY_STATE_PATH,
            ensure_storage_dirs=ensure_storage_dirs,
            list_campaign_ids=list_campaign_ids,
            load_json=load_json,
            deep_copy=deep_copy,
            make_turn_id=lambda: make_id("turn"),
            blank_patch=blank_patch,
            create_campaign_record=create_campaign_record,
        )
    )

def find_campaign_by_join_code(join_code: str) -> Optional[Dict[str, Any]]:
    return campaign_lifecycle.find_campaign_by_join_code(
        join_code,
        ports=campaign_lifecycle.JoinCodeLookupPorts(
            list_campaign_ids=list_campaign_ids,
            campaign_path=campaign_path,
            load_campaign=load_campaign,
        ),
    )

def touch_player(campaign: Dict[str, Any], player_id: str) -> None:
    campaign_lifecycle.touch_player(campaign, player_id)

def authenticate_player(
    campaign: Dict[str, Any],
    player_id: Optional[str],
    player_token: Optional[str],
    *,
    required: bool = True,
) -> Optional[Dict[str, Any]]:
    return campaign_lifecycle.authenticate_player(
        campaign,
        player_id,
        player_token,
        required=required,
    )

def require_host(campaign: Dict[str, Any], player_id: Optional[str]) -> None:
    campaign_lifecycle.require_host(campaign, player_id)

def require_claim(campaign: Dict[str, Any], player_id: str, actor: str) -> None:
    campaign_lifecycle.require_claim(campaign, player_id, actor)


_configure_extractor_service_ports()
