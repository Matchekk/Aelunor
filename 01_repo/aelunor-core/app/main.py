import hashlib
import json
import logging
import math
import os
import random
import re
import secrets
import time
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.helpers import setup_helpers
from app.routers import boards as boards_router_module
from app.routers import campaigns as campaigns_router_module
from app.routers import claim as claim_router_module
from app.routers import context as context_router_module
from app.routers import presence as presence_router_module
from app.routers import setup as setup_router_module
from app.routers import sheets as sheets_router_module
from app.routers import turns as turns_router_module
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

BASE_DIR = os.path.dirname(__file__)
UI_V1_DIST_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "ui", "dist"))
UI_V1_ASSETS_DIR = os.path.join(UI_V1_DIST_DIR, "assets")
DATA_DIR = os.getenv("DATA_DIR", "/data")
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
    "Sturmkern",
    "Runenfluss",
    "Sternenfrost",
    "Dornengeist",
    "Leere",
    "Traum",
    "Blut",
    "Gezeitenstahl",
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
RESPONSE_SCHEMA = PROMPTS["response_schema"]
INITIAL_STATE = PROMPTS["initial_state"]
CATALOG_VERSION = SETUP_CATALOG["version"]
WORLD_FORM_CATALOG = SETUP_CATALOG["world_form_catalog"]
CHARACTER_FORM_CATALOG = SETUP_CATALOG["character_form_catalog"]
WORLD_QUESTION_MAP = {entry["id"]: entry for entry in WORLD_FORM_CATALOG}
CHARACTER_QUESTION_MAP = {entry["id"]: entry for entry in CHARACTER_FORM_CATALOG}

TURN_MODE_GUIDE = {
    "do": "TUN: Die Figur versucht konkret etwas. Das Ergebnis und die Konsequenzen entscheidet der Erzähler.",
    "say": "SAGEN: Die Figur spricht. Reaktionen und Folgen entscheidet der Erzähler.",
    "story": "STORY: Erzählerischer Vorschlag oder Szenenrichtung. Der Erzähler darf ihn passend einbauen oder umlenken.",
    "canon": "CANON: Harte Wahrheit. Dieser Text wird verbindlich in den Zustand übernommen.",
}

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

def extend_turn_patch_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    extended = json.loads(json.dumps(schema))
    char_patch = (((extended.get("$defs") or {}).get("char_patch")) or {})
    properties = char_patch.setdefault("properties", {})
    properties.setdefault("scene_set", {"type": "string"})
    skill_object_schema = (
        ((properties.get("skills_set") or {}).get("additionalProperties") or {}).get("anyOf") or []
    )
    for candidate in skill_object_schema:
        if not isinstance(candidate, dict):
            continue
        if candidate.get("type") != "object":
            continue
        candidate.setdefault("properties", {})
        candidate["properties"].setdefault("effect_summary", {"type": "string"})
        candidate["properties"].setdefault("power_rating", {"type": "integer"})
        candidate["properties"].setdefault("growth_potential", {"type": "string"})
        candidate["properties"].setdefault("manifestation_source", {"type": ["string", "null"]})
        candidate["properties"].setdefault("category", {"type": ["string", "null"]})
        candidate["properties"].setdefault(
            "class_affinity",
            {"type": ["array", "null"], "items": {"type": "string"}},
        )
        candidate["properties"].setdefault(
            "elements",
            {"type": ["array", "null"], "items": {"type": "string"}},
        )
        candidate["properties"].setdefault("element_primary", {"type": ["string", "null"]})
        candidate["properties"].setdefault(
            "element_synergies",
            {"type": ["array", "null"], "items": {"type": "string"}},
        )
        break
    class_schema = properties.get("class_set")
    if isinstance(class_schema, dict):
        class_schema.setdefault("properties", {})
        class_schema["properties"].setdefault("element_id", {"type": ["string", "null"]})
        class_schema["properties"].setdefault(
            "element_tags",
            {"type": ["array", "null"], "items": {"type": "string"}},
        )
        class_schema["properties"].setdefault("path_id", {"type": ["string", "null"]})
        class_schema["properties"].setdefault("path_rank", {"type": ["string", "null"]})

    progression_event_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "actor": {"type": "string"},
                "target_skill_id": {"type": ["string", "null"]},
                "target_class_id": {"type": ["string", "null"]},
                "target_element_id": {"type": ["string", "null"]},
                "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                "tags": {"type": "array", "items": {"type": "string"}},
                "reason": {"type": "string"},
                "source_turn": {"type": "integer"},
                "metadata": {"type": "object", "additionalProperties": True},
                "skill": {"type": "object", "additionalProperties": True},
            },
            "required": ["type"],
            "additionalProperties": False,
        },
    }
    properties.setdefault("progression_events", progression_event_schema)

    skills_delta = properties.get("skills_delta")
    if isinstance(skills_delta, dict):
        skills_delta["additionalProperties"] = {
            "anyOf": [
                {"type": "integer"},
                {
                    "type": "object",
                    "properties": {
                        "xp": {"type": "integer"},
                        "level": {"type": "integer"},
                        "mastery": {"type": "integer"},
                        "description": {"type": "string"},
                        "elements": {"type": "array", "items": {"type": "string"}},
                        "element_primary": {"type": ["string", "null"]},
                        "element_synergies": {"type": ["array", "null"], "items": {"type": "string"}},
                        "cost": {
                            "type": ["object", "null"],
                            "properties": {
                                "resource": {"type": "string"},
                                "amount": {"type": "integer"},
                            },
                            "required": ["resource", "amount"],
                            "additionalProperties": False,
                        },
                    },
                    "additionalProperties": True,
                },
            ]
        }
    return extended

