import logging
import math
import os
import random
import secrets
import time
from difflib import SequenceMatcher
from typing import Any, Dict, List, Literal, Set, Tuple

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.adapters.ollama_config import (
    OLLAMA_ADAPTER,
    OLLAMA_MODEL,
    OLLAMA_NUM_CTX,
    OLLAMA_REPEAT_LAST_N,
    OLLAMA_REPEAT_PENALTY,
    OLLAMA_SEED,
    _OLLAMA_SEED_RAW,
    OLLAMA_TEMPERATURE,
    OLLAMA_TIMEOUT_SEC,
    OLLAMA_URL,
)
from app.adapters.llm_config import LLM_ADAPTER, LLM_PROVIDER
from app.catalogs.runtime_catalogs import (
    CANON_EXTRACTOR_SCHEMA,
    CATALOG_VERSION,
    CHARACTER_FORM_CATALOG,
    CHARACTER_QUESTION_MAP,
    INITIAL_STATE,
    PROGRESSION_EXTRACTOR_SCHEMA,
    PROMPTS,
    RESPONSE_SCHEMA,
    SETUP_CATALOG,
    SYSTEM_PROMPT,
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
    BASE_DIR,
    CAMPAIGNS_DIR,
    DATA_DIR,
    LEGACY_STATE_PATH,
    RUNTIME_CONFIG,
    STATIC_DIR,
    UI_V1_ASSETS_DIR,
    UI_V1_DIST_DIR,
    ensure_storage_dirs,
)
from app.dependencies.factories import (
    build_boards_service_dependencies,
    build_campaign_service_dependencies,
    build_claim_service_dependencies,
    build_context_service_dependencies,
    build_presence_service_dependencies,
    build_setup_service_dependencies,
    build_sheets_service_dependencies,
    build_turn_service_dependencies,
)
from app.helpers import setup_helpers
from app.repositories.campaign_repository import CampaignRepository
from app.routers import boards as boards_router_module
from app.routers import campaigns as campaigns_router_module
from app.routers import claim as claim_router_module
from app.routers import context as context_router_module
from app.routers import presence as presence_router_module
from app.routers import setup as setup_router_module
from app.routers import sheets as sheets_router_module
from app.routers import turns as turns_router_module
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
    TURN_MODE_GUIDE,
    TURN_RESPONSE_JSON_CONTRACT,
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
from app.schemas.api import (
    AuthorsNotePatchIn,
    CampaignCreateIn,
    CampaignMetaPatchIn,
    ClassUnlockIn,
    ContextQueryIn,
    FactionJoinIn,
    JoinCampaignIn,
    PlotEssentialsPatchIn,
    PlayerDiaryPatchIn,
    PresenceActivityIn,
    SetupAnswerIn,
    SetupRandomApplyIn,
    SetupRandomIn,
    StoryCardCreateIn,
    StoryCardPatchIn,
    TimeAdvanceIn,
    TurnCreateIn,
    TurnEditIn,
    WorldInfoCreateIn,
    WorldInfoPatchIn,
)
from app.schemas.llm import (
    CHARACTER_ATTRIBUTE_SCHEMA,
    CONTEXT_RESPONSE_SCHEMA,
    ELEMENT_GENERATOR_SCHEMA,
    MANIFESTATION_SKILL_NAME_SCHEMA,
    NPC_EXTRACTOR_SCHEMA,
    SETUP_RANDOM_SCHEMA,
    STORY_REWRITE_SCHEMA,
)
from app.serializers import campaign_view as campaign_view_serializer
from app.services import boards_service
from app.services import campaign_service
from app.services import claim_service
from app.services import context_service
from app.services import live_state_service
from app.services import presence_service
from app.services import setup_service
from app.services import sheets_service
from app.services import state_engine
from app.services import turn_engine
from app.services import turn_service

CAMPAIGN_REPOSITORY = CampaignRepository(data_dir=DATA_DIR, campaigns_dir=CAMPAIGNS_DIR)

LOGGER = logging.getLogger("isekai.turns")

def ensure_data_dirs() -> None:
    ensure_storage_dirs(data_dir=DATA_DIR, campaigns_dir=CAMPAIGNS_DIR)

