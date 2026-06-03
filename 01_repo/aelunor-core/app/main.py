import hashlib
import json
import logging
import math
import os
import random
import secrets
import time
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.adapters.llm import OllamaAdapter, OllamaSettings
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
    build_canon_extractor_schema,
    build_progression_extractor_schema,
    extend_turn_patch_schema,
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
from app.runtime_config import bundled_path, resolve_runtime_config

RUNTIME_CONFIG = resolve_runtime_config()
BASE_DIR = str(bundled_path("app"))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UI_V1_DIST_DIR = str(bundled_path("ui", "dist"))
UI_V1_ASSETS_DIR = os.path.join(UI_V1_DIST_DIR, "assets")
DATA_DIR = str(RUNTIME_CONFIG.data_dir)
LEGACY_STATE_PATH = os.path.join(DATA_DIR, "state.json")
CAMPAIGNS_DIR = os.path.join(DATA_DIR, "campaigns")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://192.168.65.254:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
_OLLAMA_SEED_RAW = str(os.getenv("OLLAMA_SEED", "")).strip()
OLLAMA_SEED: Optional[int] = int(_OLLAMA_SEED_RAW) if _OLLAMA_SEED_RAW else None
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.6"))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
OLLAMA_REPEAT_PENALTY = float(os.getenv("OLLAMA_REPEAT_PENALTY", "1.18"))
OLLAMA_REPEAT_LAST_N = int(os.getenv("OLLAMA_REPEAT_LAST_N", "192"))
OLLAMA_TIMEOUT_SEC = int(os.getenv("OLLAMA_TIMEOUT_SEC", "240"))
OLLAMA_ADAPTER = OllamaAdapter(
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
CAMPAIGN_REPOSITORY = CampaignRepository(data_dir=DATA_DIR, campaigns_dir=CAMPAIGNS_DIR)

LOGGER = logging.getLogger("isekai.turns")

LEGACY_CHARACTERS = ("Matchek", "Abo", "Beni")
ACTION_TYPES = ("do", "say", "story", "canon")
PHASES = ("lobby", "world_setup", "character_setup_open", "ready_to_start", "active")
SLOT_PREFIX = "slot_"
MAX_PLAYERS = 6
MAX_TURN_MODEL_ATTEMPTS = 3
CONTINUE_STORY_MARKER = "__CONTINUE_STORY__"
CAMPAIGN_LENGTHS = ("short", "medium", "open")
TARGET_TURNS_DEFAULTS = {"short": 120, "medium": 720, "open": None}
PACING_PROFILE_DEFAULTS = {
    "short": {
        "beats_per_turn": 3,
        "detail_level": "low",
        "plot_density": "high",
        "sideplot_limit": 1,
        "milestone_every_n_turns": 8,
        "min_story_chars": 900,
        "max_story_chars": 2200,
    },
    "medium": {
        "beats_per_turn": 2,
        "detail_level": "medium",
        "plot_density": "medium",
        "sideplot_limit": 3,
        "milestone_every_n_turns": 18,
        "min_story_chars": 800,
        "max_story_chars": 2200,
    },
    "open": {
        "beats_per_turn": 1,
        "detail_level": "high",
        "plot_density": "medium",
        "sideplot_limit": None,
        "milestone_every_n_turns": 35,
        "min_story_chars": 700,
        "max_story_chars": 2200,
    },
}
TIMING_DEFAULTS = {
    "ai_latency_ema_sec": 40.0,
    "player_latency_ema_sec": 25.0,
    "cycle_ema_sec": 65.0,
    "turns_target_est": None,
    "turns_left_est": None,
    "last_response_ready_ts": None,
}
TIMING_EMA_ALPHA = 0.1
AI_LATENCY_CLAMP = (10.0, 90.0)
PLAYER_LATENCY_CLAMP = (5.0, 120.0)
MIN_STORY_REWRITE_ATTEMPTS = 2
MAX_STORY_COMPRESS_ATTEMPTS = 1
ATTRIBUTE_INFLUENCE_DISTRIBUTION = (
    ("none", 0.15),
    ("low", 0.25),
    ("medium", 0.35),
    ("high", 0.25),
)
ATTRIBUTE_INFLUENCE_STRENGTH = {
    "none": 0.0,
    "low": 0.12,
    "medium": 0.22,
    "high": 0.35,
}
COMBAT_NARRATIVE_HINTS = (
    "kampf",
    "angriff",
    "schlag",
    "trifft",
    "wunde",
    "verwundet",
    "blutet",
    "klinge",
    "monster",
    "gegner",
    "duell",
    "zauber",
)
COMBAT_END_HINTS = (
    "kampf endet",
    "kampf vorbei",
    "gefahr gebannt",
    "gegner besiegt",
    "gegner fällt",
    "ruhe kehrt ein",
)
ENABLE_HEURISTIC_NORMALIZE_BACKFILL = (
    str(os.getenv("ENABLE_HEURISTIC_NORMALIZE_BACKFILL", "false")).strip().lower() in {"1", "true", "yes", "on"}
)
ENABLE_LEGACY_SHADOW_WRITEBACK = (
    str(os.getenv("ENABLE_LEGACY_SHADOW_WRITEBACK", "false")).strip().lower() in {"1", "true", "yes", "on"}
)
EXTRACTION_QUARANTINE_DEFAULT_MAX = 300
EXTRACTION_REASON_GENERIC_LOCATION = "GENERIC_LOCATION"
EXTRACTION_REASON_MISSING_ACQUIRE = "MISSING_ACQUIRE_SIGNAL"
EXTRACTION_REASON_ENV_OBJECT = "ENV_OBJECT_ONLY"
EXTRACTION_REASON_VERB_STYLE_SKILL = "VERB_STYLE_SKILL"
EXTRACTION_REASON_AMBIGUOUS_CLASS = "AMBIGUOUS_CLASS"
EXTRACTION_REASON_DUPLICATE = "DUPLICATE_LIKELY"
EXTRACTION_REASON_LOW_CONFIDENCE = "LOW_CONFIDENCE"
EXTRACTION_REASON_CONFLICT_WITH_LLM = "CONFLICT_WITH_LLM"
CODEX_KNOWLEDGE_LEVEL_MIN = 0
CODEX_KNOWLEDGE_LEVEL_MAX = 4
CODEX_KIND_RACE = "race"
CODEX_KIND_BEAST = "beast"
RACE_CODEX_BLOCK_ORDER = [
    "identity",
    "appearance",
    "culture",
    "homeland",
    "class_affinities",
    "skill_affinities",
    "strengths",
    "weaknesses",
    "relations",
    "notable_individuals",
]
BEAST_CODEX_BLOCK_ORDER = [
    "identity",
    "appearance",
    "habitat",
    "behavior",
    "combat_style",
    "known_abilities",
    "strengths",
    "weaknesses",
    "loot",
    "lore",
]
RACE_BLOCKS_BY_LEVEL = {
    0: [],
    1: ["identity", "appearance"],
    2: ["culture", "homeland", "relations"],
    3: ["class_affinities", "skill_affinities", "strengths", "weaknesses"],
    4: ["notable_individuals"],
}
BEAST_BLOCKS_BY_LEVEL = {
    0: [],
    1: ["identity", "appearance", "habitat"],
    2: ["behavior", "combat_style"],
    3: ["known_abilities", "strengths", "weaknesses", "loot"],
    4: ["lore"],
}
CODEX_DEFAULT_META = {
    "version": 1,
    "shared_knowledge": True,
}
CODEX_RACE_TRIGGER_LORE = {
    "archiv",
    "chronik",
    "legende",
    "lore",
    "forschung",
    "forscht",
    "bibliothek",
    "tafel",
    "buch",
    "aufzeichnung",
    "codex",
    "lehrtext",
}
CODEX_RACE_TRIGGER_CONTACT = {
    "begegnet",
    "trifft",
    "spricht",
    "verhandelt",
    "diplomatie",
    "hilfe",
    "misstrauen",
    "bittet",
    "verfolgt",
    "rettet",
}
CODEX_BEAST_TRIGGER_COMBAT = {
    "kampf",
    "angriff",
    "klaue",
    "biss",
    "zahn",
    "gift",
    "schlag",
    "trifft",
    "duell",
    "monster",
    "bestie",
}
CODEX_BEAST_TRIGGER_DEFEAT = {
    "besiegt",
    "erlegt",
    "getoetet",
    "getötet",
    "vernichtet",
    "erschlagen",
    "faellt",
    "fällt",
}
CODEX_BEAST_TRIGGER_ABILITY = {
    "faehigkeit",
    "fähigkeit",
    "atem",
    "zauber",
    "schrei",
    "aura",
    "sprung",
    "regen",
    "giftwolke",
}
ELEMENT_TOTAL_COUNT = 12
ELEMENT_CORE_NAMES = ("Feuer", "Wasser", "Erde", "Luft", "Licht", "Schatten")
ELEMENT_RELATIONS = {"dominant", "strong", "neutral", "weak", "countered"}
ELEMENT_RELATION_SCORE = {
    "dominant": 1.35,
    "strong": 1.18,
    "neutral": 1.0,
    "weak": 0.88,
    "countered": 0.72,
}
ELEMENT_CLASS_PATH_RANKS = ("F", "C", "B", "A", "S")
ELEMENT_CLASS_PATH_MIN = 1
ELEMENT_CLASS_PATH_MAX = 3
ELEMENT_GENERATED_NAMES_FALLBACK = [
    "Resonanz",
    "Nebel",
    "Asche",
    "Klangkern",
    "Runenfluss",
    "Sternenfrost",
    "Dornengeist",
    "Leere",
    "Traum",
    "Blut",
    "Eidstahl",
    "Donnerglas",
]
ELEMENT_SIMILARITY_BLACKLIST = {
    "feuer": {"flamme", "brand", "glut", "inferno", "hitz"},
    "wasser": {"flut", "strom", "gezeiten", "regen", "welle"},
    "erde": {"stein", "fels", "boden", "lehm"},
    "luft": {"wind", "sturm", "hauch", "aetherwind"},
    "licht": {"sonne", "strahl", "heilig", "glanz"},
    "schatten": {"nacht", "dunkel", "umbra", "finsternis"},
}

ERROR_CODE_NARRATOR_RESPONSE = "NARRATOR_RESPONSE_ERROR"
ERROR_CODE_JSON_REPAIR = "JSON_REPAIR_ERROR"
ERROR_CODE_SCHEMA_VALIDATION = "SCHEMA_VALIDATION_ERROR"
ERROR_CODE_PATCH_SANITIZE = "PATCH_SANITIZE_ERROR"
ERROR_CODE_PATCH_APPLY = "PATCH_APPLY_ERROR"
ERROR_CODE_EXTRACTOR = "EXTRACTOR_ERROR"
ERROR_CODE_NORMALIZE = "NORMALIZE_ERROR"
ERROR_CODE_PERSISTENCE = "PERSISTENCE_ERROR"
ERROR_CODE_SSE_BROADCAST = "SSE_BROADCAST_ERROR"
ERROR_CODE_TURN_INTERNAL = "TURN_INTERNAL_ERROR"

TURN_ERROR_USER_MESSAGES = {
    ERROR_CODE_NARRATOR_RESPONSE: "Die KI-Antwort konnte gerade nicht verarbeitet werden.",
    ERROR_CODE_JSON_REPAIR: "Die KI-Antwort war unvollständig oder ungültig formatiert.",
    ERROR_CODE_SCHEMA_VALIDATION: "Die KI-Antwort passte nicht zum erwarteten Datenformat.",
    ERROR_CODE_PATCH_SANITIZE: "Die KI-Änderungen konnten nicht sicher bereinigt werden.",
    ERROR_CODE_PATCH_APPLY: "Die KI-Änderungen konnten nicht auf den Spielzustand angewendet werden.",
    ERROR_CODE_EXTRACTOR: "Die Kanon-Extraktion konnte nicht abgeschlossen werden.",
    ERROR_CODE_NORMALIZE: "Der Kampagnenzustand konnte nicht stabilisiert werden.",
    ERROR_CODE_PERSISTENCE: "Die Kampagne konnte nicht gespeichert werden.",
    ERROR_CODE_SSE_BROADCAST: "Das Live-Update konnte nicht verteilt werden.",
    ERROR_CODE_TURN_INTERNAL: "Beim Verarbeiten des Zugs ist ein interner Fehler aufgetreten.",
}

with open(os.path.join(BASE_DIR, "prompts.json"), "r", encoding="utf-8") as f:
    PROMPTS = json.load(f)
with open(os.path.join(BASE_DIR, "setup_catalog.json"), "r", encoding="utf-8") as f:
    SETUP_CATALOG = json.load(f)

SYSTEM_PROMPT = PROMPTS["system_prompt"]
RESPONSE_SCHEMA = extend_turn_patch_schema(PROMPTS["response_schema"])
INITIAL_STATE = PROMPTS["initial_state"]
CATALOG_VERSION = SETUP_CATALOG["version"]
WORLD_FORM_CATALOG = SETUP_CATALOG["world_form_catalog"]
CHARACTER_FORM_CATALOG = SETUP_CATALOG["character_form_catalog"]
WORLD_QUESTION_MAP = {entry["id"]: entry for entry in WORLD_FORM_CATALOG}
CHARACTER_QUESTION_MAP = {entry["id"]: entry for entry in CHARACTER_FORM_CATALOG}

WORLD_SETUP_CHAPTERS = {
    "foundations": {
        "label": "Grundton der Welt",
        "questions": {"theme", "tone", "difficulty", "player_count", "campaign_length"},
    },
    "laws_power": {
        "label": "Mächte und Gesetze",
        "questions": {"resource_name", "ruleset", "attribute_range", "world_laws", "outcome_model"},
    },
    "danger_conflict": {
        "label": "Gefahren und Konflikte",
        "questions": {"death_possible", "monsters_density", "resource_scarcity", "healing_frequency", "central_conflict", "factions", "taboos"},
    },
    "structure": {
        "label": "Weltstruktur",
        "questions": {"world_structure"},
    },
}

CHAR_SETUP_CHAPTERS = {
    "identity": {
        "label": "Identität",
        "questions": {"char_name", "char_gender", "char_age"},
    },
    "origin": {
        "label": "Herkunft",
        "questions": {"earth_life", "personality_tags"},
    },
    "class_affinity": {
        "label": "Begabung und Klasse",
        "questions": {"strength", "weakness", "class_start_mode", "class_seed", "class_custom_name", "class_custom_description", "class_custom_tags"},
    },
    "drive": {
        "label": "Motivation und Einstieg",
        "questions": {"current_focus", "first_goal", "isekai_price", "earth_items", "signature_item"},
    },
}

CANON_EXTRACTOR_SCHEMA = build_canon_extractor_schema(RESPONSE_SCHEMA)
CANON_GATE_DOMAINS_SUPPORTED = ("progression", "items", "location", "faction", "injury", "spellschool")
CANON_GATE_ACTIVE_DOMAINS = {"progression"}

PROGRESSION_EXTRACTOR_SCHEMA = build_progression_extractor_schema(RESPONSE_SCHEMA)

NPC_STATUS_ALLOWED = {"active", "unknown", "gone"}

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def deep_copy(value: Any) -> Any:
    return json.loads(json.dumps(value))

def ensure_data_dirs() -> None:
    CampaignRepository(data_dir=DATA_DIR, campaigns_dir=CAMPAIGNS_DIR).ensure_storage()

def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"

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
state_engine.configure(globals())
for _name in state_engine.EXPORTED_SYMBOLS:
    globals()[_name] = getattr(state_engine, _name)
del _name

# Canon-first runtime fields. These are the primary mutable gameplay truth.
CANON_CHARACTER_FIELDS = {
    "scene_id",
    "class_current",
    "skills",
    "inventory",
    "equipment",
    "injuries",
    "scars",
    "hp_current",
    "hp_max",
    "sta_current",
    "sta_max",
    "res_current",
    "res_max",
    "carry_current",
    "carry_max",
    "level",
    "xp_total",
    "xp_current",
    "xp_to_next",
    "recent_progression_events",
    "class_path_seeds",
    "progression",
}
# Compatibility shadow fields: readable for old saves, optional writeback only.
LEGACY_SHADOW_FIELDS = {
    "resources",
    "hp",
    "stamina",
    "equip",
    "abilities",
    "potential",
}
# Migration-only inputs from old state shapes.
MIGRATION_ONLY_FIELDS = {
    "bio.party_role",
    "class_state",
    "equip",
    "abilities",
    "resources",
    "hp",
    "stamina",
    "potential",
}
INJURY_SEVERITIES = {"leicht", "mittel", "schwer"}
INJURY_HEALING_STAGES = {"frisch", "heilend", "fast_heil", "geheilt"}

LEGACY_SELECT_ALIASES: Dict[str, Dict[str, str]] = {
    "theme": {
        "grimdark": "Grimdark",
        "dark fantasy": "Dark Fantasy",
        "high fantasy": "High Fantasy",
    },
    "tone": {
        "ernst": "Ernst",
        "hart": "Hart",
        "hoffnungsvoll": "Hoffnungsvoll",
        "zerrissen": "Zerrissen",
    },
    "monsters_density": {
        "regelmaessig": "Regelmäßig",
        "regelmassig": "Regelmäßig",
    },
    "char_gender": {
        "maennlich": "Männlich",
        "male": "Männlich",
        "weiblich": "Weiblich",
        "female": "Weiblich",
        "nichtbinaer": "Nichtbinär",
        "nicht-binaer": "Nichtbinär",
        "nonbinary": "Nichtbinär",
    },
    "class_start_mode": {
        "ki jetzt": "KI jetzt",
        "selbst": "Ich definiere selbst",
        "story": "Erst in der Story",
    },
}

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
    return OLLAMA_ADAPTER.status_payload()

def setup_service_dependencies() -> setup_service.SetupServiceDependencies:
    return setup_service.SetupServiceDependencies(
        load_campaign=load_campaign,
        authenticate_player=authenticate_player,
        require_host=require_host,
        is_host=is_host,
        current_question_id=current_question_id,
        clear_live_activity=live_state_service.clear_live_activity,
        start_blocking_action=live_state_service.start_blocking_action,
        clear_blocking_action=live_state_service.clear_blocking_action,
        ensure_question_ai_copy=ensure_question_ai_copy,
        save_campaign=save_campaign,
        build_world_question_state=build_world_question_state,
        build_character_question_state=build_character_question_state,
        progress_payload=progress_payload,
        validate_answer_payload=validate_answer_payload,
        store_setup_answer=store_setup_answer,
        build_random_setup_preview=build_random_setup_preview,
        apply_random_setup_preview=apply_random_setup_preview,
        finalize_world_setup=finalize_world_setup,
        finalize_character_setup=finalize_character_setup,
        deep_copy=deep_copy,
        build_world_summary=build_world_summary,
        build_character_summary=build_character_summary,
        normalize_world_settings=normalize_world_settings,
        apply_world_summary_to_boards=apply_world_summary_to_boards,
        apply_character_summary_to_state=apply_character_summary_to_state,
        campaign_slots=campaign_slots,
        target_turns_defaults=TARGET_TURNS_DEFAULTS,
        pacing_profile_defaults=PACING_PROFILE_DEFAULTS,
        world_question_map=WORLD_QUESTION_MAP,
        character_question_map=CHARACTER_QUESTION_MAP,
    )

def claim_service_dependencies() -> claim_service.ClaimServiceDependencies:
    return claim_service.ClaimServiceDependencies(
        load_campaign=load_campaign,
        authenticate_player=authenticate_player,
        player_claim=player_claim,
        current_question_id=current_question_id,
        ensure_question_ai_copy=ensure_question_ai_copy,
        save_campaign=save_campaign,
        is_host=is_host,
    )

def turn_service_dependencies() -> turn_service.TurnServiceDependencies:
    turn_engine.configure(globals())
    return turn_service.TurnServiceDependencies(
        load_campaign=load_campaign,
        authenticate_player=authenticate_player,
        active_turns=active_turns,
        intro_state=intro_state,
        require_claim=require_claim,
        new_turn_trace_context=new_turn_trace_context,
        emit_turn_phase_event=emit_turn_phase_event,
        clear_live_activity=live_state_service.clear_live_activity,
        start_blocking_action=live_state_service.start_blocking_action,
        clear_blocking_action=live_state_service.clear_blocking_action,
        create_turn_record=create_turn_record,
        save_campaign=save_campaign,
        classify_turn_exception=classify_turn_exception,
        turn_flow_error_cls=TurnFlowError,
        remember_recent_story=remember_recent_story,
        rebuild_memory_summary=rebuild_memory_summary,
        find_turn=find_turn,
        reset_turn_branch=reset_turn_branch,
        utc_now=utc_now,
    )

def context_service_dependencies() -> context_service.ContextServiceDependencies:
    return context_service.ContextServiceDependencies(
        load_campaign=load_campaign,
        authenticate_player=authenticate_player,
        player_claim=player_claim,
        active_party=active_party,
        campaign_slots=campaign_slots,
        context_state_signature=context_state_signature,
        parse_context_intent=parse_context_intent,
        build_context_knowledge_index=build_context_knowledge_index,
        resolve_context_target=resolve_context_target,
        deterministic_context_result_from_entry=deterministic_context_result_from_entry,
        build_context_result_payload=build_context_result_payload,
        extract_story_target_evidence=extract_story_target_evidence,
        build_reduced_context_snippets=build_reduced_context_snippets,
        build_context_result_via_llm=build_context_result_via_llm,
        context_result_to_answer_text=context_result_to_answer_text,
    )

def campaign_service_dependencies() -> campaign_service.CampaignServiceDependencies:
    return campaign_service.CampaignServiceDependencies(
        ensure_campaign_storage=ensure_campaign_storage,
        create_campaign_record=create_campaign_record,
        find_campaign_by_join_code=find_campaign_by_join_code,
        new_player=new_player,
        utc_now=utc_now,
        hash_secret=hash_secret,
        save_campaign=save_campaign,
        load_campaign=load_campaign,
        authenticate_player=authenticate_player,
        require_host=require_host,
        deep_copy=deep_copy,
        intro_state=intro_state,
        active_turns=active_turns,
        can_start_adventure=can_start_adventure,
        clear_live_activity=live_state_service.clear_live_activity,
        start_blocking_action=live_state_service.start_blocking_action,
        clear_blocking_action=live_state_service.clear_blocking_action,
        try_generate_adventure_intro=try_generate_adventure_intro,
        apply_world_time_advance=apply_world_time_advance,
        rebuild_all_character_derived=rebuild_all_character_derived,
        append_character_change_events=append_character_change_events,
        normalize_class_current=normalize_class_current,
        rebuild_character_derived=rebuild_character_derived,
        normalize_world_time=normalize_world_time,
        campaign_path=campaign_path,
        clear_live_campaign_state=live_state_service.clear_campaign_state,
    )

def presence_service_dependencies() -> presence_service.PresenceServiceDependencies:
    return presence_service.PresenceServiceDependencies(
        load_campaign=load_campaign,
        authenticate_player=authenticate_player,
        set_live_activity=live_state_service.set_live_activity,
        clear_live_activity=live_state_service.clear_live_activity,
        live_snapshot=live_state_service.live_snapshot,
    )

def sheets_service_dependencies() -> sheets_service.SheetsServiceDependencies:
    return sheets_service.SheetsServiceDependencies(
        load_campaign=load_campaign,
        authenticate_player=authenticate_player,
        build_party_overview=build_party_overview,
        build_character_sheet_view=build_character_sheet_view,
        build_npc_sheet_view=build_npc_sheet_view,
    )

def boards_service_dependencies() -> boards_service.BoardsServiceDependencies:
    return boards_service.BoardsServiceDependencies(
        load_campaign=load_campaign,
        authenticate_player=authenticate_player,
        require_host=require_host,
        save_campaign=save_campaign,
        utc_now=utc_now,
        deep_copy=deep_copy,
        log_board_revision=log_board_revision,
        default_player_diary_entry=default_player_diary_entry,
        make_id=make_id,
    )

# Reconfigure once after all constants are declared so extracted state-engine
# functions receive the complete symbol set (e.g. SKILL_RANK_ORDER).
state_engine.configure(globals())
turn_engine.configure(globals())

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