RESPONSE_SCHEMA = extend_turn_patch_schema(RESPONSE_SCHEMA)
CANON_EXTRACTOR_SCHEMA = {
    "type": "object",
    "properties": {
        "patch": json.loads(json.dumps(RESPONSE_SCHEMA["properties"]["patch"])),
    },
    "required": ["patch"],
    "additionalProperties": False,
    "$defs": json.loads(json.dumps(RESPONSE_SCHEMA.get("$defs", {}))),
}
CANON_EXTRACTOR_JSON_CONTRACT = (
    "Antworte mit genau einem JSON-Objekt ohne Markdown und ohne Erklärtext. "
    "Pflichtfeld auf Root-Ebene: `patch` (Objekt). "
    "`patch` muss mindestens diese Felder enthalten: "
    "`meta`, `characters`, `items_new`, `plotpoints_add`, `plotpoints_update`, "
    "`map_add_nodes`, `map_add_edges`, `events_add`. "
    "Wenn du nichts ändern willst, nutze leere Objekte/Arrays statt Felder wegzulassen."
)
CANON_EXTRACTOR_SYSTEM_PROMPT = (
    "Du bist der Canon Extractor. "
    "Du schreibst keine Story, keinen Flavour, keine Erklärung. "
    "Du liest neuen Text und extrahierst nur kanonische Zustandsänderungen als Patch. "
    "Achte strikt darauf: "
    "Neue oder veränderte Kräfte werden immer unter skills abgebildet, nicht als abilities. "
    "skills koennen Magie, Waffenkunst, Koerperentwicklung, Sinnesgeschaerf oder Technik sein. "
    "Ortwechsel nur dann patchen, wenn der Text klar ausdrückt, dass jemand oder die Gruppe jetzt an einem neuen Ort ist. "
    "Items nur patchen, wenn Besitz/Fund/Erhalt klar ausgesprochen ist. "
    "Map-Knoten nur bei klar benannten Orten hinzufügen, nicht aus vagen Beschreibungen. "
    "equipment_set nur dann setzen, wenn der Text explizit getragen/gezogen/ausgerüstet signalisiert. "
    "Nutze nur echte Slot-IDs in `characters`. "
    "Antworte ausschließlich im JSON-Format gemäß OUTPUT-KONTRAKT."
)
CANON_GATE_DOMAINS_SUPPORTED = ("progression", "items", "location", "faction", "injury", "spellschool")
CANON_GATE_ACTIVE_DOMAINS = {"progression"}
PROGRESSION_CLAIM_TYPES = (
    "skill_claim",
    "skill_level_claim",
    "class_claim",
    "class_level_claim",
    "manifestation_claim",
)
PROGRESSION_CLAIM_CUES = {
    "skill_claim": (
        "lernt",
        "erlernt",
        "schaltet frei",
        "erhaelt die faehigkeit",
        "erhält die fähigkeit",
        "entwickelt",
        "meistert",
        "beherrscht nun",
    ),
    "skill_level_claim": (
        "skill steigt",
        "skill-level",
        "skill level",
        "stufe des skills",
        "meisterschaft",
        "verbessert",
        "verfeinert",
    ),
    "class_claim": (
        "klassenwechsel",
        "klasse gewechselt",
        "wird zum",
        "wird zur",
        "nimmt den klassenpfad",
        "schlaegt den klassenpfad ein",
        "schlägt den klassenpfad ein",
        "erwacht als",
    ),
    "class_level_claim": (
        "klassenlevel",
        "class level",
        "klassenstufe",
        "rang steigt",
        "rangaufstieg",
        "aufstieg zu rang",
    ),
    "manifestation_claim": (
        "manifestiert",
        "erstmanifestation",
        "entfesselt erstmals",
        "bricht hervor",
        "erweckt",
    ),
}
PROGRESSION_EXTRACTOR_CONFIDENCE_ORDER = {"low": 1, "medium": 2, "high": 3}
PROGRESSION_EXTRACTOR_CONFIDENCE_SCORE = {"low": 0.3, "medium": 0.6, "high": 0.85}
PROGRESSION_EXTRACTOR_CONFIDENCE_THRESHOLDS = {"high": 0.75, "medium": 0.45}