# Configure extracted turn engine early so cross-domain flows (e.g. setup finalize)
# can safely call turn helpers before the turns router is hit.
turn_engine.configure(globals())

# Extracted turn engine pipeline cluster
TurnFlowError = turn_engine.TurnFlowError
user_message_for_error_code = turn_engine.user_message_for_error_code
new_turn_trace_context = turn_engine.new_turn_trace_context
emit_turn_phase_event = turn_engine.emit_turn_phase_event
turn_flow_error = turn_engine.turn_flow_error
looks_like_ollama_transport_error = turn_engine.looks_like_ollama_transport_error
classify_turn_exception = turn_engine.classify_turn_exception
text_tokens = turn_engine.text_tokens
looks_non_german_text = turn_engine.looks_non_german_text
non_german_request_fields = turn_engine.non_german_request_fields
is_first_person_action = turn_engine.is_first_person_action
first_sentences = turn_engine.first_sentences
text_similarity = turn_engine.text_similarity
novelty_ratio = turn_engine.novelty_ratio
salient_action_tokens = turn_engine.salient_action_tokens
repetition_issue_messages = turn_engine.repetition_issue_messages
anti_repetition_examples = turn_engine.anti_repetition_examples
response_quality_issues = turn_engine.response_quality_issues
build_repetition_retry_instruction = turn_engine.build_repetition_retry_instruction
inactive_character_refs = turn_engine.inactive_character_refs
validate_patch = turn_engine.validate_patch
sanitize_patch = turn_engine.sanitize_patch
apply_patch = turn_engine.apply_patch
enforce_non_milestone_patch_limits = turn_engine.enforce_non_milestone_patch_limits
enforce_progression_set_mode_limits = turn_engine.enforce_progression_set_mode_limits
rewrite_story_length_guard = turn_engine.rewrite_story_length_guard
create_turn_record = turn_engine.create_turn_record
find_turn = turn_engine.find_turn
reset_turn_branch = turn_engine.reset_turn_branch

# Extracted normalization/world/codex/progression/state-mutation engine cluster
state_engine.configure_dependencies(
    state_engine.StateEngineDependencies(
        campaign_repository=CAMPAIGN_REPOSITORY,
        ollama_adapter=LLM_ADAPTER,
        live_state_service=live_state_service,
        logger=LOGGER,
    )
)
for _name in state_engine.EXPORTED_SYMBOLS:
    globals()[_name] = getattr(state_engine, _name)
del _name

app = FastAPI(title="Aelunor")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/v1/assets", StaticFiles(directory=UI_V1_ASSETS_DIR, check_dir=False), name="v1-assets")

@app.get("/")
def index() -> RedirectResponse:
    return RedirectResponse(url="/v1", status_code=307)

def _v1_index_html() -> str:
    index_path = os.path.join(UI_V1_DIST_DIR, "index.html")
    if os.path.isfile(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>Aelunor UI v1</title></head>"
        "<body><h1>Aelunor UI v1 is not built yet.</h1><p>Run the UI build inside the ui directory.</p></body></html>"
    )

@app.get("/v1", response_class=HTMLResponse)
@app.get("/v1/", response_class=HTMLResponse)
def index_v1() -> str:
    return _v1_index_html()

@app.get("/v1/{path:path}", response_class=HTMLResponse)
def index_v1_routes(path: str) -> str:
    return _v1_index_html()

@app.get("/api/state")
def get_state() -> Dict[str, Any]:
    raise HTTPException(status_code=410, detail="Die Legacy-State-API wurde entfernt. Verwende /api/campaigns/{campaign_id}.")

@app.get("/api/llm/status")
def get_llm_status() -> Dict[str, Any]:
    payload = dict(LLM_ADAPTER.status_payload())
    payload["llm_provider"] = LLM_PROVIDER
    return payload

def state_engine_runtime() -> Dict[str, Any]:
    runtime = dict(globals())
    runtime.update(state_engine.runtime_symbols())
    return runtime

def setup_service_dependencies() -> setup_service.SetupServiceDependencies:
    return build_setup_service_dependencies(state_engine_runtime(), setup_service=setup_service, live_state_service=live_state_service)

