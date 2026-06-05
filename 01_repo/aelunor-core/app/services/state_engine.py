import hashlib
import json
import math
import os
import random
import re
import secrets
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher
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
    CONTEXT_RESPONSE_SCHEMA,
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
    CONTEXT_META_DRIFT_MARKERS,
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
from app.services.campaigns import lifecycle as campaign_lifecycle
from app.services.campaigns import normalization as campaign_normalization
from app.services.campaigns import persistence as campaign_persistence
from app.services.campaigns import state_shape as campaign_state_shape
from app.services.campaigns import views as campaign_views
from app.services.migrations import campaign_slots as campaign_slot_migration
from app.services import live_state_service as _default_live_state_service
from app.services.canon import extractor as _canon_extractor_service
from app.services.canon import npc_extractor as _npc_extractor_service
from app.services.extraction import abilities as _extraction_abilities
from app.services.extraction import classes as _extraction_classes
from app.services.extraction import heuristics as _extraction_heuristics
from app.services.extraction import injuries as _extraction_injuries
from app.services.extraction import items as _extraction_items
from app.services.extraction import quarantine as _extraction_quarantine
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
    canonical_resource_field_name,
    ingest_legacy_resources_into_canonical,
    legacy_misc_resource_deltas_from_update,
    legacy_misc_resources_set_from_payload,
    reconcile_canonical_resources,
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
    active_faction_ids as _active_faction_ids,
    appearance_event_id as _appearance_event_id,
    default_appearance_profile,
    format_appearance_message as _format_appearance_message,
    record_appearance_change as _record_appearance_change,
)
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
        skill_id_from_name=skill_id_from_name,
        normalize_dynamic_skill_state=normalize_dynamic_skill_state,
    )
    _extraction_heuristics.configure(
        skill_id_from_name=skill_id_from_name,
        skill_rank_sort_value=skill_rank_sort_value,
        normalize_dynamic_skill_state=normalize_dynamic_skill_state,
    )
    _canon_extractor_service.configure(call_ollama_schema=call_ollama_schema)
    _npc_extractor_service.configure(
        call_ollama_schema=call_ollama_schema,
        class_rank_sort_value=class_rank_sort_value,
        normalize_skill_store=normalize_skill_store,
        normalize_dynamic_skill_state=normalize_dynamic_skill_state,
        merge_dynamic_skill=merge_dynamic_skill,
    )


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
    _configure_extractor_service_ports()
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
    'build_character_sheet_view',
    'build_character_summary',
    'build_combat_scaling_context',
    'build_context_knowledge_index',
    'build_context_packet',
    'build_context_result_payload',
    'build_context_result_via_llm',
    'build_npc_sheet_view',
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
    'log_board_revision',
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

def skill_rank_for_level(level: int) -> str:
    return _skill_rank_for_level(level, skill_rank_thresholds=SKILL_RANK_THRESHOLDS)

def next_skill_xp_for_level(level: int) -> int:
    return _next_skill_xp_for_level(level)

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

clean_extracted_skill_name = _extraction_abilities.clean_extracted_skill_name

split_extracted_skill_names = _extraction_abilities.split_extracted_skill_names

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
    return _normalize_skill_rank(value, skill_ranks=SKILL_RANKS)

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
    skill["growth_potential"] = _normalize_growth_potential(skill.get("growth_potential"))
    skill["power_rating"] = _normalize_power_rating(
        skill.get("power_rating"),
        rank=skill["rank"],
        level=int(skill.get("level", 1) or 1),
        skill_rank_sort_value=skill_rank_sort_value,
        clamp=clamp,
    )
    skill["manifestation_source"] = _normalize_optional_text(skill.get("manifestation_source"))
    skill["category"] = _normalize_optional_lower_text(skill.get("category"))
    skill["class_affinity"] = _normalize_optional_strings(skill.get("class_affinity"))
    skill["elements"], skill["element_primary"] = _normalize_skill_element_fields(skill.get("elements"), skill.get("element_primary"))
    skill["element_synergies"] = _normalize_optional_unique_strings(skill.get("element_synergies"))
    skill["cost"] = _normalize_skill_cost(skill.get("cost"), resource_name=resource_name)
    skill["price"] = str(skill.get("price", "") or "").strip() or None
    skill["cooldown_turns"] = _normalize_cooldown_turns(skill.get("cooldown_turns"))
    skill["unlocked_from"] = str(skill.get("unlocked_from") or unlocked_from or "Story").strip() or "Story"
    skill["synergy_notes"] = _normalize_optional_text(skill.get("synergy_notes"))
    skill["xp"], skill["next_xp"], skill["mastery"] = _normalize_skill_progression_fields(
        skill,
        next_skill_xp_for_level=next_skill_xp_for_level,
        clamp=clamp,
    )
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

sentence_mentions_actor_name = _extraction_items.sentence_mentions_actor_name

def effective_skill_progress_multiplier(character: Dict[str, Any], skill: Dict[str, Any], world_settings: Optional[Dict[str, Any]] = None) -> float:
    world_settings = world_settings or {}
    current_class = normalize_class_current(character.get("class_current"))
    if not current_class:
        return float(world_settings.get("onclass_xp_multiplier", 1.0) or 1.0)
    if class_affinity_match(skill.get("tags") or [], current_class.get("affinity_tags") or []):
        return float(world_settings.get("onclass_xp_multiplier", 1.0) or 1.0)
    return float(world_settings.get("offclass_xp_multiplier", 0.7) or 0.7)

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
    return campaign_lifecycle.default_boards(player_id)

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