_progress_char_patch_properties = (((RESPONSE_SCHEMA.get("$defs") or {}).get("char_patch") or {}).get("properties") or {})
PROGRESSION_EXTRACTOR_SCHEMA = {
    "type": "object",
    "properties": {
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "reason": {"type": "string"},
        "character_patch": {
            "type": "object",
            "properties": {
                "skills_set": json.loads(json.dumps(_progress_char_patch_properties.get("skills_set", {"type": "object", "additionalProperties": True}))),
                "skills_delta": json.loads(json.dumps(_progress_char_patch_properties.get("skills_delta", {"type": "object", "additionalProperties": True}))),
                "progression_events": json.loads(
                    json.dumps(_progress_char_patch_properties.get("progression_events", {"type": "array", "items": {"type": "object", "additionalProperties": True}}))
                ),
                "class_set": json.loads(
                    json.dumps(
                        _progress_char_patch_properties.get(
                            "class_set",
                            {"type": "object", "additionalProperties": True},
                        )
                    )
                ),
                "class_update": json.loads(
                    json.dumps(
                        _progress_char_patch_properties.get(
                            "class_update",
                            {"type": "object", "additionalProperties": True},
                        )
                    )
                ),
                "progression_set": json.loads(
                    json.dumps(
                        _progress_char_patch_properties.get(
                            "progression_set",
                            {"type": "object", "additionalProperties": True},
                        )
                    )
                ),
            },
            "additionalProperties": False,
        },
    },
    "required": ["confidence", "character_patch"],
    "additionalProperties": False,
}
PROGRESSION_EXTRACTOR_JSON_CONTRACT = (
    "Antworte mit genau einem JSON-Objekt ohne Markdown. "
    "Pflichtfelder: `confidence` (`high|medium|low`) und `character_patch` (Objekt). "
    "`character_patch` darf nur strukturierte Progressionsfelder enthalten: "
    "`skills_set`, `skills_delta`, `progression_events`, `class_set`, `class_update`, `progression_set`. "
    "Wenn nichts extrahierbar ist, nutze leere Objekte/Arrays."
)
PROGRESSION_EXTRACTOR_SYSTEM_PROMPT = (
    "Du bist der Progression Canon Extractor. "
    "Du schreibst keine Prosa und keine Erklärtexte. "
    "Du extrahierst nur strukturierte Progressionsänderungen für den aktiven Actor "
    "(Skills, Skill-Level, Klassenfortschritt, Manifestationen). "
    "Wenn die Evidenz schwach ist, gib confidence=low und leere Felder zurück. "
    "Nutze nur valide JSON-Antworten gemäß OUTPUT-KONTRAKT."
)
NPC_EXTRACTOR_SCHEMA = {
    "type": "object",
    "properties": {
        "npc_upserts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "race": {"type": "string"},
                    "age": {"type": "string"},
                    "goal": {"type": "string"},
                    "level": {"type": "integer"},
                    "backstory_short": {"type": "string"},
                    "role_hint": {"type": "string"},
                    "faction": {"type": "string"},
                    "status": {"type": "string"},
                    "scene_hint": {"type": "string"},
                    "history_note": {"type": "string"},
                    "relevance_score": {"type": "integer"},
                    "class_current": {
                        "type": ["object", "null"],
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "rank": {"type": "string"},
                            "level": {"type": "integer"},
                            "level_max": {"type": "integer"},
                            "xp": {"type": "integer"},
                            "xp_next": {"type": "integer"},
                            "affinity_tags": {"type": "array", "items": {"type": "string"}},
                            "description": {"type": "string"},
                            "ascension": {"type": ["object", "null"]},
                        },
                        "additionalProperties": True,
                    },
                    "skills": {
                        "type": ["object", "null"],
                        "additionalProperties": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "name": {"type": "string"},
                                "rank": {"type": "string"},
                                "level": {"type": "integer"},
                                "level_max": {"type": "integer"},
                                "tags": {"type": "array", "items": {"type": "string"}},
                                "description": {"type": "string"},
                                "cost": {"type": ["object", "null"]},
                            },
                            "additionalProperties": True,
                        },
                    },
                },
                "required": ["name"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["npc_upserts"],
    "additionalProperties": False,
}
NPC_EXTRACTOR_JSON_CONTRACT = (
    "Antworte mit genau einem JSON-Objekt ohne Markdown und ohne Erklärtext. "
    "Root-Feld: `npc_upserts` (Array). "
    "Jeder Eintrag in npc_upserts beschreibt eine story-relevante Figur und nutzt nur die erlaubten Felder. "
    "Wenn keine passende Figur enthalten ist, antworte mit `{\"npc_upserts\": []}`."
)
NPC_EXTRACTOR_SYSTEM_PROMPT = (
    "Du bist der NPC-Extractor für ein RPG-Codex-System. "
    "Du extrahierst nur story-relevante NPCs aus dem neuen Text und lieferst ausschließlich JSON. "
    "Regeln: "
    "Nimm keine Spielercharaktere auf. "
    "Nimm keine generischen Einmal-Nennungen wie 'Wache' oder 'Soldat' ohne individuelle Identität auf. "
    "Erfasse nur Figuren mit erkennbarer Plot-Relevanz. "
    "Pflicht beim ersten relevanten Auftreten: Name, Rasse, Alter, Ziel, Level, Kurz-Backstory (best effort). "
    "Aktualisiere bei Wiedererwähnung vorhandene Figuren mit konkreteren Daten. "
    "Wenn klar erkennbar, kannst du optional class_current und skills mitliefern (nur strukturierte Felder, keine Prosa). "
    "Erfinde keine Prosa, keine Requests, kein Patch."
)

NPC_STATUS_ALLOWED = {"active", "unknown", "gone"}
NPC_GENERIC_NAME_TOKENS = {
    "wache",
    "soldat",
    "kind",
    "frau",
    "mann",
    "haendler",
    "händler",
    "ritter",
    "magier",
    "priester",
    "scharlatan",
    "bandit",
    "siedler",
    "reisender",
    "taenzer",
    "tänzer",
    "vagabund",
    "buerger",
    "bürger",
    "fremder",
    "fremde",
    "gegner",
    "monster",
    "kreatur",
}
STORY_REWRITE_SCHEMA = {
    "type": "object",
    "properties": {
        "story": {"type": "string"},
    },
    "required": ["story"],
    "additionalProperties": False,
}

ACTION_STOPWORDS = {
    "ich",
    "und",
    "oder",
    "aber",
    "doch",
    "dann",
    "mit",
    "dem",
    "den",
    "der",
    "die",
    "das",
    "ein",
    "eine",
    "einer",
    "einem",
    "einen",
    "paar",
    "mehr",
    "weiter",
    "aktuelle",
    "szene",
    "organisch",
    "ohne",
    "harten",
    "sprung",
    "fort",
    "bleib",
    "direkten",
    "konsequenzen",
    "letzten",
    "turns",
    "rede",
    "sage",
    "sag",
    "mache",
    "mach",
}

ENGLISH_LANGUAGE_MARKERS = {
    "what",
    "who",
    "why",
    "how",
    "next",
    "do",
    "the",
    "and",
    "with",
    "without",
    "into",
    "through",
    "toward",
    "from",
    "before",
    "after",
    "while",
    "where",
    "there",
    "their",
    "them",
    "they",
    "you",
    "your",
    "was",
    "were",
    "is",
    "are",
    "be",
    "been",
    "being",
    "this",
    "that",
    "these",
    "those",
    "road",
    "ruins",
    "kingdom",
    "border",
    "guard",
    "watchtower",
    "scene",
    "story",
}