def claim_service_dependencies() -> claim_service.ClaimServiceDependencies:
    return build_claim_service_dependencies(state_engine_runtime(), claim_service=claim_service)

def turn_service_dependencies() -> turn_service.TurnServiceDependencies:
    turn_engine.configure(state_engine_runtime())
    return build_turn_service_dependencies(state_engine_runtime(), turn_service=turn_service, live_state_service=live_state_service)

def context_service_dependencies() -> context_service.ContextServiceDependencies:
    return build_context_service_dependencies(state_engine_runtime(), context_service=context_service)

def campaign_service_dependencies() -> campaign_service.CampaignServiceDependencies:
    return build_campaign_service_dependencies(state_engine_runtime(), campaign_service=campaign_service, live_state_service=live_state_service)

def presence_service_dependencies() -> presence_service.PresenceServiceDependencies:
    return build_presence_service_dependencies(state_engine_runtime(), presence_service=presence_service, live_state_service=live_state_service)

def sheets_service_dependencies() -> sheets_service.SheetsServiceDependencies:
    return build_sheets_service_dependencies(state_engine_runtime(), sheets_service=sheets_service)

def boards_service_dependencies() -> boards_service.BoardsServiceDependencies:
    return build_boards_service_dependencies(state_engine_runtime(), boards_service=boards_service)

# Reconfigure once after all constants are declared so extracted state-engine
# functions receive the complete symbol set (e.g. SKILL_RANK_ORDER).
state_engine.configure_dependencies(
    state_engine.StateEngineDependencies(
        campaign_repository=CAMPAIGN_REPOSITORY,
        ollama_adapter=LLM_ADAPTER,
        live_state_service=live_state_service,
        logger=LOGGER,
    )
)
turn_engine.configure(state_engine_runtime())

app.include_router(
    campaigns_router_module.build_campaigns_router(
        campaign_create_model=CampaignCreateIn,
        join_campaign_model=JoinCampaignIn,
        campaign_meta_patch_model=CampaignMetaPatchIn,
        time_advance_model=TimeAdvanceIn,
        class_unlock_model=ClassUnlockIn,
        faction_join_model=FactionJoinIn,
        campaign_service_dependencies=campaign_service_dependencies,
        build_campaign_view=build_campaign_view,
        public_turn=public_turn,
    )
)
app.include_router(
    presence_router_module.build_presence_router(
        presence_activity_model=PresenceActivityIn,
        presence_service_dependencies=presence_service_dependencies,
        campaign_event_stream=live_state_service.campaign_event_stream,
    )
)
app.include_router(
    sheets_router_module.build_sheets_router(
        sheets_service_dependencies=sheets_service_dependencies,
    )
)
app.include_router(
    setup_router_module.build_setup_router(
        setup_answer_model=SetupAnswerIn,
        setup_random_model=SetupRandomIn,
        setup_random_apply_model=SetupRandomApplyIn,
        setup_service_dependencies=setup_service_dependencies,
        build_campaign_view=build_campaign_view,
    )
)
app.include_router(
    claim_router_module.build_claim_router(
        claim_service_dependencies=claim_service_dependencies,
        build_campaign_view=build_campaign_view,
    )
)
app.include_router(
    turns_router_module.build_turns_router(
        turn_create_model=TurnCreateIn,
        turn_edit_model=TurnEditIn,
        turn_service_dependencies=turn_service_dependencies,
        build_campaign_view=build_campaign_view,
    )
)
app.include_router(
    context_router_module.build_context_router(
        context_query_model=ContextQueryIn,
        context_service_dependencies=context_service_dependencies,
    )
)
app.include_router(
    boards_router_module.build_boards_router(
        plot_essentials_patch_model=PlotEssentialsPatchIn,
        authors_note_patch_model=AuthorsNotePatchIn,
        player_diary_patch_model=PlayerDiaryPatchIn,
        story_card_create_model=StoryCardCreateIn,
        story_card_patch_model=StoryCardPatchIn,
        world_info_create_model=WorldInfoCreateIn,
        world_info_patch_model=WorldInfoPatchIn,
        boards_service_dependencies=boards_service_dependencies,
        build_campaign_view=build_campaign_view,
    )
)