def appearance_event_id(slot_name: str, kind: str, source: str, turn_number: int, absolute_day: int, new_value: str) -> str:
    return _appearance_event_id(slot_name, kind, source, turn_number, absolute_day, new_value)

def format_appearance_message(display_name: str, kind: str, source: str, new_value: str) -> str:
    return _format_appearance_message(display_name, kind, source, new_value)

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
    return _record_appearance_change(
        character,
        slot_name=slot_name,
        turn_number=turn_number,
        absolute_day=absolute_day,
        kind=kind,
        source=source,
        old_value=old_value,
        new_value=new_value,
    )

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
    before_factions = _active_faction_ids(before_character)
    after_factions = _active_faction_ids(after_character)
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

def calculate_attack_rating(character: Dict[str, Any], hand: str, items_db: Dict[str, Any]) -> int:
    return _derived_stats.calculate_attack_rating(
        character,
        hand,
        items_db,
        skill_level_value=skill_level_value,
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
        normalize_skill_state=normalize_skill_state,
        default_skill_state=default_skill_state,
    )

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
        from app.services import turn_engine as _turn_engine

        emit_turn_phase_event(trace_ctx, phase="patch_sanitize", success=True, extra={"stage": "canon_gate"})
        gate_patch = _turn_engine.sanitize_patch(state_after, gate_patch)
        emit_turn_phase_event(trace_ctx, phase="patch_sanitize", success=True, extra={"stage": "canon_gate", "result": "ok"})
        emit_turn_phase_event(trace_ctx, phase="schema_validation", success=True, extra={"stage": "canon_gate"})
        _turn_engine.validate_patch(state_after, gate_patch)
        emit_turn_phase_event(trace_ctx, phase="schema_validation", success=True, extra={"stage": "canon_gate", "result": "ok"})
        emit_turn_phase_event(trace_ctx, phase="patch_apply", success=True, extra={"stage": "canon_gate"})
        state_after = _turn_engine.apply_patch(state_after, gate_patch, attribute_cap=attribute_cap_for_campaign(campaign))
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
    return campaign_views.campaign_slots(campaign)

def player_claim(campaign: Dict[str, Any], player_id: Optional[str]) -> Optional[str]:
    return campaign_views.player_claim(campaign, player_id)

def display_name_for_slot(campaign: Dict[str, Any], slot_name: str) -> str:
    return campaign_views.display_name_for_slot(campaign, slot_name)

def active_party(campaign: Dict[str, Any]) -> List[str]:
    return campaign_views.active_party(campaign)

def expected_setup_slots(campaign: Dict[str, Any]) -> List[str]:
    return campaign_views.expected_setup_slots(campaign)

def setup_slot_statuses(campaign: Dict[str, Any]) -> List[Dict[str, Any]]:
    return campaign_views.setup_slot_statuses(campaign)

def public_player(player_id: str, player: Dict[str, Any]) -> Dict[str, Any]:
    return campaign_views.public_player(player_id, player)

def default_player_diary_entry(player_id: str, display_name: str) -> Dict[str, Any]:
    return campaign_views.default_player_diary_entry(player_id, display_name)

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
        setup_summary_preview=setup_summary_preview,
        normalize_requests_payload=normalize_requests_payload,
        blank_patch=blank_patch,
        public_turn=public_turn,
        live_snapshot=live_state.live_snapshot,
    )

def available_slots(campaign: Dict[str, Any]) -> List[Dict[str, Any]]:
    return campaign_views.available_slots(campaign, ports=_campaign_view_ports())

def compact_conditions(character: Dict[str, Any]) -> List[str]:
    return campaign_views.compact_conditions(character)

def build_party_overview(campaign: Dict[str, Any]) -> List[Dict[str, Any]]:
    return campaign_views.build_party_overview(campaign, ports=_campaign_view_ports())

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

def build_npc_extractor_context_packet(*args: Any, **kwargs: Any):
    return _npc_extractor_service.build_npc_extractor_context_packet(*args, **kwargs)

def call_npc_extractor(*args: Any, **kwargs: Any):
    return _npc_extractor_service.call_npc_extractor(*args, **kwargs)

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
    return campaign_views.build_viewer_context(campaign, player_id, ports=_campaign_view_ports())

def build_setup_runtime(campaign: Dict[str, Any], viewer_id: Optional[str]) -> Dict[str, Any]:
    return campaign_views.build_setup_runtime(campaign, viewer_id, ports=_campaign_view_ports())

def filter_private_diary_content(content: Any, viewer_is_owner: bool) -> str:
    return campaign_views.filter_private_diary_content(content, viewer_is_owner)

def build_public_boards(campaign: Dict[str, Any], viewer_id: Optional[str]) -> Dict[str, Any]:
    return campaign_views.build_public_boards(campaign, viewer_id, ports=_campaign_view_ports())

def build_campaign_view(campaign: Dict[str, Any], viewer_id: Optional[str]) -> Dict[str, Any]:
    return campaign_views.build_campaign_view(campaign, viewer_id, ports=_campaign_view_ports())

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

is_suspicious_story_text = _extraction_heuristics.is_suspicious_story_text

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

extract_story_target_evidence = _extraction_heuristics.extract_story_target_evidence

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