ABILITY_UNLOCK_TRIGGER_PATTERNS = [
    re.compile(
        r"(?:erlernt|erlent|wiedererlernt|lernt|meistert|beherrscht(?:\s+nun)?|schaltet(?:\s+\w+)?\s+frei|erhält|entwickelt|entfesselt)"
        r"\s+(?:die|den|das|eine|einen)?\s*(?:fähigkeit|technik|zauber|magie|gabe|kunst|ritual|formel|form)?\s*[„\"]([^\"“”]{3,60})[\"”]?",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"(?:erlernt|erlent|wiedererlernt|lernt|meistert|beherrscht(?:\s+nun)?|schaltet(?:\s+\w+)?\s+frei|erhält|entwickelt|entfesselt)"
        r"\s+(?:die|den|das|eine|einen)?\s*(?:fähigkeit|technik|zauber|magie|gabe|kunst|ritual|formel|form)(?:\s+(?:der|des))?\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9\- ]{2,60})",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"(?:erlernt|erlent|wiedererlernt|lernt|meistert|beherrscht(?:\s+nun)?|schaltet(?:\s+\w+)?\s+frei|erhält|entwickelt|entfesselt)\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9\- ]{2,40})",
        flags=re.IGNORECASE,
    ),
]
ABILITY_UNLOCK_GENERIC_NAMES = {
    "faehigkeit",
    "technik",
    "zauber",
    "magie",
    "gabe",
    "kunst",
    "ritual",
    "form",
    "formel",
    "neue faehigkeit",
    "neue technik",
    "neuer zauber",
    "neue magie",
    "diese magie",
    "jene magie",
}
UNIVERSAL_SKILL_LIKE_NAMES = {
    "ausdauer",
    "harter koerper",
    "harter körper",
    "schneller schritt",
    "sechster sinn",
    "6ter sinn",
    "6. sinn",
    "wacher blick",
    "zäher wille",
    "zaeher wille",
    "ruhepuls",
    "scharfer blick",
    "taktisches gefuehl",
    "taktisches gefühl",
}
AUTO_ITEM_ACQUIRE_PATTERNS = [
    re.compile(
        r"(?:hebt|hebe|findet|finde|entdeckt|entdecke|pluendert|plündert|pluendere|plündere|lootet|loote|erbeutet|erbeute|erhält|erhaelt|erhalte|nimmt|nehme|steckt|stecke|packt|packe|sammelt|sammle)\s+"
        r"(?:(?:ich|er|sie|wir|ihr|man)\s+)?(?:den|die|das|einen|eine|ein|einem|einer)?\s*([^,.!?;\n]{3,80}?)(?:\s+auf|\s+ein|\s+an\s+sich|\s+bei\s+sich|\s+und\b|,|\.|$)",
        flags=re.IGNORECASE,
    ),
]
AUTO_ITEM_EQUIP_PATTERNS = [
    re.compile(
        r"(?:zieht|ziehe|zueckt|zückt|zuecke|zücke|führt|fuehrt|fuehre|führe|schwingt|schwinge|hält|haelt|halte|greift|greife|richtet|richte|zielt|ziele)\s+"
        r"(?:(?:ich|er|sie|wir|ihr|man)\s+)?(?:den|die|das|einen|eine|ein|seinen|seine|ihr|ihre)?\s*([^,.!?;\n]{3,80}?)(?:\s+in\s+der\s+hand|\s+gegen|\s+auf|\s+vor\s+(?:mich|ihn|sie|ihm|ihr|sich|uns|euch)|\s+und\b|,|\.|$)",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"(?:trägt|trage|traegt|tragt|legt\s+an|lege\s+an|rüstet|ruestet|rüste|rueste|gürtet|guertet|gürte|guerte|schnallt|schnalle)\s+"
        r"(?:(?:ich|er|sie|wir|ihr|man)\s+)?(?:den|die|das|einen|eine|ein|seinen|seine|ihr|ihre)?\s*([^,.!?;\n]{3,80}?)(?:\s+an|\s+um|\s+bei\s+sich|\s+und\b|,|\.|$)",
        flags=re.IGNORECASE,
    ),
]
AUTO_ITEM_GENERIC_NAMES = {
    "gegenstand",
    "objekt",
    "item",
    "waffe",
    "rüstung",
    "ruestung",
    "ding",
    "ausrüstung",
    "ausruestung",
    "zeug",
    "kram",
}
ITEM_WEAPON_KEYWORDS = {
    "schwert",
    "klinge",
    "dolch",
    "messer",
    "axt",
    "hammer",
    "speer",
    "lanze",
    "stab",
    "bogen",
    "armbrust",
    "peitsche",
    "flegel",
    "waffe",
}
ITEM_OFFHAND_KEYWORDS = {"schild", "buckler", "fokus", "fokuskristall", "orb"}
ITEM_CHEST_KEYWORDS = {"rüstung", "ruestung", "panzer", "harnisch", "mantel", "robe", "weste", "brustplatte"}
ITEM_TRINKET_KEYWORDS = {"amulett", "ring", "talisman", "anhänger", "anhaenger", "kette", "reliquie", "totem"}
ITEM_DETAIL_CLAUSE_MARKERS = (" mit ", " für ", " fuer ", " welches ", " welcher ", " welche ", " das ", " der ", " die ")
EQUIPMENT_SLOT_ALIASES = {
    "armor": "chest",
    "brust": "chest",
    "body": "chest",
    "weapon": "weapon",
    "mainhand": "weapon",
    "offhand": "offhand",
    "shield": "offhand",
    "trinket": "trinket",
    "amulet": "amulet",
    "ring": "ring_1",
    "ring1": "ring_1",
    "ring_1": "ring_1",
    "ring2": "ring_2",
    "ring_2": "ring_2",
    "head": "head",
    "helmet": "head",
    "gloves": "gloves",
    "hands": "gloves",
    "boots": "boots",
    "feet": "boots",
}
EQUIPMENT_CANONICAL_SLOTS = {"weapon", "offhand", "head", "chest", "gloves", "boots", "amulet", "ring_1", "ring_2", "trinket"}
STORY_ACTION_CUES = (
    "greift",
    "attackiert",
    "schlägt",
    "rennt",
    "stürmt",
    "weicht",
    "blockt",
    "zieht",
    "hebt",
    "untersucht",
    "scannt",
    "beobachtet",
    "spricht",
    "flüstert",
    "kanalisiert",
    "wirkt",
    "konzentriert",
    "handelt",
    "versucht",
)
STORY_EXPLORE_CUES = (
    "entdeckt",
    "erkundet",
    "erreicht",
    "betritt",
    "findet",
    "stößt auf",
    "stoesst auf",
    "gelangt",
    "folgt",
)
STORY_LEARN_CUES = (
    "erlernt",
    "erlent",
    "lernt",
    "wiedererlernt",
    "meistert",
    "beherrscht",
    "begreift",
    "erkennt",
    "versteht",
    "entwickelt",
    "entfesselt",
    "manifestiert",
    "entsteht",
    "hervorgeht",
    "formt sich",
)

GERMAN_LANGUAGE_MARKERS = {
    "der",
    "die",
    "das",
    "dem",
    "den",
    "des",
    "ein",
    "eine",
    "einer",
    "einem",
    "einen",
    "und",
    "oder",
    "aber",
    "nicht",
    "noch",
    "mit",
    "ohne",
    "durch",
    "gegen",
    "über",
    "unter",
    "zwischen",
    "während",
    "weil",
    "dass",
    "wenn",
    "hier",
    "dort",
    "wurde",
    "waren",
    "ist",
    "sind",
    "szene",
    "geschichte",
    "wache",
}

MEMORY_SYSTEM_PROMPT = (
    "Du fasst eine laufende deutschsprachige Dark-Fantasy-Isekai-Kampagne zusammen. "
    "Schreibe kompakt, konkret und nur beobachtbare Fakten, offene Konflikte, Orte, "
    "Zustand der Figuren und akut relevante Story-Elemente. Keine Markdown-Listen."
)

SETUP_QUESTION_SYSTEM_PROMPT = (
    "Du formulierst die nächste Setup-Frage für eine deutschsprachige Dark-Fantasy-Isekai-Kampagne. "
    "Schreibe genau 1-2 kurze Sätze, atmosphärisch, klar und ohne Meta-Erklärungen. "
    "Erfinde keine neuen Feldtypen oder Regeln. "
    "Nenne niemals Frage-IDs, Typen, Setup-Stufen, Slots, JSON, Listen von Rohdaten oder das Weltprofil selbst."
)

SETUP_RANDOM_SYSTEM_PROMPT = (
    "Du triffst für ein deutschsprachiges Dark-Fantasy-Isekai-Setup stimmige Zufallsentscheidungen. "
    "Du antwortest nur mit gültigem JSON. Halte Textfelder knapp, konkret und passend zur bisherigen Welt oder Figur. "
    "Wenn Auswahloptionen existieren, nutze vorzugsweise diese statt Freitext. "
    "Bei Charakteren bleibe konsistent mit bereits beantworteten Feldern wie Geschlecht, Klassenrichtung und Ton."
)

SETUP_RANDOM_SCHEMA = {
    "type": "object",
    "properties": {
        "value": {"type": ["string", "boolean", "number", "null"]},
        "selected": {
            "oneOf": [
                {"type": "string"},
                {"type": "array", "items": {"type": "string"}},
                {"type": "null"},
            ]
        },
        "other_text": {"type": "string"},
        "other_values": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["value", "selected", "other_text", "other_values"],
    "additionalProperties": False,
}

CHARACTER_ATTRIBUTE_SYSTEM_PROMPT = (
    "Du verteilst Startattribute fuer eine deutschsprachige Dark-Fantasy-Isekai-Figur. "
    "Du antwortest nur mit gueltigem JSON. "
    "Verteile genau ein Profil ueber die sieben Attribute STR, DEX, CON, INT, WIS, CHA und LUCK. "
    "Die Verteilung soll zur Klassenrichtung, Staerke, Schwaeche, Persoenlichkeit, Fokus und Welt passen. "
    "Level-1-Figuren sollen klar profilierte, aber noch nicht ueberzogene Startwerte erhalten. "
    "Bleibe deutsch in allen freien Texten, aber liefere hier nur die Zahlen."
)

CONTEXT_ASSISTANT_SYSTEM_PROMPT = (
    "Du bist ein Kontext-Assistent für eine laufende deutschsprachige Isekai-Kampagne. "
    "Du beantwortest Fragen zum aktuellen Stand (Story, Figuren, Orte, Fraktionen, offene Konflikte) "
    "nur auf Basis der übergebenen Retrieval-Snippets. "
    "Wichtig: Deine Antwort ist rein erklärend und verändert keinen Zustand. "
    "Keine Prosa-Fortsetzung, kein Patch, keine Würfelmechanik. "
    "Keine Markdown-Formatierung. Keine Meta-Aussagen über Textanalyse oder Prompting. "
    "Antworte immer auf Deutsch, klar und strukturiert."
)
CONTEXT_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["found", "not_in_canon", "ambiguous"]},
        "intent": {"type": "string", "enum": ["define", "who", "where", "summary", "compare", "unknown"]},
        "target": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "entity_type": {"type": "string"},
        "entity_id": {"type": "string"},
        "title": {"type": "string"},
        "explanation": {"type": "string"},
        "facts": {"type": "array", "items": {"type": "string"}},
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                },
                "required": ["type", "id", "label"],
                "additionalProperties": False,
            },
        },
        "suggestions": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "status",
        "intent",
        "target",
        "confidence",
        "entity_type",
        "entity_id",
        "title",
        "explanation",
        "facts",
        "sources",
        "suggestions",
    ],
    "additionalProperties": False,
}
CONTEXT_META_DRIFT_MARKERS = (
    "analyse des textes",
    "bereitgestellten text",
    "anleitung fuer den autor",
    "anleitung für den autor",
    "keine neuen story-elemente",
    "formatierungsvorschläge",
    "formatierungsvorschlaege",
)

CHARACTER_ATTRIBUTE_SCHEMA = {
    "type": "object",
    "properties": {
        "str": {"type": "integer"},
        "dex": {"type": "integer"},
        "con": {"type": "integer"},
        "int": {"type": "integer"},
        "wis": {"type": "integer"},
        "cha": {"type": "integer"},
        "luck": {"type": "integer"},
    },
    "required": ["str", "dex", "con", "int", "wis", "cha", "luck"],
    "additionalProperties": False,
}

TURN_RESPONSE_JSON_CONTRACT = (
    "Antworte mit genau einem JSON-Objekt ohne Markdown und ohne Erklärtext. "
    "Pflichtfelder auf Root-Ebene: "
    "`story` (String), "
    "`patch` (Objekt), "
    "`requests` (Array). "
    "`patch` muss mindestens diese Felder enthalten: "
    "`meta`, `characters`, `items_new`, `plotpoints_add`, `plotpoints_update`, "
    "`map_add_nodes`, `map_add_edges`, `events_add`. "
    "`meta.phase` muss `lobby`, `world_setup`, `character_setup_open`, `ready_to_start` oder `active` sein. "
    "Wenn du nichts ändern willst, nutze leere Objekte/Arrays statt Felder wegzulassen. "
    "Nutze in `characters` nur echte Slot-IDs als Keys. "
    "Für Fortschritt nutze pro Character optional `progression_events` als Array strukturierter Events. "
    "`requests` ist ein Array von Objekten mit mindestens `type` und `actor`."
)

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def deep_copy(value: Any) -> Any:
    return json.loads(json.dumps(value))

def ensure_data_dirs() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(CAMPAIGNS_DIR, exist_ok=True)

def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"

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

ELEMENT_GENERATOR_SCHEMA = {
    "type": "object",
    "properties": {
        "elements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "rarity": {"type": "string"},
                    "description": {"type": "string"},
                    "theme": {"type": "string"},
                    "status_effect_tags": {"type": "array", "items": {"type": "string"}},
                    "class_affinities": {"type": "array", "items": {"type": "string"}},
                    "skill_affinities": {"type": "array", "items": {"type": "string"}},
                    "lore_notes": {"type": "array", "items": {"type": "string"}},
                    "visual_motif": {"type": "string"},
                    "temperament": {"type": "string"},
                    "environment_bias": {"type": "string"},
                    "aliases": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["name", "description", "theme"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["elements"],
    "additionalProperties": False,
}

RESOURCE_KEYS = ("hp", "stamina", "aether", "stress", "corruption", "wounds")
ATTRIBUTE_KEYS = ("str", "dex", "con", "int", "wis", "cha", "luck")
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
PROGRESSION_EVENT_TYPES = {
    "combat_victory",
    "combat_survival",
    "major_discovery",
    "milestone_progress",
    "boss_defeated",
    "class_breakthrough",
    "skill_mastery_use",
    "skill_manifestation",
    "training_success",
    "bond_event",
}
PROGRESSION_EVENT_SEVERITIES = {"low", "medium", "high"}
PROGRESSION_EVENT_SEVERITY_MULTIPLIER = {
    "low": 1.0,
    "medium": 1.35,
    "high": 1.8,
}
PROGRESSION_EVENT_BASE_XP = {
    "combat_victory": {"character": 28, "class": 18, "skill": 20},
    "combat_survival": {"character": 14, "class": 8, "skill": 10},
    "major_discovery": {"character": 24, "class": 14, "skill": 8},
    "milestone_progress": {"character": 36, "class": 24, "skill": 14},
    "boss_defeated": {"character": 55, "class": 34, "skill": 26},
    "class_breakthrough": {"character": 26, "class": 30, "skill": 8},
    "skill_mastery_use": {"character": 10, "class": 6, "skill": 16},
    "skill_manifestation": {"character": 22, "class": 14, "skill": 26},
    "training_success": {"character": 14, "class": 10, "skill": 14},
    "bond_event": {"character": 12, "class": 8, "skill": 6},
}
PROGRESSION_EVENT_PRIORITY = {
    "boss_defeated": 100,
    "milestone_progress": 90,
    "class_breakthrough": 82,
    "skill_manifestation": 76,
    "combat_victory": 66,
    "major_discovery": 62,
    "skill_mastery_use": 52,
    "training_success": 46,
    "combat_survival": 40,
    "bond_event": 34,
}
PROGRESSION_DENSITY_CAP_NON_MILESTONE = {"inferred": 1, "total": 3}
PROGRESSION_DENSITY_CAP_MILESTONE = {"inferred": 2, "total": 5}
PROGRESSION_SET_DIRECT_KEYS = {
    "level",
    "xp_total",
    "xp_current",
    "xp_to_next",
    "class_level",
    "class_xp",
    "class_xp_to_next",
}
MANIFESTATION_STRONG_CUES = {
    "manifestiert",
    "entfesselt",
    "bricht hervor",
    "erstmals",
    "zum ersten mal",
    "erweckt",
    "wird geboren",
}
MANIFESTATION_EFFECT_CUES = {
    "schlägt",
    "schlagen",
    "drängt",
    "drängen",
    "fesselt",
    "fesseln",
    "blockiert",
    "blockieren",
    "verlangsamt",
    "verlangsamen",
    "durchbohrt",
    "durchbohren",
    "zerreißt",
    "zerreissen",
    "brechen",
    "schützt",
    "schützen",
    "versperrt",
    "versperren",
    "kontrolliert",
    "kontrollieren",
}
MANIFESTATION_TACTICAL_CUES = {
    "kampffeld",
    "deckung",
    "kontrolle",
    "schutz",
    "barriere",
    "angriff",
    "position",
    "ritual",
}
MANIFESTATION_WORLD_REACTION_CUES = {
    "gegner",
    "weicht",
    "stolpert",
    "erschrickt",
    "reagiert",
    "umgebung",
    "boden",
    "wand",
}
MANIFESTATION_COST_CUES = {
    "kostet",
    "schmerz",
    "belastet",
    "erschöpft",
    "vergiftung",
    "lebensenergie",
    "kontrollverlust",
    "risiko",
}
MANIFESTATION_MOTIF_GROUPS = {
    "spore": ("pilz", "spore", "myzel", "garten", "wurzel", "ranke", "moos"),
    "light": ("licht", "strahl", "sonne", "glanz", "heilig"),
    "shadow": ("schatten", "nacht", "dunkel", "finster", "schwärze"),
    "flame": ("feuer", "flamme", "glut", "asche"),
    "frost": ("eis", "frost", "kälte", "reif"),
    "storm": ("blitz", "sturm", "donner", "wind"),
    "martial": ("schwert", "klinge", "hieb", "stoß", "parade", "speer", "lanze", "faust", "tritt", "bogen"),
}
FIRST_SKILL_FORCE_PROBABILITY = 0.8
MANIFESTATION_SKILL_NAME_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
    },
    "required": ["name"],
    "additionalProperties": False,
}
MANIFESTATION_SKILL_NAME_SYSTEM_PROMPT = (
    "Du benennst genau einen neuen Fantasy-Skill für eine gerade entstehende Kraftmanifestation. "
    "Antworte NUR als JSON mit Feld 'name'. "
    "Regeln: deutsch, 1-4 Wörter, prägnant, kein Personenname, kein generisches Verb, kein Satzzeichen-Overkill."
)
SKILL_MANIFESTATION_VERB_BLACKLIST = {
    "kaempfen",
    "kämpfen",
    "rennen",
    "laufen",
    "springen",
    "ausweichen",
    "bewegen",
    "schlagen",
    "treffen",
    "manifestiert",
    "manifestierte",
    "einleiten",
    "einleitete",
    "entfesseln",
    "entfesselte",
    "erlernen",
    "erlernte",
    "weiter",
}
SKILL_MANIFESTATION_NAME_STOPWORDS = {
    "von",
    "und",
    "mit",
    "ohne",
    "durch",
    "gegen",
    "unter",
    "ueber",
}
SKILL_MANIFESTATION_NAME_TOKEN_BLACKLIST = {
    "klasse",
    "class",
    "spieler",
    "character",
    "charakter",
    "npc",
}
SKILL_KEYS = (
    "stealth",
    "perception",
    "survival",
    "athletics",
    "intimidation",
    "persuasion",
    "lore_occult",
    "crafting",
    "lockpicking",
    "endurance",
    "willpower",
    "tactics",
)
SKILL_RANKS = ("F", "E", "D", "C", "B", "A", "S")
SKILL_RANK_ORDER = {rank: index for index, rank in enumerate(SKILL_RANKS)}
CLASS_ASCENSION_STATUSES = {"none", "available", "active", "completed"}
INJURY_SEVERITIES = {"leicht", "mittel", "schwer"}
INJURY_HEALING_STAGES = {"frisch", "heilend", "fast_heil", "geheilt"}
LEGACY_ROLE_CLASS_MAP = {
    "frontline": {
        "id": "class_vorhut",
        "name": "Vorhut",
        "rank": "F",
        "affinity_tags": ["körper", "kampf", "schutz"],
        "description": "Geht voran, hält Treffer aus und bindet die schlimmste Gefahr zuerst.",
    },
    "scout": {
        "id": "class_spaeher",
        "name": "Späher",
        "rank": "F",
        "affinity_tags": ["bewegung", "heimlichkeit", "sinn"],
        "description": "Lebt von Überblick, Fährten und riskanten Vorstößen.",
    },
    "face": {
        "id": "class_unterhaendler",
        "name": "Unterhändler",
        "rank": "F",
        "affinity_tags": ["sozial", "sprache", "einfluss"],
        "description": "Zwingt Gespräche, Drohungen und Deals in eine brauchbare Richtung.",
    },
    "support": {
        "id": "class_waechter",
        "name": "Wächter",
        "rank": "F",
        "affinity_tags": ["schutz", "heilung", "standhaft"],
        "description": "Hält andere auf den Beinen und stabilisiert chaotische Lagen.",
    },
    "tueftler": {
        "id": "class_schrotttueftler",
        "name": "Schrotttüftler",
        "rank": "F",
        "affinity_tags": ["technik", "improvisation", "werkzeug"],
        "description": "Macht aus Schrott, Relikten und Notlösungen einen Vorteil.",
    },
    "occult": {
        "id": "class_okkultist",
        "name": "Okkultist",
        "rank": "F",
        "affinity_tags": ["okkult", "ritual", "schatten"],
        "description": "Greift nach verbotenen Wahrheiten und zahlt dafür einen Preis.",
    },
}
LEGACY_SKILL_NAME_MAP = {
    "stealth": "Schleichen",
    "perception": "Wahrnehmung",
    "survival": "Überleben",
    "athletics": "Athletik",
    "intimidation": "Einschüchtern",
    "persuasion": "Überzeugen",
    "lore_occult": "Okkultes Wissen",
    "crafting": "Handwerk",
    "lockpicking": "Schlösser öffnen",
    "endurance": "Ausdauer",
    "willpower": "Willenskraft",
    "tactics": "Taktik",
}
LEGACY_SKILL_TAGS = {
    "stealth": ["bewegung", "heimlichkeit"],
    "perception": ["sinn", "wahrnehmung"],
    "survival": ["wildnis", "ausdauer"],
    "athletics": ["körper", "kraft"],
    "intimidation": ["sozial", "druck"],
    "persuasion": ["sozial", "sprache"],
    "lore_occult": ["wissen", "okkult"],
    "crafting": ["technik", "handwerk"],
    "lockpicking": ["technik", "präzision"],
    "endurance": ["körper", "regeneration"],
    "willpower": ["geist", "widerstand"],
    "tactics": ["kampf", "strategie"],
}
RESISTANCE_KEYS = ("physical", "fire", "cold", "lightning", "poison", "bleed", "shadow", "holy", "curse", "fear")
SKILL_ATTRIBUTE_MAP = {
    "stealth": "dex",
    "perception": "wis",
    "survival": "wis",
    "athletics": "str",
    "intimidation": "cha",
    "persuasion": "cha",
    "lore_occult": "int",
    "crafting": "int",
    "lockpicking": "dex",
    "endurance": "con",
    "willpower": "wis",
    "tactics": "int",
}
SKILL_RANK_THRESHOLDS = (
    ("S", 14),
    ("A", 11),
    ("B", 9),
    ("C", 7),
    ("D", 5),
    ("E", 3),
    ("F", 1),
)
SKILL_OUTCOME_XP = {"success": 12, "partial": 8, "fail": 5}
SKILL_PATHS = {
    "stealth": ["Shadow Veil", "Ghost Scout", "Cursed Slip"],
    "perception": ["Hunter Sight", "Arc Sense", "Dread Echo"],
    "survival": ["Ash Walker", "Beast Route", "Starved Resolve"],
    "athletics": ["Breaker Frame", "Wild Rush", "Blood Sprint"],
    "intimidation": ["Grave Voice", "Tyrant Stare", "Panic Chorus"],
    "persuasion": ["Silver Tongue", "False Halo", "Oath Binder"],
    "lore_occult": ["Hex Reader", "Curse Weaving", "Void Lexicon"],
    "crafting": ["Trap Architect", "Relic Smith", "Blight Tinkerer"],
    "lockpicking": ["Whisper Keys", "Ruin Fingers", "Void Picks"],
    "endurance": ["Iron Body", "Last Ember", "Pain Vessel"],
    "willpower": ["Soul Brace", "Moon Mind", "Hollow Oath"],
    "tactics": ["Kill Box", "War Reader", "Night Marshal"],
}
SKILL_EVOLUTIONS = {
    "stealth": ["Shadow Veil", "Silent Steps", "Night Skin"],
    "perception": ["Predator Glimpse", "Thread Sense", "Fear Scent"],
    "athletics": ["Breaker Surge", "Iron Leap", "Ruin Charge"],
    "lore_occult": ["Curse Weaving", "Hex Memory", "Blood Lexicon"],
    "crafting": ["Trap Architect", "Relic Stitching", "Ash Forge"],
    "endurance": ["Iron Body", "Pain Engine", "Grave Stance"],
    "tactics": ["Kill Grid", "Night Marshal", "Ambush Doctrine"],
}
SKILL_FUSIONS = {
    ("perception", "stealth"): {"id": "skill_predator_sense", "name": "Predator Sense", "rank": "S"},
    ("athletics", "endurance"): {"id": "skill_iron_body", "name": "Iron Body", "rank": "S"},
    ("lore_occult", "willpower"): {"id": "skill_curse_weaving", "name": "Curse Weaving", "rank": "S"},
    ("crafting", "tactics"): {"id": "skill_trap_architect", "name": "Trap Architect", "rank": "S"},
}

DEFAULT_DYNAMIC_SKILL_LEVEL_MAX = 10
DEFAULT_NUMERIC_SKILL_DELTA_XP = 20

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

AUTO_INJURY_PATTERNS = (
    re.compile(r"\b((?:tiefer?|tiefe|tiefen|klaffender?|klaffende|blutiger?|blutige|frischer?|frische|heftiger?|heftige)\s+)?(Schnitt(?:\s+am|\s+an der|\s+in der)?\s+[A-Za-zÄÖÜäöüß\-]+(?:\s+[A-Za-zÄÖÜäöüß\-]+){0,3})", flags=re.IGNORECASE),
    re.compile(r"\b((?:tiefer?|tiefe|tiefen|klaffender?|klaffende|blutiger?|blutige|frischer?|frische)\s+)?(Stichwunde(?:\s+am|\s+an der|\s+in der)?\s+[A-Za-zÄÖÜäöüß\-]+(?:\s+[A-Za-zÄÖÜäöüß\-]+){0,3})", flags=re.IGNORECASE),
    re.compile(r"\b((?:tiefer?|tiefe|tiefen|blutiger?|blutige)\s+)?(Bisswunde(?:\s+am|\s+an der|\s+in der)?\s+[A-Za-zÄÖÜäöüß\-]+(?:\s+[A-Za-zÄÖÜäöüß\-]+){0,3})", flags=re.IGNORECASE),
    re.compile(r"\b((?:schwere|heftige|frische)\s+)?(Brandwunde(?:\s+am|\s+an der|\s+in der)?\s+[A-Za-zÄÖÜäöüß\-]+(?:\s+[A-Za-zÄÖÜäöüß\-]+){0,3})", flags=re.IGNORECASE),
    re.compile(r"\b((?:schwere|heftige)\s+)?(Prellung(?:\s+am|\s+an der|\s+in der)?\s+[A-Za-zÄÖÜäöüß\-]+(?:\s+[A-Za-zÄÖÜäöüß\-]+){0,3})", flags=re.IGNORECASE),
    re.compile(r"\b(gebrochene[rsnm]?\s+[A-Za-zÄÖÜäöüß\-]+(?:\s+[A-Za-zÄÖÜäöüß\-]+){0,3})", flags=re.IGNORECASE),
    re.compile(r"\b(verstauchte[rsnm]?\s+[A-Za-zÄÖÜäöüß\-]+(?:\s+[A-Za-zÄÖÜäöüß\-]+){0,3})", flags=re.IGNORECASE),
)

app = FastAPI(title="Aelunor")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.mount("/v1/assets", StaticFiles(directory=UI_V1_ASSETS_DIR, check_dir=False), name="v1-assets")
ensure_campaign_storage()

@app.get("/", response_class=HTMLResponse)
def index() -> str:
    with open(os.path.join(BASE_DIR, "static", "index.html"), "r", encoding="utf-8") as f:
        return f.read()

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
    ensure_campaign_storage()
    campaign_ids = list_campaign_ids()
    if not campaign_ids:
        return deep_copy(INITIAL_STATE)
    return load_campaign(campaign_ids[0])["state"]

@app.get("/api/llm/status")
def get_llm_status() -> Dict[str, Any]:
    available_models: List[Dict[str, Any]] = []
    ollama_ok = False
    error = ""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=15)
        if response.status_code != 200:
            raise RuntimeError(f"Ollama error {response.status_code}: {response.text[:300]}")
        payload = response.json() or {}
        available_models = payload.get("models", []) or []
        ollama_ok = True
    except Exception as exc:
        error = str(exc)
    return {
        "ollama_url": OLLAMA_URL,
        "configured_model": OLLAMA_MODEL,
        "request_timeout_sec": OLLAMA_TIMEOUT_SEC,
        "seed": OLLAMA_SEED,
        "temperature": OLLAMA_TEMPERATURE,
        "num_ctx": OLLAMA_NUM_CTX,
        "ollama_ok": ollama_ok,
        "configured_model_available": any((entry or {}).get("name") == OLLAMA_MODEL for entry in available_models),
        "available_models": [
            {
                "name": entry.get("name"),
                "size": entry.get("size"),
                "parameter_size": ((entry.get("details") or {}).get("parameter_size")),
                "family": ((entry.get("details") or {}).get("family")),
            }
            for entry in available_models
        ],
        "error": error,
    }

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
