import hashlib
import json
import os
import queue
import random
import re
import secrets
import threading
import time
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, Generator, List, Literal, Optional

import requests
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.getenv("DATA_DIR", "/data")
LEGACY_STATE_PATH = os.path.join(DATA_DIR, "state.json")
CAMPAIGNS_DIR = os.path.join(DATA_DIR, "campaigns")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_SEED = int(os.getenv("OLLAMA_SEED", "123"))
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.6"))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))

LEGACY_CHARACTERS = ("Matchek", "Abo", "Beni")
ACTION_TYPES = ("do", "say", "story")
PHASES = ("world_setup", "character_setup", "adventure")
SLOT_PREFIX = "slot_"
MAX_PLAYERS = 6
MAX_TURN_MODEL_ATTEMPTS = 3
LIVE_ACTIVITY_TTLS = {
    "typing_turn": 5,
    "editing_turn": 6,
    "claiming_slot": 6,
    "building_character": 8,
    "building_world": 8,
    "reviewing_choices": 6,
}
BLOCKING_ACTION_TTL = 120
SSE_PING_INTERVAL = 15

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
    "do": "Konkrete In-World-Aktion der Figur.",
    "say": "Gesprochene Rede der Figur.",
    "story": "Gezielte Story-Lenkung, Fokus oder Szenenwunsch aus Spielersicht.",
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
    "Bei Charakteren bleibe konsistent mit bereits beantworteten Feldern wie Geschlecht, Rolle und Ton."
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

TURN_RESPONSE_JSON_CONTRACT = (
    "Antworte mit genau einem JSON-Objekt ohne Markdown und ohne Erklärtext. "
    "Pflichtfelder auf Root-Ebene: "
    "`story` (String), "
    "`patch` (Objekt), "
    "`requests` (Array). "
    "`patch` muss mindestens diese Felder enthalten: "
    "`meta`, `characters`, `items_new`, `plotpoints_add`, `plotpoints_update`, "
    "`map_add_nodes`, `map_add_edges`, `events_add`. "
    "`meta.phase` muss `world_setup`, `character_setup` oder `adventure` sein. "
    "Wenn du nichts ändern willst, nutze leere Objekte/Arrays statt Felder wegzulassen. "
    "Nutze in `characters` nur echte Slot-IDs als Keys. "
    "`requests` ist ein Array von Objekten mit mindestens `type` und `actor`."
)

LIVE_STATE_LOCK = threading.Lock()
LIVE_STATE_REGISTRY: Dict[str, Dict[str, Any]] = {}


def default_live_state() -> Dict[str, Any]:
    return {
        "activities": {},
        "blocking_action": None,
        "version": 0,
        "subscribers": [],
    }


def iso_to_epoch(value: str) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def live_state_for_campaign(campaign_id: str) -> Dict[str, Any]:
    with LIVE_STATE_LOCK:
        return live_state_for_campaign_unlocked(campaign_id)


def live_state_for_campaign_unlocked(campaign_id: str) -> Dict[str, Any]:
    state = LIVE_STATE_REGISTRY.get(campaign_id)
    if state is None:
        state = default_live_state()
        LIVE_STATE_REGISTRY[campaign_id] = state
    return state


def live_presence_snapshot(state: Dict[str, Any]) -> Dict[str, Any]:
    activities: Dict[str, Dict[str, Any]] = {}
    for player_id, activity in (state.get("activities") or {}).items():
        activities[player_id] = {
            key: value
            for key, value in activity.items()
            if not str(key).startswith("_")
        }
    blocking = state.get("blocking_action")
    return {
        "version": state.get("version", 0),
        "activities": activities,
        "blocking_action": {
            key: value
            for key, value in (blocking or {}).items()
            if not str(key).startswith("_")
        }
        if blocking
        else None,
    }


def cleanup_live_state_locked(state: Dict[str, Any]) -> bool:
    changed = False
    now = time.time()
    expired_players = [
        player_id
        for player_id, activity in (state.get("activities") or {}).items()
        if float(activity.get("_expires_at_ts") or 0) <= now
    ]
    for player_id in expired_players:
        state["activities"].pop(player_id, None)
        changed = True
    blocking = state.get("blocking_action")
    if blocking and float(blocking.get("_expires_at_ts") or 0) <= now:
        state["blocking_action"] = None
        changed = True
    if changed:
        state["version"] = int(state.get("version", 0)) + 1
    return changed


def cleanup_live_state(campaign_id: str) -> bool:
    with LIVE_STATE_LOCK:
        state = live_state_for_campaign_unlocked(campaign_id)
        return cleanup_live_state_locked(state)


def live_snapshot(campaign_id: str) -> Dict[str, Any]:
    with LIVE_STATE_LOCK:
        state = live_state_for_campaign_unlocked(campaign_id)
        cleanup_live_state_locked(state)
        return live_presence_snapshot(state)


def broadcast_live_event(campaign_id: str, event_name: str, payload: Dict[str, Any]) -> None:
    with LIVE_STATE_LOCK:
        state = live_state_for_campaign_unlocked(campaign_id)
        subscribers = list(state.get("subscribers") or [])
    message = {"event": event_name, "data": payload}
    stale: List[queue.Queue] = []
    for subscriber in subscribers:
        try:
            subscriber.put_nowait(message)
        except queue.Full:
            stale.append(subscriber)
    if not stale:
        return
    with LIVE_STATE_LOCK:
        state = live_state_for_campaign_unlocked(campaign_id)
        state["subscribers"] = [subscriber for subscriber in state.get("subscribers") or [] if subscriber not in stale]


def broadcast_presence_sync(campaign_id: str) -> None:
    snapshot = live_snapshot(campaign_id)
    broadcast_live_event(campaign_id, "presence_sync", snapshot)


def broadcast_campaign_sync(campaign_id: str, reason: str = "campaign_updated") -> None:
    with LIVE_STATE_LOCK:
        state = live_state_for_campaign_unlocked(campaign_id)
        cleanup_live_state_locked(state)
        state["version"] = int(state.get("version", 0)) + 1
        version = state["version"]
    broadcast_live_event(
        campaign_id,
        "campaign_sync",
        {
            "version": version,
            "reason": reason,
        },
    )


def make_activity_label(campaign: Dict[str, Any], player_id: str, kind: str) -> str:
    display_name = (campaign.get("players", {}).get(player_id, {}) or {}).get("display_name") or "Jemand"
    return {
        "typing_turn": f"{display_name} schreibt...",
        "editing_turn": f"{display_name} ändert die Geschichte...",
        "claiming_slot": f"{display_name} wählt einen Platz in der Gruppe...",
        "building_character": f"{display_name} formt die Figur...",
        "building_world": f"{display_name} entwirft die Welt...",
        "reviewing_choices": f"{display_name} prüft die nächsten Schritte...",
    }.get(kind, f"{display_name} ist aktiv...")


def make_blocking_label(campaign: Dict[str, Any], player_id: Optional[str], kind: str) -> str:
    display_name = (campaign.get("players", {}).get(player_id or "", {}) or {}).get("display_name") or "Jemand"
    return {
        "generate_intro": f"{display_name} beschwört den Auftakt der Geschichte...",
        "submit_turn": f"{display_name} handelt in der Szene...",
        "continue_turn": f"{display_name} führt die Geschichte weiter...",
        "retry_turn": f"{display_name} formt den letzten Moment neu...",
        "undo_turn": f"{display_name} nimmt den letzten Schritt zurück...",
        "character_randomize": f"{display_name} ruft eine neue Gestalt hervor...",
        "world_randomize": f"{display_name} lässt die Welt Gestalt annehmen...",
        "building_character": f"{display_name} formt die Figur...",
        "building_world": f"{display_name} entwirft die Welt...",
    }.get(kind, f"{display_name} wirkt auf die Szene ein...")


def set_live_activity(
    campaign: Dict[str, Any],
    player_id: str,
    kind: str,
    *,
    slot_id: Optional[str] = None,
    target_turn_id: Optional[str] = None,
) -> Dict[str, Any]:
    ttl = LIVE_ACTIVITY_TTLS.get(kind, 6)
    now = utc_now()
    expires_at_ts = time.time() + ttl
    activity = {
        "kind": kind,
        "label": make_activity_label(campaign, player_id, kind),
        "slot_id": slot_id,
        "target_turn_id": target_turn_id,
        "blocking": False,
        "updated_at": now,
        "expires_at": datetime.fromtimestamp(expires_at_ts, tz=timezone.utc).isoformat(),
        "_expires_at_ts": expires_at_ts,
    }
    campaign_id = campaign["campaign_meta"]["campaign_id"]
    with LIVE_STATE_LOCK:
        state = live_state_for_campaign_unlocked(campaign_id)
        cleanup_live_state_locked(state)
        state["activities"][player_id] = activity
        state["version"] = int(state.get("version", 0)) + 1
    broadcast_presence_sync(campaign_id)
    return activity


def clear_live_activity(campaign_id: str, player_id: Optional[str]) -> None:
    if not player_id:
        return
    changed = False
    with LIVE_STATE_LOCK:
        state = live_state_for_campaign_unlocked(campaign_id)
        cleanup_live_state_locked(state)
        if player_id in state.get("activities", {}):
            state["activities"].pop(player_id, None)
            state["version"] = int(state.get("version", 0)) + 1
            changed = True
    if changed:
        broadcast_presence_sync(campaign_id)


def start_blocking_action(
    campaign: Dict[str, Any],
    *,
    player_id: Optional[str],
    kind: str,
    slot_id: Optional[str] = None,
) -> Dict[str, Any]:
    now = utc_now()
    expires_at_ts = time.time() + BLOCKING_ACTION_TTL
    blocking_action = {
        "player_id": player_id,
        "slot_id": slot_id,
        "kind": kind,
        "label": make_blocking_label(campaign, player_id, kind),
        "started_at": now,
        "_expires_at_ts": expires_at_ts,
    }
    campaign_id = campaign["campaign_meta"]["campaign_id"]
    with LIVE_STATE_LOCK:
        state = live_state_for_campaign_unlocked(campaign_id)
        cleanup_live_state_locked(state)
        state["blocking_action"] = blocking_action
        state["version"] = int(state.get("version", 0)) + 1
    broadcast_presence_sync(campaign_id)
    return blocking_action


def clear_blocking_action(campaign_id: str) -> None:
    changed = False
    with LIVE_STATE_LOCK:
        state = live_state_for_campaign_unlocked(campaign_id)
        cleanup_live_state_locked(state)
        if state.get("blocking_action"):
            state["blocking_action"] = None
            state["version"] = int(state.get("version", 0)) + 1
            changed = True
    if changed:
        broadcast_presence_sync(campaign_id)


def sse_message(event_name: str, payload: Dict[str, Any]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def campaign_event_stream(campaign_id: str) -> Generator[str, None, None]:
    subscriber: queue.Queue = queue.Queue(maxsize=100)
    with LIVE_STATE_LOCK:
        state = live_state_for_campaign_unlocked(campaign_id)
        state["subscribers"].append(subscriber)
    yield sse_message("presence_sync", live_snapshot(campaign_id))
    idle_ticks = 0
    try:
        while True:
            try:
                message = subscriber.get(timeout=1.0)
                idle_ticks = 0
                yield sse_message(message["event"], message["data"])
            except queue.Empty:
                idle_ticks += 1
                if cleanup_live_state(campaign_id):
                    yield sse_message("presence_sync", live_snapshot(campaign_id))
                    idle_ticks = 0
                    continue
                if idle_ticks >= SSE_PING_INTERVAL:
                    idle_ticks = 0
                    yield sse_message("ping", {"ts": utc_now()})
    finally:
        with LIVE_STATE_LOCK:
            state = live_state_for_campaign_unlocked(campaign_id)
            state["subscribers"] = [entry for entry in state.get("subscribers") or [] if entry is not subscriber]


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
        "meta": {"phase": INITIAL_STATE["meta"]["phase"]},
        "characters": {},
        "items_new": {},
        "plotpoints_add": [],
        "plotpoints_update": [],
        "map_add_nodes": [],
        "map_add_edges": [],
        "events_add": [],
    }


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
            "party_role": "",
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
        "class_state": {
            "class_id": "",
            "class_name": "",
            "unlocked_at_turn": 0,
            "visual_modifiers": [],
        },
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
        "skills": {skill_name: default_skill_state(skill_name) for skill_name in SKILL_KEYS},
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
            "system_fragments": 0,
            "system_cores": 0,
            "attribute_points": 0,
            "skill_points": 0,
            "talent_points": 0,
            "paths": [],
            "potential_cards": [],
        },
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
        "equip": {"weapon": "", "armor": ""},
        "potential": [],
    }


RESOURCE_KEYS = ("hp", "stamina", "aether", "stress", "corruption", "wounds")
ATTRIBUTE_KEYS = ("str", "dex", "con", "int", "wis", "cha", "luck")
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
ROLE_STARTER_SKILLS = {
    "frontline": {"athletics": 1, "endurance": 1},
    "scout": {"stealth": 1, "perception": 1},
    "face": {"persuasion": 1, "intimidation": 1},
    "support": {"endurance": 1, "willpower": 1},
    "occult": {"lore_occult": 1, "willpower": 1},
    "tueftler": {"crafting": 1, "lockpicking": 1},
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


def skill_display_name(skill_name: str) -> str:
    return skill_name.replace("_", " ").title()


def skill_level_value(character: Dict[str, Any], skill_name: str) -> int:
    skill = normalize_skill_state(skill_name, (character.get("skills") or {}).get(skill_name, default_skill_state(skill_name)))
    return int(skill.get("level", 0) or 0)


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


def apply_role_starter_skills(character: Dict[str, Any], role_text: str) -> None:
    if any(skill_level_value(character, skill_name) > 0 for skill_name in SKILL_KEYS):
        return
    loadout = ROLE_STARTER_SKILLS.get(role_key(role_text), {})
    if not loadout:
        return
    skills = character.setdefault("skills", {})
    for skill_name, level in loadout.items():
        skill = normalize_skill_state(skill_name, skills.get(skill_name, default_skill_state(skill_name)))
        skill["level"] = max(int(skill.get("level", 0) or 0), int(level))
        skill["xp"] = 0
        skill["next_xp"] = next_skill_xp_for_level(skill["level"])
        skills[skill_name] = normalize_skill_state(skill_name, skill)


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
    }


def resource_delta_payload() -> Dict[str, int]:
    return {key: 0 for key in RESOURCE_KEYS}


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
    return {
        "hp": max(1, 10 + int(attrs.get("con", 0) or 0) + int(age_modifiers["resource_deltas"].get("hp_max", 0) or 0)),
        "stamina": max(1, 10 + int(attrs.get("con", 0) or 0) + int(age_modifiers["resource_deltas"].get("stamina_max", 0) or 0)),
        "aether": max(1, 5 + int(attrs.get("int", 0) or 0)),
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


def rebuild_resource_maxima(character: Dict[str, Any], items_db: Dict[str, Any], age_modifiers: Dict[str, Any]) -> None:
    resources = character.setdefault("resources", {})
    layer_presence: Dict[str, Dict[str, bool]] = {}
    for resource_key in RESOURCE_KEYS:
        resource = resources.setdefault(resource_key, {})
        layer_presence[resource_key] = {
            "base_max": "base_max" in resource,
            "bonus_max": "bonus_max" in resource,
        }
        resource.setdefault("current", 0)
        resource.setdefault("base_max", int(resource.get("max", 0) or 0))
        resource.setdefault("bonus_max", 0)
        resource.setdefault("max", int(resource.get("max", 0) or 0))

    base_maxima = calculate_base_resource_maxima(character, age_modifiers)
    known_bonus = calculate_bonus_resource_maxima(character, items_db)
    migrate_legacy_resource_bonus_modifiers(character, base_maxima, known_bonus, layer_presence)
    total_bonus = calculate_bonus_resource_maxima(character, items_db)

    for resource_key in RESOURCE_KEYS:
        resource = resources[resource_key]
        resource["base_max"] = max(0, int(base_maxima.get(resource_key, resource.get("base_max", 0)) or 0))
        resource["bonus_max"] = int(total_bonus.get(resource_key, 0) or 0)
        resource["max"] = max(0, int(resource["base_max"]) + int(resource["bonus_max"]))
        resource["current"] = clamp(int(resource.get("current", 0) or 0), 0, int(resource["max"]))


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


def sync_legacy_character_fields(character: Dict[str, Any]) -> None:
    resources = character.get("resources", {})
    character["hp"] = int(((resources.get("hp") or {}).get("current", 0)) or 0)
    character["stamina"] = int(((resources.get("stamina") or {}).get("current", 0)) or 0)
    character["conditions"] = [
        effect.get("name", "")
        for effect in (character.get("effects") or [])
        if effect.get("visible", True) and effect.get("name")
    ][:6]
    equipment = character.get("equipment", {}) or {}
    character["equip"] = {
        "weapon": equipment.get("weapon", ""),
        "armor": equipment.get("chest", ""),
    }
    character["potential"] = [card.get("name", card.get("id", "")) for card in (character.get("progression", {}).get("potential_cards") or [])]


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
    class_state = character.get("class_state", {}) or {}
    visuals = []
    class_id = class_state.get("class_id", "")
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
    before_class = ((before_character.get("class_state") or {}).get("class_id", ""))
    after_class = ((after_character.get("class_state") or {}).get("class_id", ""))
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
    hp_current = int((((character.get("resources") or {}).get("hp") or {}).get("current", 0)) or 0)
    downed = hp_current <= 0
    in_combat = bool(character.get("combat_state", {}).get("in_combat", False))
    can_act = not downed
    for effect in character.get("effects", []) or []:
        effect_tags = set(effect.get("tags", []) or [])
        if "stun" in effect_tags or effect.get("category") == "stun":
            can_act = False
        if effect.get("category") == "combat":
            in_combat = True
    if int((((character.get("resources") or {}).get("wounds") or {}).get("current", 0)) or 0) >= 3:
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
    progression.setdefault("system_fragments", 0)
    progression.setdefault("system_cores", 0)
    progression.setdefault("attribute_points", 0)
    progression.setdefault("skill_points", 0)
    progression.setdefault("talent_points", 0)
    progression.setdefault("paths", [])
    progression.setdefault("potential_cards", [])


def apply_system_xp(character: Dict[str, Any], amount: int) -> None:
    if amount <= 0:
        return
    ensure_progression_shape(character)
    progression = character["progression"]
    progression["system_xp"] = int(progression.get("system_xp", 0) or 0) + amount
    while progression["system_xp"] >= int(progression.get("next_system_xp", 100) or 100):
        progression["system_xp"] -= int(progression.get("next_system_xp", 100) or 100)
        progression["system_level"] = int(progression.get("system_level", 1) or 1) + 1
        progression["attribute_points"] = int(progression.get("attribute_points", 0) or 0) + 1
        progression["skill_points"] = int(progression.get("skill_points", 0) or 0) + 1
        progression["talent_points"] = int(progression.get("talent_points", 0) or 0) + 1
        progression["next_system_xp"] = 100 + ((int(progression["system_level"]) - 1) * 50)


def refresh_skill_progression(character: Dict[str, Any]) -> None:
    ensure_progression_shape(character)
    skills = character.setdefault("skills", {})
    for skill_name in SKILL_KEYS:
        skills[skill_name] = normalize_skill_state(skill_name, skills.get(skill_name, default_skill_state(skill_name)))

    strong_skills = [name for name, data in skills.items() if data.get("rank") in ("A", "S")]
    for skill_name, skill in skills.items():
        skill["evolutions"] = SKILL_EVOLUTIONS.get(skill_name, []) if skill.get("rank") in ("A", "S") else []
        if skill.get("rank") == "S":
            skill["awakened"] = True
        if skill.get("rank") in ("C", "B", "A", "S") and not skill.get("path"):
            skill["path_choice_available"] = True
            skill["path_options"] = SKILL_PATHS.get(skill_name, [])
        else:
            skill["path_choice_available"] = False
            skill["path_options"] = SKILL_PATHS.get(skill_name, [])
        skill["fusion_candidates"] = []
        for other in strong_skills:
            if other == skill_name:
                continue
            fusion = SKILL_FUSIONS.get(tuple(sorted((skill_name, other))))
            if fusion:
                skill["fusion_candidates"].append(
                    {
                        "with": other,
                        "with_display": skill_display_name(other),
                        "result": fusion["name"],
                        "result_id": fusion["id"],
                        "rank": fusion["rank"],
                        "requires_core": 1,
                    }
                )
        skill["next_evolution"] = skill["evolutions"][0] if skill["evolutions"] else ""
        skill["unlocks"] = []
        if skill["path"]:
            skill["unlocks"].append(f"Pfad: {skill['path']}")
        if skill["next_evolution"]:
            skill["unlocks"].append(f"Awakening: {skill['next_evolution']}")


def grant_skill_xp(character: Dict[str, Any], skill_name: str, outcome: str) -> List[str]:
    if skill_name not in SKILL_KEYS:
        return []
    ensure_progression_shape(character)
    refresh_skill_progression(character)
    skill = character["skills"][skill_name]
    previous_rank = skill.get("rank", "F")
    previous_level = int(skill.get("level", 1) or 1)
    gained = SKILL_OUTCOME_XP.get(outcome, 0)
    skill["xp"] = int(skill.get("xp", 0) or 0) + gained
    messages = []
    while skill["xp"] >= int(skill.get("next_xp", next_skill_xp_for_level(skill["level"])) or next_skill_xp_for_level(skill["level"])):
        skill["xp"] -= int(skill.get("next_xp", next_skill_xp_for_level(skill["level"])) or next_skill_xp_for_level(skill["level"]))
        skill["level"] = clamp(int(skill.get("level", 1) or 1) + 1, 1, 20)
        skill["next_xp"] = next_skill_xp_for_level(skill["level"])
        messages.append(f"{skill_display_name(skill_name)} erreicht Lv {skill['level']}.")
    skill["rank"] = skill_rank_for_level(skill["level"])
    if skill["rank"] != previous_rank:
        messages.append(f"{skill_display_name(skill_name)} steigt auf Rank {skill['rank']}.")
        apply_system_xp(character, 50)
        character["progression"]["skill_points"] = int(character["progression"].get("skill_points", 0) or 0) + 1
    elif int(skill["level"]) > previous_level:
        apply_system_xp(character, 20)
    refresh_skill_progression(character)
    return messages


def parse_skill_event(campaign: Dict[str, Any], event_text: str) -> Optional[Dict[str, str]]:
    text = str(event_text or "").strip()
    if not text:
        return None
    canonical = re.search(r"skillxp\s*:\s*(slot_\d+)\s*:\s*([a-z_]+)\s*:\s*(success|partial|fail)", text, re.IGNORECASE)
    if canonical:
        return {"slot_id": canonical.group(1), "skill": canonical.group(2).lower(), "outcome": canonical.group(3).lower()}
    human = re.search(r"(.+?)\s+used\s+([A-Za-z_ ]+).*:\s*(success|partial|fail)", text, re.IGNORECASE)
    if not human:
        return None
    actor_text = human.group(1).strip()
    skill_text = human.group(2).strip().lower().replace(" ", "_")
    slot_name = None
    for current_slot in campaign_slots(campaign):
        if actor_text.lower() in {current_slot.lower(), display_name_for_slot(campaign, current_slot).lower()}:
            slot_name = current_slot
            break
    if not slot_name:
        return None
    if skill_text not in SKILL_KEYS:
        aliases = {skill_display_name(key).lower().replace(" ", "_"): key for key in SKILL_KEYS}
        skill_text = aliases.get(skill_text, skill_text)
    if skill_text not in SKILL_KEYS:
        return None
    return {"slot_id": slot_name, "skill": skill_text, "outcome": human.group(3).lower()}


def build_skill_system_requests(
    campaign: Dict[str, Any],
    state_before: Dict[str, Any],
    state_after: Dict[str, Any],
) -> List[Dict[str, Any]]:
    items_db = state_after.get("items", {}) or {}
    generated = []
    for slot_name in campaign_slots(campaign):
        before_character = normalize_character_state(
            ((state_before.get("characters") or {}).get(slot_name) or blank_character_state(slot_name)),
            slot_name,
            items_db,
        )
        after_character = normalize_character_state(
            ((state_after.get("characters") or {}).get(slot_name) or blank_character_state(slot_name)),
            slot_name,
            items_db,
        )
        for skill_name in SKILL_KEYS:
            before_skill = normalize_skill_state(skill_name, (before_character.get("skills") or {}).get(skill_name))
            after_skill = normalize_skill_state(skill_name, (after_character.get("skills") or {}).get(skill_name))
            display_name = display_name_for_slot(campaign, slot_name)
            skill_name_display = skill_display_name(skill_name)
            if not before_skill.get("path_choice_available") and after_skill.get("path_choice_available"):
                generated.append(
                    {
                        "type": "choice",
                        "actor": slot_name,
                        "question": f"{display_name}: {skill_name_display} hat Rank {after_skill['rank']} erreicht. Welchen Pfad willst du öffnen?",
                        "options": [str(option) for option in (after_skill.get("path_options") or [])[:3]],
                    }
                )
            if len(after_skill.get("evolutions", [])) > len(before_skill.get("evolutions", [])):
                generated.append(
                    {
                        "type": "choice",
                        "actor": slot_name,
                        "question": f"{display_name}: {skill_name_display} kann erwachen. Welche Entwicklung interessiert dich?",
                        "options": [str(option) for option in (after_skill.get("evolutions") or [])[:3]],
                    }
                )
            before_fusions = {(entry.get("with"), entry.get("result")) for entry in (before_skill.get("fusion_candidates") or [])}
            new_fusions = [
                entry
                for entry in (after_skill.get("fusion_candidates") or [])
                if (entry.get("with"), entry.get("result")) not in before_fusions
            ]
            if new_fusions:
                generated.append(
                    {
                        "type": "choice",
                        "actor": slot_name,
                        "question": f"{display_name}: {skill_name_display} hat neue Fusionen freigeschaltet. Welche Route willst du später verfolgen?",
                        "options": [
                            f"{entry.get('result')} mit {entry.get('with_display')} (kostet {entry.get('requires_core', 1)} System Core)"
                            for entry in new_fusions[:3]
                        ],
                    }
                )
    return generated


def apply_skill_events(campaign: Dict[str, Any], state: Dict[str, Any], events: List[str]) -> List[str]:
    messages = []
    items_db = state.get("items", {}) or {}
    for event_text in events or []:
        parsed = parse_skill_event(campaign, event_text)
        if not parsed:
            continue
        slot_name = parsed["slot_id"]
        if slot_name not in (state.get("characters") or {}):
            continue
        character = state["characters"][slot_name]
        messages.extend(grant_skill_xp(character, parsed["skill"], parsed["outcome"]))
        rebuild_character_derived(character, items_db)
    return messages


def rebuild_character_derived(character: Dict[str, Any], items_db: Dict[str, Any], world_time: Optional[Dict[str, Any]] = None) -> None:
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


def normalize_character_state(character: Dict[str, Any], slot_name: str, items_db: Dict[str, Any]) -> Dict[str, Any]:
    base = blank_character_state(slot_name)
    merged = deep_copy(base)
    merged.update({key: value for key, value in character.items() if key not in ("bio", "resources", "attributes", "derived", "skills", "inventory", "equipment", "progression", "journal", "appearance", "class_state", "aging", "modifiers")})
    merged["bio"].update(character.get("bio", {}) or {})
    merged["appearance"] = normalize_appearance_state({**merged, "appearance": character.get("appearance", {}) or {}})
    merged["appearance_history"] = [deep_copy(entry) for entry in (character.get("appearance_history") or []) if isinstance(entry, dict)]
    merged["class_state"].update(character.get("class_state", {}) or {})
    merged["faction_memberships"] = [deep_copy(entry) for entry in (character.get("faction_memberships") or []) if isinstance(entry, dict)]
    merged["aging"].update(character.get("aging", {}) or {})
    merged["modifiers"].update(character.get("modifiers", {}) or {})
    ensure_character_modifier_shape(merged)

    merged["resources"].update(character.get("resources", {}) or {})
    if "hp" in character:
        merged["resources"]["hp"]["current"] = int(character.get("hp", merged["resources"]["hp"]["current"]) or 0)
    if "stamina" in character:
        merged["resources"]["stamina"]["current"] = int(character.get("stamina", merged["resources"]["stamina"]["current"]) or 0)

    merged["attributes"].update(character.get("attributes", {}) or {})
    raw_skills = character.get("skills", {}) or {}
    if looks_like_legacy_seeded_skills(raw_skills):
        raw_skills = {skill_name: default_skill_state(skill_name) for skill_name in SKILL_KEYS}
    normalized_skills = {}
    for skill_name in SKILL_KEYS:
        normalized_skills[skill_name] = normalize_skill_state(skill_name, raw_skills.get(skill_name, default_skill_state(skill_name)))
    merged["skills"] = normalized_skills
    merged["equipment"].update(character.get("equipment", {}) or {})
    merged["progression"].update(character.get("progression", {}) or {})
    merged["journal"].update(character.get("journal", {}) or {})

    inventory = character.get("inventory", {})
    if isinstance(inventory, list):
        merged["inventory"]["items"] = [{"item_id": str(item_id), "stack": 1} for item_id in inventory if item_id]
    elif isinstance(inventory, dict):
        merged["inventory"].update(inventory)
    if character.get("equip"):
        merged["equipment"]["weapon"] = character["equip"].get("weapon", merged["equipment"]["weapon"])
        merged["equipment"]["chest"] = character["equip"].get("armor", merged["equipment"]["chest"])

    if character.get("potential"):
        merged["progression"]["potential_cards"] = [
            {"id": make_id("potential"), "name": str(name), "description": "", "tags": [], "requirements": [], "status": "locked"}
            for name in character.get("potential", []) if str(name).strip()
        ]

    ensure_progression_shape(merged)
    apply_role_starter_skills(merged, (merged.get("bio") or {}).get("party_role", ""))
    refresh_skill_progression(merged)
    migrate_effects_from_conditions(merged)
    rebuild_character_derived(merged, items_db)
    return merged


def rebuild_all_character_derived(campaign: Dict[str, Any]) -> None:
    items_db = campaign.get("state", {}).get("items", {}) or {}
    world_time = normalize_world_time(campaign.get("state", {}).get("meta", {}))
    for slot_name, character in (campaign.get("state", {}).get("characters") or {}).items():
        campaign["state"]["characters"][slot_name] = normalize_character_state(character, slot_name, items_db)
        rebuild_character_derived(campaign["state"]["characters"][slot_name], items_db, world_time)


def derive_scene_name(campaign: Dict[str, Any], slot_name: str) -> str:
    scene_id = (campaign.get("state", {}).get("characters", {}).get(slot_name) or {}).get("scene_id", "")
    if not scene_id:
        return "Kein Ort"
    scenes = campaign.get("state", {}).get("scenes", {}) or {}
    if scene_id in scenes and scenes[scene_id].get("name"):
        return scenes[scene_id]["name"]
    nodes = (campaign.get("state", {}).get("map", {}).get("nodes") or {})
    if scene_id in nodes and nodes[scene_id].get("name"):
        return nodes[scene_id]["name"]
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
    }


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


def parse_earth_items(value: str) -> List[str]:
    items = []
    for chunk in parse_lines(value):
        for part in chunk.split(","):
            text = part.strip()
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
    "party_role": {
        "scout": "Scout (Späher/Info)",
        "tank": "Front (Tank/Schutz)",
        "support": "Support (Buff/Heal)",
        "striker": "Striker (Burst/Druck)",
        "controller": "Controller (Debuff/Zone)",
        "face": "Face (Rede/Führung)",
    },
}


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
    }


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


def public_player(player_id: str, player: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "player_id": player_id,
        "display_name": player.get("display_name", ""),
        "joined_at": player.get("joined_at"),
        "last_seen_at": player.get("last_seen_at"),
    }


def available_slots(campaign: Dict[str, Any]) -> List[Dict[str, Any]]:
    players = campaign.get("players", {})
    out = []
    for slot_name in campaign_slots(campaign):
        owner = campaign.get("claims", {}).get(slot_name)
        owner_name = players.get(owner, {}).get("display_name") if owner else None
        setup_node = campaign.get("setup", {}).get("characters", {}).get(slot_name, {})
        out.append(
            {
                "slot_id": slot_name,
                "claimed_by": owner,
                "claimed_by_name": owner_name,
                "completed": bool(setup_node.get("completed")),
                "display_name": display_name_for_slot(campaign, slot_name),
                "summary": setup_node.get("summary", {}),
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
    for slot_name in campaign_slots(campaign):
        character = (campaign.get("state", {}).get("characters", {}) or {}).get(slot_name) or blank_character_state(slot_name)
        resources = character.get("resources", {})
        derived = character.get("derived", {})
        overview.append(
            {
                "slot_id": slot_name,
                "display_name": display_name_for_slot(campaign, slot_name),
                "claimed_by": campaign.get("claims", {}).get(slot_name),
                "claimed_by_name": campaign.get("players", {}).get(campaign.get("claims", {}).get(slot_name), {}).get("display_name"),
                "scene_id": character.get("scene_id", ""),
                "scene_name": derive_scene_name(campaign, slot_name),
                "hp": f"{((resources.get('hp') or {}).get('current', 0))}/{((resources.get('hp') or {}).get('max', 0))}",
                "stamina": f"{((resources.get('stamina') or {}).get('current', 0))}/{((resources.get('stamina') or {}).get('max', 0))}",
                "aether": f"{((resources.get('aether') or {}).get('current', 0))}/{((resources.get('aether') or {}).get('max', 0))}",
                "stress": f"{((resources.get('stress') or {}).get('current', 0))}/{((resources.get('stress') or {}).get('max', 0))}",
                "corruption": f"{((resources.get('corruption') or {}).get('current', 0))}/{((resources.get('corruption') or {}).get('max', 0))}",
                "wounds": f"{((resources.get('wounds') or {}).get('current', 0))}/{((resources.get('wounds') or {}).get('max', 0))}",
                "carry": f"{derived.get('carry_weight', 0)}/{derived.get('carry_limit', 0)}",
                "conditions": compact_conditions(character),
                "in_combat": bool((derived.get("combat_flags") or {}).get("in_combat", False)),
                "party_role": (character.get("bio") or {}).get("party_role", ""),
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
    bio = character.get("bio", {})
    resources = character.get("resources", {})
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
    skill_views = []
    for skill_name in SKILL_KEYS:
        skill_state = normalize_skill_state(skill_name, skills.get(skill_name))
        if (
            int(skill_state.get("level", 0) or 0) <= 0
            and not skill_state.get("path")
            and not skill_state.get("awakened")
            and not skill_state.get("evolutions")
            and not skill_state.get("fusion_candidates")
        ):
            continue
        skill_views.append(
            {
                "id": skill_name,
                "name": skill_display_name(skill_name),
                "level": skill_state.get("level", 1),
                "xp": skill_state.get("xp", 0),
                "next_xp": skill_state.get("next_xp", 100),
                "rank": skill_state.get("rank", "F"),
                "mastery": skill_state.get("mastery", 0),
                "path": skill_state.get("path", ""),
                "path_choice_available": skill_state.get("path_choice_available", False),
                "path_options": skill_state.get("path_options", []),
                "evolutions": skill_state.get("evolutions", []),
                "fusion_candidates": skill_state.get("fusion_candidates", []),
                "awakened": skill_state.get("awakened", False),
                "unlocks": skill_state.get("unlocks", []),
                "attribute": SKILL_ATTRIBUTE_MAP.get(skill_name, "int"),
                "effective_bonus": skill_effective_bonus(character, skill_name, items_db),
                "modifier_bonus": calculate_skill_modifier_bonus(character, items_db, skill_name),
            }
        )
    modifier_summary = {
        "defense": calculate_derived_bonus(character, items_db, "defense"),
        "initiative": calculate_derived_bonus(character, items_db, "initiative"),
        "attack_rating_mainhand": calculate_derived_bonus(character, items_db, "attack_rating_mainhand"),
        "attack_rating_offhand": calculate_derived_bonus(character, items_db, "attack_rating_offhand"),
    }
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
                "location": {"scene_id": character.get("scene_id", ""), "scene_name": derive_scene_name(campaign, slot_name)},
                "claim_status": "geclaimt" if campaign.get("claims", {}).get(slot_name) else "frei",
                "appearance": character.get("appearance", {}),
                "ageing": character.get("aging", {}),
            },
            "stats": {
                "attributes": character.get("attributes", {}),
                "derived": derived,
                "resistances": derived.get("resistances", {}),
                "age_modifiers": derived.get("age_modifiers", {}),
                "modifier_summary": modifier_summary,
            },
            "skills": skill_views,
            "abilities": character.get("abilities", []),
            "gear_inventory": {
                "equipment": equipment_view,
                "quick_slots": character.get("inventory", {}).get("quick_slots", {}),
                "inventory_items": item_views,
                "carry_weight": derived.get("carry_weight", 0),
                "carry_limit": derived.get("carry_limit", 0),
                "encumbrance_state": derived.get("encumbrance_state", "normal"),
            },
            "effects": character.get("effects", []),
            "journal": {
                **(character.get("journal", {}) or {}),
                "appearance_history": character.get("appearance_history", []),
            },
            "progression": character.get("progression", {}),
            "meta": {
                "class_state": character.get("class_state", {}),
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


def current_question_id(setup_node: Dict[str, Any]) -> Optional[str]:
    answers = setup_node.get("answers", {})
    for qid in setup_node.get("question_queue", []):
        if qid not in answers:
            return qid
    return None


def answered_count(setup_node: Dict[str, Any]) -> int:
    return len(setup_node.get("answers", {}))


def progress_payload(setup_node: Dict[str, Any]) -> Dict[str, int]:
    total = len(setup_node.get("question_queue", []))
    return {
        "answered": answered_count(setup_node),
        "total": total,
        "step": min(answered_count(setup_node) + 1, total) if total else 0,
    }


def call_ollama_text(system: str, user: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": {
            "seed": OLLAMA_SEED,
            "temperature": 0.35,
            "num_ctx": 4096,
        },
    }
    response = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=120)
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


def extract_json_payload(text: str) -> Dict[str, Any]:
    content = str(text or "").strip()
    if not content:
        raise RuntimeError("Model returned empty content.")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError(f"Model returned non-JSON content. First 500 chars:\n{content[:500]}")
    snippet = content[start : end + 1]
    try:
        return json.loads(snippet)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Model returned non-JSON content. First 500 chars:\n{content[:500]}") from exc


def normalize_patch_payload(payload: Any) -> Dict[str, Any]:
    patch = payload if isinstance(payload, dict) else {}
    normalized = blank_patch()

    meta = patch.get("meta")
    if isinstance(meta, dict):
        normalized_meta = {"phase": meta.get("phase", normalized["meta"]["phase"])}
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


def normalize_model_output_payload(payload: Any) -> Dict[str, Any]:
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

    requests_payload = candidate.get("requests")
    if requests_payload is None:
        requests_payload = []
    elif isinstance(requests_payload, dict):
        requests_payload = [requests_payload]
    elif not isinstance(requests_payload, list):
        requests_payload = []
    requests_payload = [entry for entry in requests_payload if isinstance(entry, dict)]

    normalized = {
        "story": str(story or "").strip(),
        "patch": patch,
        "requests": requests_payload,
    }
    return normalized if normalized["story"] else {}


def call_ollama_chat(
    system: str,
    user: str,
    *,
    format_schema: Optional[Dict[str, Any]] = None,
    timeout: int = 180,
    temperature: Optional[float] = None,
) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": {
            "seed": OLLAMA_SEED,
            "temperature": OLLAMA_TEMPERATURE if temperature is None else temperature,
            "num_ctx": OLLAMA_NUM_CTX,
        },
    }
    if format_schema is not None:
        payload["format"] = format_schema
    response = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=timeout)
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
                timeout=timeout,
                temperature=temperature,
            )
        raise RuntimeError(message)
    return (response.json().get("message", {}) or {}).get("content", "").strip()


def call_ollama_json(system: str, user: str) -> Dict[str, Any]:
    content = call_ollama_chat(system, user, format_schema=RESPONSE_SCHEMA, timeout=180, temperature=OLLAMA_TEMPERATURE)
    return extract_json_payload(content)


def call_ollama_schema(system: str, user: str, schema: Dict[str, Any], *, timeout: int = 120, temperature: float = 0.45) -> Dict[str, Any]:
    content = call_ollama_chat(system, user, format_schema=schema, timeout=timeout, temperature=temperature)
    return extract_json_payload(content)


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
        return prompt if is_bad_setup_ai_copy(text) else text
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


def build_question_payload(
    question: Dict[str, Any],
    *,
    ai_copy: str,
    setup_node: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = {
        "question_id": question["id"],
        "label": question["label"],
        "type": question["type"],
        "required": question.get("required", False),
        "options": question.get("options", []),
        "min_selected": question.get("min_selected"),
        "max_selected": question.get("max_selected"),
        "allow_other": question.get("allow_other", False),
        "ai_copy": clean_setup_ai_copy(ai_copy) or question["label"],
        "existing_answer": None,
    }
    if setup_node:
        payload["existing_answer"] = deep_copy(setup_node.get("answers", {}).get(question["id"]))
    return payload


def validate_answer_payload(question: Dict[str, Any], answer: Dict[str, Any]) -> Any:
    qtype = question["type"]
    required = question.get("required", False)
    allow_other = question.get("allow_other", False)
    options = question.get("options", [])

    if qtype in ("text", "textarea"):
        value = str(answer.get("value") or "").strip()
        if required and not value:
            raise HTTPException(status_code=400, detail=f"Antwort für {question['label']} fehlt.")
        return value

    if qtype == "boolean":
        value = answer.get("value")
        if isinstance(value, bool):
            return value
        text = str(value or "").strip().lower()
        if text in ("ja", "true", "1"):
            return True
        if text in ("nein", "false", "0"):
            return False
        raise HTTPException(status_code=400, detail=f"Antwort für {question['label']} muss Ja oder Nein sein.")

    if qtype == "select":
        selected = str(answer.get("value") or answer.get("selected") or "").strip()
        other_text = str(answer.get("other_text") or "").strip()
        if required and not selected and not other_text:
            raise HTTPException(status_code=400, detail=f"Antwort für {question['label']} fehlt.")
        if not required and not selected and not other_text:
            return {"selected": "", "other_text": ""}
        if selected in options:
            return {"selected": selected, "other_text": other_text}
        if allow_other and other_text:
            return {"selected": "Sonstiges", "other_text": other_text}
        raise HTTPException(status_code=400, detail=f"Ungültige Auswahl für {question['label']}.")

    if qtype == "multiselect":
        raw = answer.get("selected")
        if raw is None:
            raw = answer.get("value")
        if raw is None:
            raw_list: List[str] = []
        elif isinstance(raw, list):
            raw_list = [str(entry).strip() for entry in raw if str(entry).strip()]
        else:
            raw_list = [str(raw).strip()] if str(raw).strip() else []
        selected = [entry for entry in raw_list if entry in options]
        other_values = [str(entry).strip() for entry in answer.get("other_values", []) if str(entry).strip()]
        if allow_other and answer.get("other_text"):
            other_values.append(str(answer["other_text"]).strip())
        count = len(selected) + len(other_values)
        if required and count == 0:
            raise HTTPException(status_code=400, detail=f"Antwort für {question['label']} fehlt.")
        if not required and count == 0:
            return {"selected": [], "other_values": []}
        if question.get("min_selected") and count < question["min_selected"]:
            raise HTTPException(status_code=400, detail=f"Bitte wähle mehr Einträge für {question['label']}.")
        if question.get("max_selected") and count > question["max_selected"]:
            raise HTTPException(status_code=400, detail=f"Zu viele Einträge für {question['label']}.")
        return {"selected": selected, "other_values": other_values}

    raise HTTPException(status_code=400, detail=f"Unbekannter Frage-Typ: {qtype}")


def fallback_random_text(question_id: str, *, setup_type: str, campaign: Dict[str, Any], slot_name: Optional[str] = None) -> str:
    world_theme = extract_text_answer((campaign.get("setup", {}).get("world", {}).get("answers", {}) or {}).get("theme"))
    gender = ""
    if slot_name:
        gender = extract_text_answer((((campaign.get("setup", {}) or {}).get("characters", {}) or {}).get(slot_name, {}).get("answers", {}) or {}).get("char_gender"))
    fallbacks = {
        "central_conflict": "Ein sterbendes Grenzland wird von einem alten Schattenkult und hungrigen Bestien zugleich zerfressen.",
        "factions": "Die Schwarze Abtei - will verbotene Reliquien sammeln und herrscht durch Angst.\nDie Roten Zöllner - pressen die letzten Siedlungen mit Gewalt aus.\nDer Aschencirkel - jagt jede fremde Macht und opfert Wissen für Stärke.",
        "taboos": "Keine zusätzlichen Tabus. Konsequenzen sollen hart, aber fair bleiben.",
        "earth_life": "Auf der Erde führte die Figur ein unscheinbares Leben, war aber zäh, aufmerksam und unter Druck belastbar.",
        "first_goal": "Schnell einen sicheren Ort finden und verstehen, welche Macht diese Welt im Hintergrund lenkt.",
        "earth_items": "Taschenlampe, Feuerzeug, kleines Notizbuch",
        "signature_item": "Ein abgenutztes Messer mit Erinnerungsspur",
    }
    if question_id == "char_name":
        male_names = ["Riven", "Kael", "Marek", "Taron", "Levin"]
        female_names = ["Mira", "Elara", "Sera", "Nyra", "Talia"]
        neutral_names = ["Ash", "Rin", "Nox", "Vale", "Kian"]
        if "männ" in gender.lower():
            return random.choice(male_names)
        if "weib" in gender.lower():
            return random.choice(female_names)
        return random.choice(neutral_names)
    if question_id == "central_conflict" and world_theme:
        return f"In einer Welt mit dem Thema {world_theme} kämpfen die letzten freien Enklaven gegen eine Macht, die langsam alles Lebendige verdirbt."
    return fallbacks.get(question_id, "Etwas Düsteres, Eigenes und Folgenschweres.")


def fallback_random_answer_payload(
    campaign: Dict[str, Any],
    question: Dict[str, Any],
    *,
    setup_type: str,
    slot_name: Optional[str] = None,
) -> Dict[str, Any]:
    qtype = question["type"]
    options = question.get("options", [])
    min_selected = int(question.get("min_selected") or 1)
    max_selected = int(question.get("max_selected") or max(min_selected, len(options) or 1))
    if qtype in ("text", "textarea"):
        return {"value": fallback_random_text(question["id"], setup_type=setup_type, campaign=campaign, slot_name=slot_name)}
    if qtype == "boolean":
        return {"value": random.choice([True, False])}
    if qtype == "select":
        if options:
            return {"selected": random.choice(options), "other_text": ""}
        return {"selected": "", "other_text": fallback_random_text(question["id"], setup_type=setup_type, campaign=campaign, slot_name=slot_name)}
    if qtype == "multiselect":
        if not options:
            return {"selected": [], "other_values": []}
        count = random.randint(min_selected, min(max_selected, len(options)))
        return {"selected": random.sample(options, count), "other_values": []}
    return {"value": ""}


def generate_random_setup_answer(
    campaign: Dict[str, Any],
    question: Dict[str, Any],
    *,
    setup_type: str,
    slot_name: Optional[str] = None,
    setup_node: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    summary = campaign.get("setup", {}).get("world", {}).get("summary", {})
    current_answers = (setup_node or {}).get("answers", {})
    user = (
        f"Setup-Typ: {setup_type}\n"
        f"Slot: {slot_name or '-'}\n"
        f"Aktuelle Welt-Zusammenfassung: {json.dumps(summary, ensure_ascii=False)}\n"
        f"Bisherige Antworten dieses Flows: {json.dumps(current_answers, ensure_ascii=False)}\n"
        f"Frage: {json.dumps(question, ensure_ascii=False)}\n"
        "Gib eine passende zufällige Antwort für genau diese eine Frage zurück."
    )
    try:
        raw = call_ollama_schema(SETUP_RANDOM_SYSTEM_PROMPT, user, SETUP_RANDOM_SCHEMA, timeout=120, temperature=0.7)
    except Exception:
        raw = fallback_random_answer_payload(campaign, question, setup_type=setup_type, slot_name=slot_name)
    if not isinstance(raw, dict):
        raw = fallback_random_answer_payload(campaign, question, setup_type=setup_type, slot_name=slot_name)
    normalized = {
        "question_id": question["id"],
        "value": raw.get("value"),
        "selected": raw.get("selected"),
        "other_text": str(raw.get("other_text") or ""),
        "other_values": [str(entry).strip() for entry in (raw.get("other_values") or []) if str(entry).strip()],
    }
    try:
        validate_answer_payload(question, normalized)
        return normalized
    except HTTPException:
        fallback = fallback_random_answer_payload(campaign, question, setup_type=setup_type, slot_name=slot_name)
        normalized_fallback = {
            "question_id": question["id"],
            "value": fallback.get("value"),
            "selected": fallback.get("selected"),
            "other_text": str(fallback.get("other_text") or ""),
            "other_values": [str(entry).strip() for entry in (fallback.get("other_values") or []) if str(entry).strip()],
        }
        validate_answer_payload(question, normalized_fallback)
        return normalized_fallback


def store_setup_answer(
    setup_node: Dict[str, Any],
    question: Dict[str, Any],
    stored: Any,
    *,
    player_id: Optional[str],
    source: str = "manual",
) -> None:
    setup_node["answers"][question["id"]] = stored
    setup_node["raw_transcript"].append(
        {
            "question_id": question["id"],
            "label": question["label"],
            "answer": stored,
            "answered_at": utc_now(),
            "answered_by": player_id,
            "source": source,
        }
    )


def setup_answer_to_input_payload(question: Dict[str, Any], stored: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "question_id": question["id"],
        "value": None,
        "selected": None,
        "other_text": "",
        "other_values": [],
    }
    qtype = question["type"]
    if qtype in ("text", "textarea", "boolean"):
        payload["value"] = stored
        return payload
    if qtype == "select":
        if isinstance(stored, dict):
            payload["selected"] = stored.get("selected")
            payload["other_text"] = str(stored.get("other_text") or "")
        return payload
    if qtype == "multiselect":
        if isinstance(stored, dict):
            payload["selected"] = stored.get("selected", [])
            payload["other_values"] = list(stored.get("other_values", []))
        return payload
    return payload


def setup_answer_preview_text(question: Dict[str, Any], stored: Any) -> str:
    qtype = question["type"]
    if qtype == "boolean":
        return "Ja" if bool(stored) else "Nein"
    if qtype in ("text", "textarea"):
        return str(stored or "").strip() or "Leer"
    if qtype == "select":
        if isinstance(stored, dict):
            selected = str(stored.get("selected") or "").strip()
            other_text = str(stored.get("other_text") or "").strip()
            if selected == "Sonstiges" and other_text:
                return other_text
            return selected or other_text or "Leer"
        return str(stored or "").strip() or "Leer"
    if qtype == "multiselect":
        if isinstance(stored, dict):
            values = list(stored.get("selected", [])) + list(stored.get("other_values", []))
            return ", ".join(value for value in values if value) or "Leer"
        if isinstance(stored, list):
            return ", ".join(str(value) for value in stored if value) or "Leer"
    return str(stored or "").strip() or "Leer"


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
    preview_campaign = deep_copy(campaign)
    preview_setup_node = preview_campaign["setup"]["world"] if setup_type == "world" else preview_campaign["setup"]["characters"][slot_name]
    for entry in preview_answers or []:
        qid = current_question_id(preview_setup_node)
        if not qid:
            break
        if entry.question_id != qid:
            raise HTTPException(status_code=409, detail="Die Vorschau passt nicht mehr zur aktuellen Setup-Reihenfolge.")
        question = question_map.get(qid)
        if not question:
            raise HTTPException(status_code=404, detail="Unbekannte Setup-Frage.")
        stored = validate_answer_payload(question, entry.model_dump())
        store_setup_answer(preview_setup_node, question, stored, player_id=player_id, source="ai_preview_locked")
    previews: List[Dict[str, Any]] = []
    generated_count = 0
    while True:
        qid = current_question_id(preview_setup_node)
        if not qid:
            break
        if question_id and generated_count == 0 and qid != question_id:
            raise HTTPException(status_code=409, detail="Die aktive Setup-Frage hat sich geändert. Bitte neu öffnen.")
        question = question_map.get(qid)
        if not question:
            raise HTTPException(status_code=404, detail="Unbekannte Setup-Frage.")
        raw_answer = generate_random_setup_answer(
            preview_campaign,
            question,
            setup_type=setup_type,
            slot_name=slot_name,
            setup_node=preview_setup_node,
        )
        stored = validate_answer_payload(question, raw_answer)
        store_setup_answer(preview_setup_node, question, stored, player_id=player_id, source="ai_preview")
        previews.append(
            {
                "question_id": qid,
                "label": question["label"],
                "type": question["type"],
                "preview_text": setup_answer_preview_text(question, stored),
                "answer": setup_answer_to_input_payload(question, stored),
            }
        )
        generated_count += 1
        if mode == "single":
            break
    return previews


def apply_random_setup_preview(
    campaign: Dict[str, Any],
    setup_node: Dict[str, Any],
    question_map: Dict[str, Dict[str, Any]],
    preview_answers: List["SetupAnswerIn"],
    *,
    player_id: Optional[str],
) -> int:
    applied_count = 0
    for entry in preview_answers:
        qid = current_question_id(setup_node)
        if not qid:
            break
        if entry.question_id != qid:
            raise HTTPException(status_code=409, detail="Die Setup-Reihenfolge hat sich geändert. Bitte neu würfeln.")
        question = question_map.get(qid)
        if not question:
            raise HTTPException(status_code=404, detail="Unbekannte Setup-Frage.")
        stored = validate_answer_payload(question, entry.model_dump())
        store_setup_answer(setup_node, question, stored, player_id=player_id, source="ai_random")
        applied_count += 1
    return applied_count


def finalize_world_setup(campaign: Dict[str, Any], player_id: Optional[str]) -> None:
    setup_node = campaign["setup"]["world"]
    setup_node["completed"] = True
    setup_node["summary"] = build_world_summary(campaign)
    initialize_dynamic_slots(campaign, setup_node["summary"]["player_count"])
    apply_world_summary_to_boards(campaign, player_id)
    campaign["state"]["world"]["notes"] = setup_node["summary"].get("premise", "")
    campaign["state"]["meta"]["phase"] = "character_setup"


def finalize_character_setup(campaign: Dict[str, Any], slot_name: str) -> Optional[Dict[str, Any]]:
    setup_node = campaign["setup"]["characters"][slot_name]
    setup_node["completed"] = True
    setup_node["summary"] = build_character_summary(campaign, slot_name)
    apply_character_summary_to_state(campaign, slot_name)
    if campaign["state"]["meta"].get("phase") != "adventure":
        campaign["state"]["meta"]["phase"] = "character_setup"
    return maybe_start_adventure(campaign)


def build_world_summary(campaign: Dict[str, Any]) -> Dict[str, Any]:
    answers = campaign["setup"]["world"]["answers"]
    theme = extract_text_answer(answers.get("theme"))
    tone = extract_text_answer(answers.get("tone"))
    difficulty = extract_text_answer(answers.get("difficulty"))
    death_possible = bool(answers.get("death_possible", True))
    death_policy = "Charaktertod möglich" if death_possible else "Kein permanenter Charaktertod"
    world_structure = extract_text_answer(answers.get("world_structure"))
    world_laws = []
    laws_answer = answers.get("world_laws")
    if isinstance(laws_answer, dict):
        world_laws.extend(laws_answer.get("selected", []))
        world_laws.extend(laws_answer.get("other_values", []))
    central_conflict = extract_text_answer(answers.get("central_conflict"))
    factions = parse_factions(extract_text_answer(answers.get("factions")))
    player_count = int(extract_text_answer(answers.get("player_count")) or 1)
    summary = normalize_answer_summary_defaults()
    summary.update(
        {
            "theme": theme,
            "premise": central_conflict or theme,
            "tone": tone,
            "difficulty": difficulty,
            "death_policy": death_policy,
            "death_possible": death_possible,
            "ruleset": extract_text_answer(answers.get("ruleset")),
            "outcome_model": extract_text_answer(answers.get("outcome_model")),
            "world_structure": world_structure,
            "world_laws": world_laws,
            "central_conflict": central_conflict,
            "factions": factions,
            "taboos": extract_text_answer(answers.get("taboos")),
            "player_count": max(1, min(MAX_PLAYERS, player_count)),
            "resource_scarcity": extract_text_answer(answers.get("resource_scarcity")),
            "healing_frequency": extract_text_answer(answers.get("healing_frequency")),
            "monsters_density": extract_text_answer(answers.get("monsters_density")),
        }
    )
    return summary


def build_character_summary(campaign: Dict[str, Any], slot_name: str) -> Dict[str, Any]:
    answers = campaign["setup"]["characters"][slot_name]["answers"]
    tags = []
    tags_answer = answers.get("personality_tags")
    if isinstance(tags_answer, dict):
        tags.extend(tags_answer.get("selected", []))
        tags.extend(tags_answer.get("other_values", []))
    summary = {
        "display_name": extract_text_answer(answers.get("char_name")),
        "gender": extract_text_answer(answers.get("char_gender")),
        "age_bucket": extract_text_answer(answers.get("char_age")),
        "earth_life": extract_text_answer(answers.get("earth_life")),
        "personality_tags": tags,
        "background_tags": parse_lines(extract_text_answer(answers.get("earth_life")))[:3],
        "strength": extract_text_answer(answers.get("strength")),
        "weakness": extract_text_answer(answers.get("weakness")),
        "party_role": extract_text_answer(answers.get("party_role")),
        "current_focus": extract_text_answer(answers.get("current_focus")),
        "first_goal": extract_text_answer(answers.get("first_goal")),
        "isekai_price": extract_text_answer(answers.get("isekai_price")),
        "earth_items": parse_earth_items(extract_text_answer(answers.get("earth_items"))),
        "signature_item": extract_text_answer(answers.get("signature_item")),
    }
    return summary


def apply_world_summary_to_boards(campaign: Dict[str, Any], updated_by: Optional[str]) -> None:
    summary = campaign["setup"]["world"]["summary"]
    campaign["boards"]["plot_essentials"] = {
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
        f"Tod: {summary.get('death_policy', '')}",
        f"Ressourcen: {summary.get('resource_scarcity', '')}",
        f"Heilung: {summary.get('healing_frequency', '')}",
        f"Monsterdichte: {summary.get('monsters_density', '')}",
        f"Regelsystem: {summary.get('ruleset', '')}",
        f"Outcome-Modell: {summary.get('outcome_model', '')}",
        f"Weltstruktur: {summary.get('world_structure', '')}",
        f"Weltgesetze: {', '.join(summary.get('world_laws', []))}",
        f"Zentraler Konflikt: {summary.get('central_conflict', '')}",
        f"Tabus/Notizen: {summary.get('taboos', '')}",
    ]
    campaign["boards"]["authors_note"] = {
        "content": "\n".join(line for line in authors_lines if line.split(": ", 1)[1]),
        "updated_at": utc_now(),
        "updated_by": updated_by,
    }
    campaign["boards"]["world_info"] = [
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
    for faction in summary.get("factions", []):
        campaign["boards"]["world_info"].append(
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
    summary = campaign["setup"]["characters"][slot_name]["summary"]
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
        "party_role": summary.get("party_role", ""),
        "isekai_price": summary.get("isekai_price", ""),
        "earth_items": summary.get("earth_items", []),
        "signature_item": summary.get("signature_item", ""),
    }
    character["aging"] = {
        "arrival_absolute_day": world_time["absolute_day"],
        "days_since_arrival": 0,
        "last_aged_absolute_day": world_time["absolute_day"],
        "age_effects_applied": [],
    }
    apply_role_starter_skills(character, summary.get("party_role", ""))
    refresh_skill_progression(character)
    rebuild_character_derived(character, campaign["state"].get("items", {}), world_time)


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
        if request.get("actor") in mapping:
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
    world_answers = {
        "theme": legacy_select_answer_payload(world_question["theme"], world_setup.get("theme", "")),
        "player_count": {"selected": str(max(1, len([owner for owner in new_claims.values() if owner]) or 1)), "other_text": ""},
        "tone": legacy_select_answer_payload(world_question["tone"], world_setup.get("tone", "")),
        "difficulty": legacy_select_answer_payload(world_question["difficulty"], "Brutal"),
        "death_possible": True,
        "monsters_density": legacy_select_answer_payload(world_question["monsters_density"], "Regelmäßig"),
        "resource_scarcity": legacy_select_answer_payload(world_question["resource_scarcity"], "Mittel"),
        "healing_frequency": legacy_select_answer_payload(world_question["healing_frequency"], "Normal"),
        "ruleset": legacy_select_answer_payload(world_question["ruleset"], "1W20"),
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
    new_setup["world"]["completed"] = state.get("meta", {}).get("phase") in ("character_setup", "adventure")

    old_setup_chars = old_setup.get("characters") or {}
    for legacy_name, new_slot in mapping.items():
        old_answers = ((old_setup_chars.get(legacy_name) or {}).get("answers") or {})
        bio = (new_characters[new_slot].get("bio") or {})
        legacy_gender = bio.get("gender") or extract_text_answer(old_answers.get("char_gender"))
        legacy_age = bio.get("age") or extract_text_answer(old_answers.get("char_age"))
        legacy_strength = bio.get("strength") or extract_text_answer(old_answers.get("strength"))
        legacy_weakness = bio.get("weakness") or extract_text_answer(old_answers.get("weakness"))
        legacy_role = bio.get("party_role") or extract_text_answer(old_answers.get("party_role"))
        legacy_focus = bio.get("focus") or extract_text_answer(old_answers.get("current_focus"))
        legacy_price = bio.get("isekai_price") or extract_text_answer(old_answers.get("isekai_price"))
        legacy_items = bio.get("earth_items") or parse_earth_items(extract_text_answer(old_answers.get("earth_items")))
        node = default_character_setup_node()
        node["answers"] = {
            "char_name": bio.get("name", ""),
            "char_gender": legacy_select_answer_payload(char_question["char_gender"], legacy_gender),
            "char_age": legacy_select_answer_payload(char_question["char_age"], legacy_age),
            "earth_life": bio.get("earth_life", old_answers.get("earth_life", "")),
            "personality_tags": {"selected": bio.get("personality", []), "other_values": []},
            "strength": legacy_select_answer_payload(char_question["strength"], legacy_strength),
            "weakness": legacy_select_answer_payload(char_question["weakness"], legacy_weakness),
            "party_role": legacy_select_answer_payload(char_question["party_role"], legacy_role),
            "current_focus": legacy_select_answer_payload(char_question["current_focus"], legacy_focus),
            "first_goal": bio.get("goal", ""),
            "isekai_price": legacy_select_answer_payload(char_question["isekai_price"], legacy_price),
            "earth_items": ", ".join(legacy_items),
            "signature_item": bio.get("signature_item", ""),
        }
        node["summary"] = build_character_summary({"setup": {"characters": {new_slot: node}}}, new_slot)
        node["completed"] = bool(node["summary"].get("display_name")) or state.get("meta", {}).get("phase") == "adventure"
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
        state["meta"]["phase"] = "character_setup"
    if state["meta"].get("phase") not in PHASES:
        state["meta"]["phase"] = "world_setup"
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
    state["world"]["day"] = state["meta"]["world_time"]["day"]
    state["world"]["time"] = state["meta"]["world_time"]["time_of_day"]
    state["world"]["weather"] = state["meta"]["world_time"]["weather"]
    state.setdefault("map", {"nodes": {}, "edges": []})
    state.setdefault("plotpoints", [])
    state.setdefault("scenes", {})
    state.setdefault("items", {})
    state.setdefault("characters", {})
    state.setdefault("recent_story", [])
    state.setdefault("events", [])

    boards = campaign["boards"]
    boards.setdefault("plot_essentials", default_boards()["plot_essentials"])
    boards.setdefault("authors_note", default_boards()["authors_note"])
    boards.setdefault("story_cards", [])
    boards.setdefault("world_info", [])
    boards.setdefault("memory_summary", default_boards()["memory_summary"])

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

    for slot_name in campaign_slots(campaign):
        state["characters"].setdefault(slot_name, blank_character_state(slot_name))
        state["characters"][slot_name] = normalize_character_state(state["characters"][slot_name], slot_name, state.get("items", {}))
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
        state["meta"]["phase"] = "adventure"
        if state["meta"]["intro_state"].get("status") in ("idle", "pending", "failed"):
            state["meta"]["intro_state"]["status"] = "generated"
        if not state["meta"]["intro_state"].get("generated_turn_id"):
            state["meta"]["intro_state"]["generated_turn_id"] = active_turns(campaign)[0]["turn_id"]

    rebuild_all_character_derived(campaign)

    return campaign


def load_campaign(campaign_id: str) -> Dict[str, Any]:
    path = campaign_path(campaign_id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Kampagne nicht gefunden.")
    return normalize_campaign(load_json(path))


def save_campaign(campaign: Dict[str, Any], *, reason: str = "campaign_updated") -> None:
    campaign = normalize_campaign(campaign)
    campaign["campaign_meta"]["updated_at"] = utc_now()
    campaign_id = campaign["campaign_meta"]["campaign_id"]
    save_json(campaign_path(campaign_id), campaign)
    broadcast_campaign_sync(campaign_id, reason=reason)


def active_turns(campaign: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [turn for turn in campaign.get("turns", []) if turn.get("status") == "active"]


def is_host(campaign: Dict[str, Any], player_id: Optional[str]) -> bool:
    return bool(player_id) and player_id == campaign["campaign_meta"]["host_player_id"]


def build_patch_summary(patch: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "characters_changed": len((patch.get("characters") or {}).keys()),
        "items_added": len(patch.get("items_new") or {}),
        "plot_updates": len(patch.get("plotpoints_add") or []) + len(patch.get("plotpoints_update") or []),
        "map_updates": len(patch.get("map_add_nodes") or []) + len(patch.get("map_add_edges") or []),
        "events_added": len(patch.get("events_add") or []),
    }


def public_turn(turn: Dict[str, Any], campaign: Dict[str, Any], viewer_id: Optional[str]) -> Dict[str, Any]:
    actor = turn["actor"]
    return {
        "turn_id": turn["turn_id"],
        "turn_number": turn["turn_number"],
        "status": turn["status"],
        "actor": actor,
        "actor_display": display_name_for_slot(campaign, actor) if is_slot_id(actor) else actor,
        "player_id": turn.get("player_id"),
        "action_type": turn["action_type"],
        "input_text_display": turn["input_text_display"],
        "gm_text_display": turn["gm_text_display"],
        "requests": turn.get("requests", []),
        "retry_of_turn_id": turn.get("retry_of_turn_id"),
        "created_at": turn["created_at"],
        "updated_at": turn["updated_at"],
        "edited_at": turn.get("edited_at"),
        "edit_count": len(turn.get("edit_history", [])),
        "patch_summary": build_patch_summary(turn.get("patch") or blank_patch()),
        "can_edit": is_host(campaign, viewer_id),
        "can_undo": is_host(campaign, viewer_id) and turn["status"] == "active",
        "can_retry": is_host(campaign, viewer_id) and turn["status"] == "active",
    }


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
        ai_copy=get_persisted_question_ai_copy(setup_node, qid) or base_question["label"],
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
    if campaign["state"]["meta"]["phase"] == "world_setup":
        pending_setup_question = build_world_question_state(campaign, player_id)
    elif claimed_slot and campaign["state"]["meta"]["phase"] == "character_setup":
        pending_setup_question = build_character_question_state(campaign, claimed_slot)
    return {
        "player_id": player_id,
        "display_name": player.get("display_name") if player else None,
        "is_host": is_host(campaign, player_id),
        "claimed_slot_id": claimed_slot,
        "claimed_character": claimed_slot,
        "needs_world_setup": not campaign["setup"]["world"].get("completed", False),
        "needs_character_setup": (
            campaign["state"]["meta"].get("phase") == "character_setup"
            and bool(claimed_slot)
            and not campaign["setup"]["characters"].get(claimed_slot, {}).get("completed", False)
        ),
        "pending_setup_question": pending_setup_question,
    }


def build_setup_runtime(campaign: Dict[str, Any], viewer_id: Optional[str]) -> Dict[str, Any]:
    claimed_slot = player_claim(campaign, viewer_id)
    return {
        "phase": campaign["state"]["meta"]["phase"],
        "world": {
            "completed": campaign["setup"]["world"].get("completed", False),
            "progress": progress_payload(campaign["setup"]["world"]),
            "next_question": build_world_question_state(campaign, viewer_id),
        },
        "claimed_slot_id": claimed_slot,
        "character": build_character_question_state(campaign, claimed_slot) if claimed_slot else None,
    }


def build_campaign_view(campaign: Dict[str, Any], viewer_id: Optional[str]) -> Dict[str, Any]:
    campaign = normalize_campaign(campaign)
    return {
        "campaign_meta": {
            "campaign_id": campaign["campaign_meta"]["campaign_id"],
            "title": campaign["campaign_meta"]["title"],
            "created_at": campaign["campaign_meta"]["created_at"],
            "updated_at": campaign["campaign_meta"]["updated_at"],
            "status": campaign["campaign_meta"]["status"],
            "host_player_id": campaign["campaign_meta"]["host_player_id"],
        },
        "state": campaign["state"],
        "setup": campaign["setup"],
        "setup_runtime": build_setup_runtime(campaign, viewer_id),
        "available_slots": available_slots(campaign),
        "claims": campaign["claims"],
        "active_party": active_party(campaign),
        "display_party": [
            {"slot_id": slot_name, "display_name": display_name_for_slot(campaign, slot_name)}
            for slot_name in active_party(campaign)
        ],
        "world_time": normalize_world_time(campaign["state"]["meta"]),
        "boards": campaign["boards"],
        "active_turns": [public_turn(turn, campaign, viewer_id) for turn in active_turns(campaign)],
        "party_overview": build_party_overview(campaign),
        "character_sheet_slots": campaign_slots(campaign),
        "ui_panels": {
            "sidebar": ["party", "chars", "map", "events"],
            "settings": ["session", "plot", "note", "cards", "world", "memory"],
        },
        "players": [public_player(player_id, player) for player_id, player in campaign.get("players", {}).items()],
        "viewer_context": build_viewer_context(campaign, viewer_id),
        "live": live_snapshot(campaign["campaign_meta"]["campaign_id"]),
    }


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
                "hp": (data.get("resources", {}).get("hp") or {}).get("current", 0),
                "stamina": (data.get("resources", {}).get("stamina") or {}).get("current", 0),
                "aether": (data.get("resources", {}).get("aether") or {}).get("current", 0),
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
        "characters": state["characters"],
        "items": state.get("items", {}),
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


def is_first_person_action(text: str) -> bool:
    return bool(
        re.search(
            r"\b(ich|mich|mir|mein|meine|meinen|meinem|meiner|meins)\b",
            str(text or "").lower(),
        )
    )


def first_sentences(text: str, count: int = 2) -> str:
    parts = re.split(r"(?<=[.!?])\s+", str(text or "").strip())
    return " ".join(part for part in parts[:count] if part)


def text_similarity(left: str, right: str) -> float:
    left_norm = normalized_eval_text(left)
    right_norm = normalized_eval_text(right)
    if not left_norm or not right_norm:
        return 0.0
    return SequenceMatcher(a=left_norm, b=right_norm).ratio()


def salient_action_tokens(text: str) -> List[str]:
    tokens = []
    for token in re.findall(r"[a-zA-ZäöüÄÖÜß]{4,}", str(text or "").lower()):
        if token in ACTION_STOPWORDS:
            continue
        tokens.append(token)
    return tokens[:8]


def has_placeholder_roll_request(requests_payload: List[Dict[str, Any]]) -> bool:
    for request in requests_payload or []:
        if request.get("type") != "roll":
            continue
        check = normalized_eval_text(request.get("check", ""))
        success = normalized_eval_text(request.get("stakes_success", ""))
        failure = normalized_eval_text(request.get("stakes_fail", ""))
        dc = request.get("dc")
        if not check or check in {"kampagne", "story", "allgemein", "general"}:
            return True
        if isinstance(dc, int) and dc <= 0:
            return True
        if "kampagne" in success or "kampagne" in failure:
            return True
    return False


def response_quality_issues(
    campaign: Dict[str, Any],
    actor: str,
    action_type: str,
    content: str,
    out: Dict[str, Any],
    patch: Dict[str, Any],
) -> List[str]:
    issues = []
    story = str(out.get("story", "") or "")
    turns = active_turns(campaign)
    last_gm = turns[-1]["gm_text_display"] if turns else ""
    if last_gm and text_similarity(last_gm, story) >= 0.72:
        issues.append("Die GM-Antwort wiederholt den letzten Beat fast unverändert.")
    recent_gm = [turn.get("gm_text_display", "") for turn in turns[-3:]]
    if any(previous and text_similarity(previous, story) >= 0.82 for previous in recent_gm):
        issues.append("Die GM-Antwort ist zu nah an einer der letzten Antworten.")
    if has_placeholder_roll_request(out.get("requests", [])):
        issues.append("Die Requests enthalten einen Platzhalter-Wurf statt eines echten Checks.")

    patch_summary = build_patch_summary(patch or blank_patch())
    no_progress = (
        patch_summary["characters_changed"] == 0
        and patch_summary["items_added"] == 0
        and patch_summary["plot_updates"] == 0
        and patch_summary["map_updates"] == 0
        and patch_summary["events_added"] == 0
    )
    action_tokens = salient_action_tokens(content)
    story_norm = normalized_eval_text(story)
    if action_type in ("do", "say") and action_tokens and no_progress:
        if not any(token[:4] in story_norm for token in action_tokens):
            issues.append("Die GM-Antwort greift die konkrete Aktion nicht sichtbar auf.")
    if content.strip().lower().startswith("weiter") and last_gm and text_similarity(last_gm, story) >= 0.55:
        issues.append("Der Weiter-Zug führt die Szene nicht wirklich fort.")
    if actor and is_slot_id(actor):
        actor_display = normalized_eval_text(display_name_for_slot(campaign, actor))
        if actor_display and actor_display not in story_norm and no_progress:
            issues.append("Die Antwort verliert den aktiven Charakter aus dem Fokus.")
        if is_first_person_action(content):
            opening_norm = normalized_eval_text(first_sentences(story, 2))
            other_party = [
                normalized_eval_text(display_name_for_slot(campaign, slot_name))
                for slot_name in active_party(campaign)
                if slot_name != actor
            ]
            if actor_display and actor_display not in opening_norm:
                issues.append("Die Antwort löst eine Ich-Aktion nicht klar auf den aktiven Charakter auf.")
            elif any(name and name in opening_norm for name in other_party):
                issues.append("Die Antwort zieht in den ersten Sätzen den falschen Charakter in den Fokus.")
    return issues


def inactive_character_refs(campaign: Dict[str, Any], story: str, patch: Dict[str, Any]) -> List[str]:
    inactive_slots = [slot_name for slot_name in campaign_slots(campaign) if slot_name not in active_party(campaign)]
    refs = []
    patch_chars = patch.get("characters") or {}
    for slot_name in inactive_slots:
        display = display_name_for_slot(campaign, slot_name)
        if slot_name in patch_chars or (display and display != f"Slot {slot_index(slot_name)}" and display in story):
            refs.append(display or slot_name)
    return refs


def validate_patch(state: Dict[str, Any], patch: Dict[str, Any]) -> None:
    for slot_name, upd in (patch.get("characters") or {}).items():
        if slot_name not in state["characters"]:
            raise ValueError(f"Unbekannter Slot im Patch: {slot_name}")
        if "derived" in upd:
            raise ValueError(f"Derived stats duerfen nicht direkt gepatcht werden: {slot_name}")
        for ability in upd.get("abilities_add", []) or []:
            if ability.get("owner") != slot_name:
                raise ValueError(f"Ability owner mismatch: {ability.get('id')} owner={ability.get('owner')} expected={slot_name}")

        for ability_update in upd.get("abilities_update", []) or []:
            existing = {entry["id"]: entry for entry in state["characters"][slot_name]["abilities"]}
            if ability_update["id"] not in existing:
                raise ValueError(f"Ability update refers to unknown ability on {slot_name}: {ability_update['id']}")
        for faction in upd.get("factions_add", []) or []:
            if not faction.get("faction_id"):
                raise ValueError(f"Faction membership without faction_id on {slot_name}")
        class_set = upd.get("class_set") or {}
        if class_set and not class_set.get("class_id"):
            raise ValueError(f"class_set without class_id on {slot_name}")

    items_new = patch.get("items_new") or {}
    known_items = set(state.get("items", {}).keys()) | set(items_new.keys())
    for slot_name, upd in (patch.get("characters") or {}).items():
        for item_id in upd.get("inventory_add", []) or []:
            if item_id not in known_items:
                raise ValueError(f"Unknown item id in inventory_add for {slot_name}: {item_id}")
        eq = upd.get("equip_set") or upd.get("equipment_set") or {"weapon": "", "armor": ""}
        for equip_slot in eq.keys():
            value = eq.get(equip_slot, "")
            if value and value not in known_items:
                raise ValueError(f"Unknown item id in equipment_set.{equip_slot} for {slot_name}: {value}")


def sanitize_patch(state: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    known_items = set((state.get("items") or {}).keys()) | set((patch.get("items_new") or {}).keys())
    sanitized = deep_copy(patch)
    characters = sanitized.get("characters") or {}
    for slot_name in list(characters.keys()):
        if slot_name not in state["characters"]:
            characters.pop(slot_name, None)
            continue
        upd = characters[slot_name]
        upd["inventory_add"] = [item_id for item_id in (upd.get("inventory_add") or []) if item_id in known_items]
        eq = upd.get("equip_set") or upd.get("equipment_set") or {}
        for equip_slot in ("weapon", "armor"):
            if eq.get(equip_slot) and eq[equip_slot] not in known_items:
                eq[equip_slot] = ""
        if eq:
            if "equipment_set" in upd:
                upd["equipment_set"] = eq
            else:
                upd["equip_set"] = eq
        upd.pop("derived", None)
        if upd.get("class_set") and not upd["class_set"].get("class_name"):
            upd["class_set"]["class_name"] = upd["class_set"].get("class_id", "")
    sanitized["characters"] = characters
    return sanitized


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


def apply_patch(state: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    state.setdefault("items", {})
    for item_id, item in (patch.get("items_new") or {}).items():
        state["items"][item_id] = ensure_item_shape(item_id, item)

    state.setdefault("plotpoints", [])
    for pp in (patch.get("plotpoints_add") or []):
        if not any(existing.get("id") == pp.get("id") for existing in state["plotpoints"]):
            state["plotpoints"].append(pp)

    for upd in (patch.get("plotpoints_update") or []):
        pid = upd.get("id")
        for pp in state["plotpoints"]:
            if pp.get("id") == pid:
                if "status" in upd:
                    pp["status"] = upd["status"]
                if "notes" in upd and upd["notes"]:
                    pp["notes"] = upd["notes"]

    state.setdefault("map", {"nodes": {}, "edges": []})
    state["map"].setdefault("nodes", {})
    for node in (patch.get("map_add_nodes") or []):
        node_id = node["id"]
        state["map"]["nodes"][node_id] = {
            "name": node["name"],
            "type": node["type"],
            "danger": node["danger"],
            "discovered": node["discovered"],
        }
        state.setdefault("scenes", {})
        state["scenes"].setdefault(node_id, {"name": node["name"], "danger": node["danger"], "notes": ""})

    for edge in (patch.get("map_add_edges") or []):
        if edge not in state["map"]["edges"]:
            state["map"]["edges"].append(edge)

    time_advance = ((patch.get("meta") or {}).get("time_advance") or {})
    if time_advance:
        apply_world_time_advance(state, int(time_advance.get("days", 0) or 0), time_advance.get("time_of_day"))
        if time_advance.get("reason"):
            state.setdefault("events", [])
            state["events"].append(f"Zeit vergeht: +{int(time_advance.get('days', 0) or 0)} Tage ({time_advance.get('reason')}).")

    effective_world_time = normalize_world_time(state.get("meta", {}))
    for slot_name, upd in (patch.get("characters") or {}).items():
        if slot_name not in state["characters"]:
            continue
        character = state["characters"][slot_name]
        character["scene_id"] = upd.get("scene_id", character["scene_id"])
        if upd.get("bio_set"):
            character["bio"] = {**character.get("bio", {}), **upd["bio_set"]}
        if upd.get("resources_set"):
            for key, value in (upd.get("resources_set") or {}).items():
                if key in RESOURCE_KEYS and isinstance(value, dict):
                    current = character.setdefault("resources", {}).setdefault(key, {"current": 0, "max": 0})
                    current.update({k: int(v) for k, v in value.items() if k in ("current", "max")})
        resource_deltas = resource_delta_payload()
        resource_deltas["hp"] += int(upd.get("hp_delta", 0) or 0)
        resource_deltas["stamina"] += int(upd.get("stamina_delta", 0) or 0)
        for key, value in (upd.get("resources_delta") or {}).items():
            if key in resource_deltas:
                resource_deltas[key] += int(value or 0)
        for resource_key, delta in resource_deltas.items():
            if delta:
                current_resource = character.setdefault("resources", {}).setdefault(resource_key, {"current": 0, "max": 0})
                current_resource["current"] = int(current_resource.get("current", 0) or 0) + delta

        if upd.get("attributes_set"):
            character.setdefault("attributes", {}).update({key: int(value or 0) for key, value in upd["attributes_set"].items() if key in ATTRIBUTE_KEYS})
        for key, value in (upd.get("attributes_delta") or {}).items():
            if key in ATTRIBUTE_KEYS:
                character.setdefault("attributes", {})[key] = int(character["attributes"].get(key, 0) or 0) + int(value or 0)

        if upd.get("skills_set"):
            for key, value in (upd.get("skills_set") or {}).items():
                if key not in SKILL_KEYS:
                    continue
                skill = normalize_skill_state(key, character.setdefault("skills", {}).get(key, default_skill_state(key)))
                if isinstance(value, dict):
                    skill.update(value)
                else:
                    skill["level"] = clamp(int(value or 1), 1, 20)
                    skill["xp"] = 0
                    skill["next_xp"] = next_skill_xp_for_level(skill["level"])
                character["skills"][key] = normalize_skill_state(key, skill)
        for key, value in (upd.get("skills_delta") or {}).items():
            if key in SKILL_KEYS:
                current_skill = normalize_skill_state(key, character.setdefault("skills", {}).get(key, default_skill_state(key)))
                current_skill["level"] = clamp(int(current_skill.get("level", 1) or 1) + int(value or 0), 1, 20)
                current_skill["xp"] = 0
                current_skill["next_xp"] = next_skill_xp_for_level(current_skill["level"])
                character["skills"][key] = normalize_skill_state(key, current_skill)

        for condition in upd.get("conditions_add", []) or []:
            if condition and condition not in character["conditions"]:
                character["conditions"].append(condition)
        for condition in upd.get("conditions_remove", []) or []:
            if condition in character["conditions"]:
                character["conditions"].remove(condition)

        for effect in upd.get("effects_add", []) or []:
            if effect.get("id") and not any(existing.get("id") == effect.get("id") for existing in character.get("effects", [])):
                character.setdefault("effects", []).append(effect)
        remove_effect_ids = set(upd.get("effects_remove", []) or [])
        if remove_effect_ids:
            character["effects"] = [effect for effect in character.get("effects", []) if effect.get("id") not in remove_effect_ids]

        for item_id in upd.get("inventory_add", []) or []:
            if item_id and not any(entry.get("item_id") == item_id for entry in character.get("inventory", {}).get("items", [])):
                character.setdefault("inventory", {}).setdefault("items", []).append({"item_id": item_id, "stack": 1})
        for item_id in upd.get("inventory_remove", []) or []:
            character.setdefault("inventory", {}).setdefault("items", [])
            character["inventory"]["items"] = [entry for entry in character["inventory"]["items"] if entry.get("item_id") != item_id]

        inventory_set = upd.get("inventory_set") or {}
        if inventory_set.get("items") is not None:
            character.setdefault("inventory", {})["items"] = inventory_set.get("items", [])
        if inventory_set.get("quick_slots") is not None:
            character.setdefault("inventory", {})["quick_slots"] = inventory_set.get("quick_slots", {})

        equipment_set = upd.get("equipment_set") or upd.get("equip_set")
        if equipment_set:
            normalized_equipment = character.get("equipment", {})
            for key, value in equipment_set.items():
                target_key = "chest" if key == "armor" else key
                normalized_equipment[target_key] = value
            character["equipment"] = normalized_equipment

        for ability in upd.get("abilities_add", []) or []:
            if not any(existing["id"] == ability["id"] for existing in character["abilities"]):
                character["abilities"].append(ability)

        abilities_by_id = {ability["id"]: ability for ability in character["abilities"]}
        for ability_update in upd.get("abilities_update", []) or []:
            ability_id = ability_update["id"]
            if ability_id in abilities_by_id:
                if "charges" in ability_update:
                    abilities_by_id[ability_id]["charges"] = ability_update["charges"]
                if "cooldown_turns" in ability_update:
                    abilities_by_id[ability_id]["cooldown_turns"] = ability_update["cooldown_turns"]

        for potential in upd.get("potential_add", []) or []:
            if isinstance(potential, dict):
                existing_ids = {entry.get("id") for entry in character.get("progression", {}).get("potential_cards", [])}
                if potential.get("id") and potential.get("id") not in existing_ids:
                    character.setdefault("progression", {}).setdefault("potential_cards", []).append(potential)
            elif potential:
                card = {"id": make_id("potential"), "name": str(potential), "description": "", "tags": [], "requirements": [], "status": "locked"}
                character.setdefault("progression", {}).setdefault("potential_cards", []).append(card)

        if upd.get("progression_set"):
            character.setdefault("progression", {}).update(upd["progression_set"])
        if upd.get("journal_add"):
            journal = character.setdefault("journal", {})
            for key, value in upd["journal_add"].items():
                journal.setdefault(key, [])
                if isinstance(value, list):
                    journal[key].extend(value)

        if upd.get("class_set"):
            class_state = character.setdefault("class_state", {})
            class_state.update(deep_copy(upd["class_set"]))
            class_state.setdefault("visual_modifiers", [])
        for faction in upd.get("factions_add", []) or []:
            faction_id = faction.get("faction_id", "")
            if not faction_id:
                continue
            memberships = character.setdefault("faction_memberships", [])
            existing = next((entry for entry in memberships if entry.get("faction_id") == faction_id), None)
            if existing:
                existing.update(deep_copy(faction))
            else:
                memberships.append(deep_copy(faction))
        for faction_update in upd.get("factions_update", []) or []:
            faction_id = faction_update.get("faction_id", "")
            for membership in character.setdefault("faction_memberships", []):
                if membership.get("faction_id") == faction_id:
                    membership.update(deep_copy(faction_update))
                    break
        for scar in upd.get("scars_add", []) or []:
            if not isinstance(scar, dict):
                continue
            scar_entry = {
                "id": scar.get("id") or make_id("scar"),
                "label": scar.get("label", ""),
                "source": scar.get("source", "story"),
                "turn_number": int(scar.get("turn_number", state.get("meta", {}).get("turn", 0)) or 0),
                "visible": bool(scar.get("visible", True)),
            }
            if scar_entry["label"] and not any(entry.get("label") == scar_entry["label"] for entry in character.setdefault("appearance", {}).setdefault("scars", [])):
                character["appearance"]["scars"].append(scar_entry)
        for flag in upd.get("appearance_flags_add", []) or []:
            if not flag:
                continue
            character.setdefault("appearance", {}).setdefault("visual_modifiers", []).append(
                {
                    "source_type": "story",
                    "source_id": "story_flag",
                    "kind": "skin_mark",
                    "value": str(flag),
                    "active": True,
                }
            )

        ensure_progression_shape(character)
        refresh_skill_progression(character)
        rebuild_character_derived(character, state.get("items", {}), effective_world_time)

    meta = patch.get("meta")
    if meta and "phase" in meta:
        state["meta"]["phase"] = meta["phase"]

    state.setdefault("events", [])
    for entry in (patch.get("events_add") or []):
        if entry:
            state["events"].append(entry)
    return state


def create_turn_record(
    *,
    campaign: Dict[str, Any],
    actor: str,
    player_id: Optional[str],
    action_type: str,
    content: str,
    retry_of_turn_id: Optional[str] = None,
) -> Dict[str, Any]:
    state_before = deep_copy(campaign["state"])
    working_state = deep_copy(campaign["state"])
    working_state["meta"]["turn"] += 1

    context = build_context_packet(campaign, working_state, actor, action_type)
    actor_display = display_name_for_slot(campaign, actor) if is_slot_id(actor) else actor
    actor_resolution_hint = [
        f"Aktiver Actor-Slot: {actor}.",
        f"Aktive Figur dieses Turns: {actor_display}.",
        f"Diese {action_type}-Aktion gehört ausschließlich zu {actor_display}.",
    ]
    if is_first_person_action(content):
        actor_resolution_hint.append(
            f"Erste-Person-Pronomen im Spieltext wie 'ich', 'mich', 'mir' oder 'mein' meinen in diesem Turn immer {actor_display} und niemals eine andere Figur."
        )
    action_packet = {
        "actor": actor,
        "actor_display": actor_display,
        "action_type": action_type,
        "action_type_note": TURN_MODE_GUIDE[action_type],
        "content": content,
        "actor_resolution_hint": " ".join(actor_resolution_hint),
    }
    user_prompt = (
        "CONTEXT_PACKET(JSON):\n"
        + context
        + "\n\nOUTPUT-KONTRAKT:\n"
        + TURN_RESPONSE_JSON_CONTRACT
        + "\n\nPLAYER_ACTION(JSON):\n"
        + json.dumps(action_packet, ensure_ascii=False)
        + "\n\nACTOR_AUFLÖSUNG:\n"
        + "\n".join(f"- {line}" for line in actor_resolution_hint)
        + "\n\nAntworte ausschließlich im JSON-Format gemäß OUTPUT-KONTRAKT."
    )
    system_prompt = (
        SYSTEM_PROMPT
        + "\n\nACTION_TYPE-HINWEIS:\n"
        + "\n".join(f"- {mode}: {description}" for mode, description in TURN_MODE_GUIDE.items())
        + "\nAuthor's Note ist immer bindender Zusatzkontext und liegt im Context Packet unter boards.authors_note.content."
        + "\nDu musst immer direkt auf die letzte Spieleraktion reagieren."
        + "\nGreife in den ersten 1-2 Sätzen die konkrete Aktion oder Aussage des Actors sichtbar auf."
        + "\nWenn der Spieltext in der ersten Person formuliert ist, löse 'ich/mich/mir/mein' immer auf den aktuellen Actor-Slot auf."
        + "\nBei 'Weiter' setzt du exakt am letzten erzählten Beat an und springst nicht zu einer früheren Standardidee zurück."
        + "\nWiederhole niemals frühere GM-Sätze oder fast identische Paraphrasen."
        + "\nRoll-Requests dürfen keine Platzhalter sein: nie 'Kampagne', nie DC 0, nie generische Stakes."
    )
    prompt_payload = {
        "system": system_prompt,
        "user": user_prompt,
        "context": json.loads(context),
    }

    out = None
    prompt_attempt_user = user_prompt
    for attempt in range(1, MAX_TURN_MODEL_ATTEMPTS + 1):
        out = normalize_model_output_payload(call_ollama_json(system_prompt, prompt_attempt_user))
        if not isinstance(out, dict) or "story" not in out or "patch" not in out or "requests" not in out:
            raise HTTPException(status_code=500, detail="Model output missing required fields")
        inactive_refs = inactive_character_refs(campaign, out.get("story", ""), out.get("patch") or {})
        if inactive_refs:
            if attempt == MAX_TURN_MODEL_ATTEMPTS:
                raise HTTPException(
                    status_code=500,
                    detail=f"Modell hat wiederholt ungültige Figuren eingeführt: {', '.join(inactive_refs)}.",
                )
            prompt_attempt_user = (
                user_prompt
                + "\n\nDEINE LETZTE ANTWORT HAT INAKTIVE ODER UNFERTIGE FIGUREN EINGEFÜHRT ("
                + ", ".join(inactive_refs)
                + "). Nutze ausschließlich die Figuren aus active_party."
            )
            continue
        quality_issues = response_quality_issues(campaign, actor, action_type, content, out, out.get("patch") or {})
        if quality_issues:
            if attempt == MAX_TURN_MODEL_ATTEMPTS:
                raise HTTPException(status_code=500, detail="Modellantwort war inhaltlich zu schwach oder repetitiv. Bitte Retry verwenden.")
            prompt_attempt_user = (
                user_prompt
                + "\n\nDEINE LETZTE ANTWORT WAR QUALITATIV NICHT AKZEPTABEL:\n- "
                + "\n- ".join(quality_issues)
                + "\nSchreibe die Szene neu. Reagiere direkt auf die letzte Aktion, entwickle die Lage sichtbar weiter und liefere nur konkrete, nicht-generische Requests."
            )
            continue
        if not is_suspicious_story_text(out.get("story", "")):
            break
        if attempt == MAX_TURN_MODEL_ATTEMPTS:
            raise HTTPException(status_code=500, detail="Modellantwort wirkt abgeschnitten. Bitte Retry verwenden.")
        prompt_attempt_user = (
            user_prompt
            + "\n\nDEINE LETZTE ANTWORT WAR OFFENSICHTLICH ABGESCHNITTEN. "
            + "Schreibe dieselbe Szene erneut, aber diesmal als vollstaendige, abgeschlossene Prosa ohne abgebrochene Zeichen, ohne endenden Backslash und ohne offenen Satz."
        )

    patch = sanitize_patch(working_state, out["patch"])
    validate_patch(working_state, patch)
    state_after = apply_patch(working_state, patch)
    append_character_change_events(state_before, state_after, turn_number=int(state_after.get("meta", {}).get("turn", 0) or 0))
    skill_messages = apply_skill_events(campaign, state_after, patch.get("events_add") or [])
    if skill_messages:
        state_after.setdefault("events", [])
        state_after["events"].extend(skill_messages)
    skill_requests = build_skill_system_requests(campaign, state_before, state_after)
    now = utc_now()
    combined_requests = list(out.get("requests", [])) + skill_requests
    turn_record = {
        "turn_id": make_id("turn"),
        "turn_number": len(campaign.get("turns", [])) + 1,
        "status": "active",
        "actor": actor,
        "player_id": player_id,
        "action_type": action_type,
        "input_text_raw": content,
        "input_text_display": content,
        "gm_text_raw": out["story"],
        "gm_text_display": out["story"],
        "requests": combined_requests,
        "patch": patch,
        "state_before": state_before,
        "state_after": deep_copy(state_after),
        "retry_of_turn_id": retry_of_turn_id,
        "edited_at": None,
        "created_at": now,
        "updated_at": now,
        "edit_history": [],
        "prompt_payload": prompt_payload,
    }
    campaign["state"] = state_after
    campaign.setdefault("turns", []).append(turn_record)
    remember_recent_story(campaign)
    rebuild_memory_summary(campaign)
    return turn_record


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
    campaign = normalize_campaign(campaign)
    required_players = int(campaign["setup"]["world"].get("summary", {}).get("player_count") or 1)
    completed_slots = active_party(campaign)
    if not campaign["setup"]["world"].get("completed"):
        return False
    if len(completed_slots) < required_players:
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
    if not can_start_adventure(campaign):
        return None
    campaign["state"]["meta"]["phase"] = "adventure"
    return try_generate_adventure_intro(campaign)


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
            "title": title.strip() or "Neue Isekai-Kampagne",
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
        campaign = load_campaign(campaign_id)
        if campaign["campaign_meta"]["join_code_hash"] == join_hash:
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


def find_turn(campaign: Dict[str, Any], turn_id: str) -> Dict[str, Any]:
    for turn in campaign.get("turns", []):
        if turn["turn_id"] == turn_id:
            return turn
    raise HTTPException(status_code=404, detail="Turn nicht gefunden.")


def reset_turn_branch(campaign: Dict[str, Any], turn: Dict[str, Any], new_status: str) -> None:
    if turn["status"] != "active":
        raise HTTPException(status_code=409, detail="Nur aktive Turns können rückgängig gemacht oder neu gerollt werden.")
    campaign["state"] = deep_copy(turn["state_before"])
    for current_turn in campaign.get("turns", []):
        if current_turn["status"] == "active" and current_turn["turn_number"] >= turn["turn_number"]:
            current_turn["status"] = new_status
            current_turn["updated_at"] = utc_now()
    remember_recent_story(campaign)
    rebuild_memory_summary(campaign)


class CampaignCreateIn(BaseModel):
    title: str = "Neue Isekai-Kampagne"
    display_name: str


class JoinCampaignIn(BaseModel):
    join_code: str
    display_name: str


class SlotClaimIn(BaseModel):
    slot_id: str


class SetupAnswerIn(BaseModel):
    question_id: str
    value: Optional[Any] = None
    selected: Optional[Any] = None
    other_text: str = ""
    other_values: List[str] = Field(default_factory=list)


class SetupRandomIn(BaseModel):
    question_id: Optional[str] = None
    mode: Literal["single", "all"] = "single"
    preview_answers: List["SetupAnswerIn"] = Field(default_factory=list)


class SetupRandomApplyIn(BaseModel):
    question_id: Optional[str] = None
    mode: Literal["single", "all"] = "single"
    preview_answers: List[SetupAnswerIn] = Field(default_factory=list)


class TurnCreateIn(BaseModel):
    actor: str
    action_type: Literal["do", "say", "story"]
    content: str


class TurnEditIn(BaseModel):
    input_text_display: str
    gm_text_display: str


class PresenceActivityIn(BaseModel):
    kind: Literal["typing_turn", "editing_turn", "claiming_slot", "building_character", "building_world", "reviewing_choices"]
    slot_id: Optional[str] = None
    target_turn_id: Optional[str] = None


class PlotEssentialsPatchIn(BaseModel):
    premise: Optional[str] = None
    current_goal: Optional[str] = None
    current_threat: Optional[str] = None
    active_scene: Optional[str] = None
    open_loops: Optional[List[str]] = None
    tone: Optional[str] = None


class AuthorsNotePatchIn(BaseModel):
    content: str


class StoryCardCreateIn(BaseModel):
    title: str
    kind: Literal["npc", "location", "faction", "item", "hook", "rule"]
    content: str
    tags: List[str] = Field(default_factory=list)


class StoryCardPatchIn(BaseModel):
    title: Optional[str] = None
    kind: Optional[Literal["npc", "location", "faction", "item", "hook", "rule"]] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    archived: Optional[bool] = None


class WorldInfoCreateIn(BaseModel):
    title: str
    category: str
    content: str
    tags: List[str] = Field(default_factory=list)


class WorldInfoPatchIn(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None


class CampaignMetaPatchIn(BaseModel):
    title: str


class TimeAdvanceIn(BaseModel):
    days: int = 0
    time_of_day: Optional[str] = None
    reason: str = ""


class ClassUnlockIn(BaseModel):
    class_id: str
    class_name: Optional[str] = None
    visual_modifiers: List[Dict[str, Any]] = Field(default_factory=list)


class FactionJoinIn(BaseModel):
    faction_id: str
    name: str
    rank: str = ""
    visual_modifiers: List[Dict[str, Any]] = Field(default_factory=list)


app = FastAPI(title="Isekai GM MVP")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
ensure_campaign_storage()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    with open(os.path.join(BASE_DIR, "static", "index.html"), "r", encoding="utf-8") as f:
        return f.read()


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


@app.post("/api/campaigns")
def create_campaign(inp: CampaignCreateIn) -> Dict[str, Any]:
    ensure_campaign_storage()
    result = create_campaign_record(inp.title, inp.display_name)
    campaign = result["campaign"]
    return {
        "campaign_id": campaign["campaign_meta"]["campaign_id"],
        "join_code": result["join_code"],
        "player_id": result["player_id"],
        "player_token": result["player_token"],
        "campaign": build_campaign_view(campaign, result["player_id"]),
    }


@app.post("/api/campaigns/join")
def join_campaign(inp: JoinCampaignIn) -> Dict[str, Any]:
    ensure_campaign_storage()
    campaign = find_campaign_by_join_code(inp.join_code)
    if not campaign:
        raise HTTPException(status_code=404, detail="Join-Code nicht gefunden.")
    identity = new_player(inp.display_name)
    now = utc_now()
    campaign["players"][identity["player_id"]] = {
        "display_name": identity["display_name"],
        "player_token_hash": hash_secret(identity["player_token"]),
        "joined_at": now,
        "last_seen_at": now,
    }
    save_campaign(campaign)
    return {
        "campaign_id": campaign["campaign_meta"]["campaign_id"],
        "join_code": inp.join_code.strip().upper(),
        "player_id": identity["player_id"],
        "player_token": identity["player_token"],
        "campaign_summary": {
            "title": campaign["campaign_meta"]["title"],
            "status": campaign["campaign_meta"]["status"],
        },
        "campaign": build_campaign_view(campaign, identity["player_id"]),
    }


@app.get("/api/campaigns/{campaign_id}")
def get_campaign(
    campaign_id: str,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    return build_campaign_view(campaign, x_player_id)


@app.get("/api/campaigns/{campaign_id}/events")
def stream_campaign_events(
    campaign_id: str,
    player_id: Optional[str] = Query(default=None),
    player_token: Optional[str] = Query(default=None),
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> StreamingResponse:
    campaign = load_campaign(campaign_id)
    auth_player_id = player_id or x_player_id
    auth_player_token = player_token or x_player_token
    authenticate_player(campaign, auth_player_id, auth_player_token, required=True)
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(campaign_event_stream(campaign_id), media_type="text/event-stream", headers=headers)


@app.post("/api/campaigns/{campaign_id}/presence/activity")
def set_presence_activity(
    campaign_id: str,
    inp: PresenceActivityIn,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    activity = set_live_activity(
        campaign,
        x_player_id,
        inp.kind,
        slot_id=inp.slot_id,
        target_turn_id=inp.target_turn_id,
    )
    return {"ok": True, "activity": activity, "live": live_snapshot(campaign_id)}


@app.post("/api/campaigns/{campaign_id}/presence/clear")
def clear_presence_activity(
    campaign_id: str,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    clear_live_activity(campaign_id, x_player_id)
    return {"ok": True, "live": live_snapshot(campaign_id)}


@app.get("/api/campaigns/{campaign_id}/party-overview")
def get_party_overview(
    campaign_id: str,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    return {"party_overview": build_party_overview(campaign)}


@app.get("/api/campaigns/{campaign_id}/characters/{slot_name}")
def get_character_sheet(
    campaign_id: str,
    slot_name: str,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    if slot_name not in campaign.get("state", {}).get("characters", {}):
        raise HTTPException(status_code=404, detail="Charakter nicht gefunden.")
    return build_character_sheet_view(campaign, slot_name)


@app.post("/api/campaigns/{campaign_id}/intro/retry")
def retry_campaign_intro(
    campaign_id: str,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    require_host(campaign, x_player_id)
    intro = intro_state(campaign)
    if active_turns(campaign):
        intro["status"] = "generated"
        if not intro.get("generated_turn_id"):
            intro["generated_turn_id"] = active_turns(campaign)[0]["turn_id"]
        save_campaign(campaign)
        return {
            "turn": None,
            "intro_state": deep_copy(intro),
            "campaign": build_campaign_view(campaign, x_player_id),
        }
    if not can_start_adventure(campaign):
        raise HTTPException(
            status_code=409,
            detail="Der Kampagnenauftakt ist noch nicht bereit. Schließe zuerst Welt-Setup und alle benoetigten Charaktere ab.",
        )
    if intro.get("status") not in ("pending", "failed", "idle"):
        raise HTTPException(status_code=409, detail="Der Kampagnenauftakt wurde bereits erzeugt.")
    clear_live_activity(campaign_id, x_player_id)
    start_blocking_action(campaign, player_id=x_player_id, kind="generate_intro")
    try:
        turn = try_generate_adventure_intro(campaign)
        save_campaign(campaign, reason="intro_retry")
    finally:
        clear_blocking_action(campaign_id)
    return {
        "turn": public_turn(turn, campaign, x_player_id) if turn else None,
        "intro_state": deep_copy(intro_state(campaign)),
        "campaign": build_campaign_view(campaign, x_player_id),
    }


@app.post("/api/campaigns/{campaign_id}/time/advance")
def advance_campaign_time(
    campaign_id: str,
    inp: TimeAdvanceIn,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    require_host(campaign, x_player_id)
    state_before = deep_copy(campaign["state"])
    apply_world_time_advance(campaign["state"], inp.days, inp.time_of_day)
    rebuild_all_character_derived(campaign)
    append_character_change_events(state_before, campaign["state"], turn_number=int(campaign["state"]["meta"].get("turn", 0) or 0))
    if inp.reason.strip():
        campaign["state"].setdefault("events", []).append(f"Zeit vergeht: +{inp.days} Tage ({inp.reason.strip()}).")
    save_campaign(campaign)
    return {"campaign": build_campaign_view(campaign, x_player_id)}


@app.post("/api/campaigns/{campaign_id}/characters/{slot_name}/class/unlock")
def unlock_character_class(
    campaign_id: str,
    slot_name: str,
    inp: ClassUnlockIn,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    require_host(campaign, x_player_id)
    if slot_name not in campaign.get("state", {}).get("characters", {}):
        raise HTTPException(status_code=404, detail="Charakter nicht gefunden.")
    state_before = deep_copy(campaign["state"])
    character = campaign["state"]["characters"][slot_name]
    character["class_state"] = {
        "class_id": inp.class_id,
        "class_name": inp.class_name or inp.class_id,
        "unlocked_at_turn": int(campaign["state"]["meta"].get("turn", 0) or 0),
        "visual_modifiers": deep_copy(inp.visual_modifiers),
    }
    rebuild_character_derived(character, campaign["state"].get("items", {}), normalize_world_time(campaign["state"]["meta"]))
    append_character_change_events(state_before, campaign["state"], turn_number=int(campaign["state"]["meta"].get("turn", 0) or 0))
    save_campaign(campaign)
    return {"campaign": build_campaign_view(campaign, x_player_id)}


@app.post("/api/campaigns/{campaign_id}/characters/{slot_name}/factions/join")
def join_character_faction(
    campaign_id: str,
    slot_name: str,
    inp: FactionJoinIn,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    require_host(campaign, x_player_id)
    if slot_name not in campaign.get("state", {}).get("characters", {}):
        raise HTTPException(status_code=404, detail="Charakter nicht gefunden.")
    state_before = deep_copy(campaign["state"])
    character = campaign["state"]["characters"][slot_name]
    memberships = character.setdefault("faction_memberships", [])
    existing = next((entry for entry in memberships if entry.get("faction_id") == inp.faction_id), None)
    faction_payload = {
        "faction_id": inp.faction_id,
        "name": inp.name,
        "rank": inp.rank,
        "joined_at_turn": int(campaign["state"]["meta"].get("turn", 0) or 0),
        "active": True,
        "visual_modifiers": deep_copy(inp.visual_modifiers),
    }
    if existing:
        existing.update(faction_payload)
    else:
        memberships.append(faction_payload)
    rebuild_character_derived(character, campaign["state"].get("items", {}), normalize_world_time(campaign["state"]["meta"]))
    append_character_change_events(state_before, campaign["state"], turn_number=int(campaign["state"]["meta"].get("turn", 0) or 0))
    save_campaign(campaign)
    return {"campaign": build_campaign_view(campaign, x_player_id)}


@app.patch("/api/campaigns/{campaign_id}/meta")
def patch_campaign_meta(
    campaign_id: str,
    inp: CampaignMetaPatchIn,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    require_host(campaign, x_player_id)
    campaign["campaign_meta"]["title"] = inp.title.strip() or "Unbenannte Session"
    save_campaign(campaign)
    return {"campaign": build_campaign_view(campaign, x_player_id)}


@app.get("/api/campaigns/{campaign_id}/export")
def export_campaign(
    campaign_id: str,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    return campaign


@app.delete("/api/campaigns/{campaign_id}")
def delete_campaign(
    campaign_id: str,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    require_host(campaign, x_player_id)
    path = campaign_path(campaign_id)
    if os.path.exists(path):
        os.remove(path)
    with LIVE_STATE_LOCK:
        LIVE_STATE_REGISTRY.pop(campaign_id, None)
    return {"ok": True, "campaign_id": campaign_id}


@app.post("/api/campaigns/{campaign_id}/setup/world/next")
def next_world_setup_question(
    campaign_id: str,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    require_host(campaign, x_player_id)
    qid = current_question_id(campaign["setup"]["world"])
    if qid:
        clear_live_activity(campaign_id, x_player_id)
        start_blocking_action(campaign, player_id=x_player_id, kind="building_world")
        try:
            ensure_question_ai_copy(campaign, setup_type="world", question_id=qid)
            save_campaign(campaign, reason="world_setup_next")
        finally:
            clear_blocking_action(campaign_id)
    setup_state = build_world_question_state(campaign, x_player_id)
    return {
        "completed": campaign["setup"]["world"].get("completed", False),
        "question": setup_state["question"] if setup_state else None,
        "progress": setup_state["progress"] if setup_state else progress_payload(campaign["setup"]["world"]),
        "campaign": build_campaign_view(campaign, x_player_id),
    }


@app.post("/api/campaigns/{campaign_id}/setup/world/answer")
def answer_world_setup_question(
    campaign_id: str,
    inp: SetupAnswerIn,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    require_host(campaign, x_player_id)
    question = WORLD_QUESTION_MAP.get(inp.question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Unbekannte Weltfrage.")
    setup_node = campaign["setup"]["world"]
    stored = validate_answer_payload(question, inp.model_dump())
    clear_live_activity(campaign_id, x_player_id)
    start_blocking_action(campaign, player_id=x_player_id, kind="building_world")
    try:
        store_setup_answer(setup_node, question, stored, player_id=x_player_id, source="manual")
        next_qid = current_question_id(setup_node)
        if not next_qid:
            finalize_world_setup(campaign, x_player_id)
        else:
            ensure_question_ai_copy(campaign, setup_type="world", question_id=next_qid)
        save_campaign(campaign, reason="world_setup_answer")
    finally:
        clear_blocking_action(campaign_id)
    updated = load_campaign(campaign_id)
    next_state = build_world_question_state(updated, x_player_id)
    return {
        "completed": updated["setup"]["world"].get("completed", False),
        "question": next_state["question"] if next_state else None,
        "progress": next_state["progress"] if next_state else progress_payload(updated["setup"]["world"]),
        "campaign": build_campaign_view(updated, x_player_id),
    }


@app.post("/api/campaigns/{campaign_id}/setup/world/random")
def randomize_world_setup_question(
    campaign_id: str,
    inp: SetupRandomIn,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    require_host(campaign, x_player_id)
    setup_node = campaign["setup"]["world"]
    clear_live_activity(campaign_id, x_player_id)
    start_blocking_action(campaign, player_id=x_player_id, kind="world_randomize")
    try:
        preview_answers = build_random_setup_preview(
            campaign,
            setup_node,
            WORLD_QUESTION_MAP,
            setup_type="world",
            player_id=x_player_id,
            mode=inp.mode,
            question_id=inp.question_id,
            preview_answers=inp.preview_answers,
        )
    finally:
        clear_blocking_action(campaign_id)
    return {
        "mode": inp.mode,
        "question_id": inp.question_id,
        "preview_answers": preview_answers,
        "randomized_count": len(preview_answers),
    }


@app.post("/api/campaigns/{campaign_id}/setup/world/random/apply")
def apply_world_setup_random_preview(
    campaign_id: str,
    inp: SetupRandomApplyIn,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    require_host(campaign, x_player_id)
    setup_node = campaign["setup"]["world"]
    clear_live_activity(campaign_id, x_player_id)
    start_blocking_action(campaign, player_id=x_player_id, kind="world_randomize")
    try:
        applied_count = apply_random_setup_preview(campaign, setup_node, WORLD_QUESTION_MAP, inp.preview_answers, player_id=x_player_id)
        if not current_question_id(setup_node):
            finalize_world_setup(campaign, x_player_id)
        else:
            ensure_question_ai_copy(campaign, setup_type="world", question_id=current_question_id(setup_node))
        save_campaign(campaign, reason="world_setup_random_apply")
    finally:
        clear_blocking_action(campaign_id)
    updated = load_campaign(campaign_id)
    next_state = build_world_question_state(updated, x_player_id)
    return {
        "completed": updated["setup"]["world"].get("completed", False),
        "question": next_state["question"] if next_state else None,
        "progress": next_state["progress"] if next_state else progress_payload(updated["setup"]["world"]),
        "campaign": build_campaign_view(updated, x_player_id),
        "randomized_count": applied_count,
    }


@app.post("/api/campaigns/{campaign_id}/setup/finalize")
def finalize_setup(
    campaign_id: str,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    require_host(campaign, x_player_id)
    if campaign["setup"]["world"]["answers"]:
        campaign["setup"]["world"]["summary"] = build_world_summary(campaign)
        apply_world_summary_to_boards(campaign, x_player_id)
    for slot_name in campaign_slots(campaign):
        if campaign["setup"]["characters"].get(slot_name, {}).get("answers"):
            campaign["setup"]["characters"][slot_name]["summary"] = build_character_summary(campaign, slot_name)
            apply_character_summary_to_state(campaign, slot_name)
    save_campaign(campaign)
    return {"campaign": build_campaign_view(campaign, x_player_id)}


@app.post("/api/campaigns/{campaign_id}/slots/{slot_name}/claim")
def claim_slot(
    campaign_id: str,
    slot_name: str,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    if not campaign["setup"]["world"].get("completed", False):
        raise HTTPException(status_code=409, detail="Slots können erst nach dem Welt-Setup geclaimt werden.")
    if slot_name not in campaign["claims"]:
        raise HTTPException(status_code=404, detail="Slot nicht gefunden.")
    current_owner = campaign["claims"].get(slot_name)
    if current_owner and current_owner != x_player_id:
        raise HTTPException(status_code=409, detail="Dieser Slot ist bereits geclaimt.")
    existing_claim = player_claim(campaign, x_player_id)
    if existing_claim and existing_claim != slot_name:
        raise HTTPException(status_code=409, detail="Du hast bereits einen anderen Slot geclaimt.")
    campaign["claims"][slot_name] = x_player_id
    qid = current_question_id(campaign["setup"]["characters"].get(slot_name, {}))
    if qid:
        ensure_question_ai_copy(campaign, setup_type="character", question_id=qid, slot_name=slot_name)
    save_campaign(campaign)
    return {"campaign": build_campaign_view(campaign, x_player_id)}


@app.post("/api/campaigns/{campaign_id}/slots/{slot_name}/unclaim")
def unclaim_slot(
    campaign_id: str,
    slot_name: str,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    if slot_name not in campaign["claims"]:
        raise HTTPException(status_code=404, detail="Slot nicht gefunden.")
    current_owner = campaign["claims"].get(slot_name)
    if current_owner != x_player_id and not is_host(campaign, x_player_id):
        raise HTTPException(status_code=403, detail="Du darfst diesen Claim nicht lösen.")
    campaign["claims"][slot_name] = None
    save_campaign(campaign)
    return {"campaign": build_campaign_view(campaign, x_player_id)}


@app.post("/api/campaigns/{campaign_id}/slots/{slot_name}/setup/next")
def next_character_setup_question(
    campaign_id: str,
    slot_name: str,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    if slot_name not in campaign["claims"]:
        raise HTTPException(status_code=404, detail="Slot nicht gefunden.")
    if campaign["claims"].get(slot_name) != x_player_id and not is_host(campaign, x_player_id):
        raise HTTPException(status_code=403, detail="Nur der claimgende Spieler oder Host darf dieses Profil bauen.")
    qid = current_question_id(campaign["setup"]["characters"][slot_name])
    if qid:
        clear_live_activity(campaign_id, x_player_id)
        start_blocking_action(campaign, player_id=x_player_id, kind="building_character", slot_id=slot_name)
        try:
            ensure_question_ai_copy(campaign, setup_type="character", question_id=qid, slot_name=slot_name)
            save_campaign(campaign, reason="character_setup_next")
        finally:
            clear_blocking_action(campaign_id)
    state = build_character_question_state(campaign, slot_name)
    setup_node = campaign["setup"]["characters"][slot_name]
    return {
        "completed": setup_node.get("completed", False),
        "question": state["question"] if state else None,
        "progress": state["progress"] if state else progress_payload(setup_node),
        "campaign": build_campaign_view(campaign, x_player_id),
    }


@app.post("/api/campaigns/{campaign_id}/slots/{slot_name}/setup/answer")
def answer_character_setup_question(
    campaign_id: str,
    slot_name: str,
    inp: SetupAnswerIn,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    if slot_name not in campaign["claims"]:
        raise HTTPException(status_code=404, detail="Slot nicht gefunden.")
    claimed_owner = campaign["claims"].get(slot_name)
    if claimed_owner != x_player_id and not is_host(campaign, x_player_id):
        raise HTTPException(status_code=403, detail="Nur der claimgende Spieler oder Host darf dieses Profil bauen.")
    if campaign["state"]["meta"].get("phase") == "world_setup":
        raise HTTPException(status_code=409, detail="Das Welt-Setup muss zuerst abgeschlossen werden.")
    question = CHARACTER_QUESTION_MAP.get(inp.question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Unbekannte Charakterfrage.")
    setup_node = campaign["setup"]["characters"][slot_name]
    stored = validate_answer_payload(question, inp.model_dump())
    clear_live_activity(campaign_id, x_player_id)
    start_blocking_action(campaign, player_id=x_player_id, kind="building_character", slot_id=slot_name)
    try:
        store_setup_answer(setup_node, question, stored, player_id=x_player_id, source="manual")
        next_qid = current_question_id(setup_node)
        new_turn = None
        if not next_qid:
            new_turn = finalize_character_setup(campaign, slot_name)
        else:
            ensure_question_ai_copy(campaign, setup_type="character", question_id=next_qid, slot_name=slot_name)
        save_campaign(campaign, reason="character_setup_answer")
    finally:
        clear_blocking_action(campaign_id)
    updated = load_campaign(campaign_id)
    state = build_character_question_state(updated, slot_name)
    return {
        "completed": updated["setup"]["characters"][slot_name].get("completed", False),
        "question": state["question"] if state else None,
        "progress": state["progress"] if state else progress_payload(updated["setup"]["characters"][slot_name]),
        "started_adventure": bool(new_turn),
        "turn_id": new_turn["turn_id"] if new_turn else None,
        "campaign": build_campaign_view(updated, x_player_id),
    }


@app.post("/api/campaigns/{campaign_id}/slots/{slot_name}/setup/random")
def randomize_character_setup_question(
    campaign_id: str,
    slot_name: str,
    inp: SetupRandomIn,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    if slot_name not in campaign["claims"]:
        raise HTTPException(status_code=404, detail="Slot nicht gefunden.")
    claimed_owner = campaign["claims"].get(slot_name)
    if claimed_owner != x_player_id and not is_host(campaign, x_player_id):
        raise HTTPException(status_code=403, detail="Nur der claimgende Spieler oder Host darf dieses Profil bauen.")
    if campaign["state"]["meta"].get("phase") == "world_setup":
        raise HTTPException(status_code=409, detail="Das Welt-Setup muss zuerst abgeschlossen werden.")
    setup_node = campaign["setup"]["characters"][slot_name]
    clear_live_activity(campaign_id, x_player_id)
    start_blocking_action(campaign, player_id=x_player_id, kind="character_randomize", slot_id=slot_name)
    try:
        preview_answers = build_random_setup_preview(
            campaign,
            setup_node,
            CHARACTER_QUESTION_MAP,
            setup_type="character",
            player_id=x_player_id,
            slot_name=slot_name,
            mode=inp.mode,
            question_id=inp.question_id,
            preview_answers=inp.preview_answers,
        )
    finally:
        clear_blocking_action(campaign_id)
    return {
        "mode": inp.mode,
        "question_id": inp.question_id,
        "preview_answers": preview_answers,
        "randomized_count": len(preview_answers),
    }


@app.post("/api/campaigns/{campaign_id}/slots/{slot_name}/setup/random/apply")
def apply_character_setup_random_preview(
    campaign_id: str,
    slot_name: str,
    inp: SetupRandomApplyIn,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    if slot_name not in campaign["claims"]:
        raise HTTPException(status_code=404, detail="Slot nicht gefunden.")
    claimed_owner = campaign["claims"].get(slot_name)
    if claimed_owner != x_player_id and not is_host(campaign, x_player_id):
        raise HTTPException(status_code=403, detail="Nur der claimgende Spieler oder Host darf dieses Profil bauen.")
    if campaign["state"]["meta"].get("phase") == "world_setup":
        raise HTTPException(status_code=409, detail="Das Welt-Setup muss zuerst abgeschlossen werden.")
    setup_node = campaign["setup"]["characters"][slot_name]
    clear_live_activity(campaign_id, x_player_id)
    start_blocking_action(campaign, player_id=x_player_id, kind="character_randomize", slot_id=slot_name)
    try:
        applied_count = apply_random_setup_preview(campaign, setup_node, CHARACTER_QUESTION_MAP, inp.preview_answers, player_id=x_player_id)
        new_turn = None
        if not current_question_id(setup_node):
            new_turn = finalize_character_setup(campaign, slot_name)
        else:
            ensure_question_ai_copy(
                campaign,
                setup_type="character",
                question_id=current_question_id(setup_node),
                slot_name=slot_name,
            )
        save_campaign(campaign, reason="character_setup_random_apply")
    finally:
        clear_blocking_action(campaign_id)
    updated = load_campaign(campaign_id)
    state = build_character_question_state(updated, slot_name)
    return {
        "completed": updated["setup"]["characters"][slot_name].get("completed", False),
        "question": state["question"] if state else None,
        "progress": state["progress"] if state else progress_payload(updated["setup"]["characters"][slot_name]),
        "started_adventure": bool(new_turn),
        "turn_id": new_turn["turn_id"] if new_turn else None,
        "campaign": build_campaign_view(updated, x_player_id),
        "randomized_count": applied_count,
    }


@app.post("/api/campaigns/{campaign_id}/turns")
def create_turn(
    campaign_id: str,
    inp: TurnCreateIn,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    actor = inp.actor.strip()
    if actor not in campaign["state"]["characters"]:
        raise HTTPException(status_code=400, detail="Unbekannter Slot.")
    content = inp.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Leerer Turn ist nicht erlaubt.")
    if campaign["state"]["meta"].get("phase") != "adventure":
        raise HTTPException(status_code=409, detail="Story-Turns sind erst nach Welt- und Charakter-Setup möglich.")
    if not active_turns(campaign):
        intro = intro_state(campaign)
        if intro.get("status") == "failed":
            raise HTTPException(status_code=409, detail="Der Kampagnenauftakt fehlt noch. Bitte zuerst den Auftakt erneut versuchen.")
        raise HTTPException(status_code=409, detail="Die Geschichte hat noch keinen Auftakt. Bitte warte auf den ersten GM-Text.")
    require_claim(campaign, x_player_id, actor)
    clear_live_activity(campaign_id, x_player_id)
    blocking_kind = "continue_turn" if content.startswith("Weiter.") else "submit_turn"
    start_blocking_action(campaign, player_id=x_player_id, kind=blocking_kind, slot_id=actor)
    try:
        turn = create_turn_record(
            campaign=campaign,
            actor=actor,
            player_id=x_player_id,
            action_type=inp.action_type,
            content=content,
        )
        save_campaign(campaign, reason="turn_created")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        clear_blocking_action(campaign_id)
    return {"turn_id": turn["turn_id"], "campaign": build_campaign_view(campaign, x_player_id)}


@app.patch("/api/campaigns/{campaign_id}/turns/{turn_id}")
def edit_turn(
    campaign_id: str,
    turn_id: str,
    inp: TurnEditIn,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    require_host(campaign, x_player_id)
    turn = find_turn(campaign, turn_id)
    previous = {
        "input_text_display": turn["input_text_display"],
        "gm_text_display": turn["gm_text_display"],
    }
    turn.setdefault("edit_history", []).append(
        {
            "edited_at": utc_now(),
            "edited_by": x_player_id,
            "previous": previous,
        }
    )
    turn["input_text_display"] = inp.input_text_display.strip()
    turn["gm_text_display"] = inp.gm_text_display.strip()
    turn["edited_at"] = utc_now()
    turn["updated_at"] = turn["edited_at"]
    remember_recent_story(campaign)
    rebuild_memory_summary(campaign)
    save_campaign(campaign)
    return {"campaign": build_campaign_view(campaign, x_player_id)}


@app.post("/api/campaigns/{campaign_id}/turns/{turn_id}/undo")
def undo_turn(
    campaign_id: str,
    turn_id: str,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    require_host(campaign, x_player_id)
    turn = find_turn(campaign, turn_id)
    clear_live_activity(campaign_id, x_player_id)
    start_blocking_action(campaign, player_id=x_player_id, kind="undo_turn", slot_id=turn.get("actor"))
    try:
        reset_turn_branch(campaign, turn, "undone")
        save_campaign(campaign, reason="turn_undone")
    finally:
        clear_blocking_action(campaign_id)
    return {"campaign": build_campaign_view(campaign, x_player_id)}


@app.post("/api/campaigns/{campaign_id}/turns/{turn_id}/retry")
def retry_turn(
    campaign_id: str,
    turn_id: str,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    require_host(campaign, x_player_id)
    turn = find_turn(campaign, turn_id)
    clear_live_activity(campaign_id, x_player_id)
    start_blocking_action(campaign, player_id=x_player_id, kind="retry_turn", slot_id=turn.get("actor"))
    try:
        reset_turn_branch(campaign, turn, "superseded")
        new_turn = create_turn_record(
            campaign=campaign,
            actor=turn["actor"],
            player_id=turn.get("player_id"),
            action_type=turn["action_type"],
            content=turn["input_text_raw"],
            retry_of_turn_id=turn["turn_id"],
        )
        new_turn["input_text_display"] = turn.get("input_text_display", new_turn["input_text_display"])
        save_campaign(campaign, reason="turn_retried")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        clear_blocking_action(campaign_id)
    return {"turn_id": new_turn["turn_id"], "campaign": build_campaign_view(campaign, x_player_id)}


@app.patch("/api/campaigns/{campaign_id}/boards/plot-essentials")
def patch_plot_essentials(
    campaign_id: str,
    inp: PlotEssentialsPatchIn,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    require_host(campaign, x_player_id)
    board = campaign["boards"]["plot_essentials"]
    previous = deep_copy(board)
    for key, value in inp.model_dump(exclude_none=True).items():
        board[key] = value
    board["updated_at"] = utc_now()
    board["updated_by"] = x_player_id
    log_board_revision(campaign, board="plot_essentials", op="patch", updated_by=x_player_id, previous=previous, current=deep_copy(board))
    save_campaign(campaign)
    return {"campaign": build_campaign_view(campaign, x_player_id)}


@app.patch("/api/campaigns/{campaign_id}/boards/authors-note")
def patch_authors_note(
    campaign_id: str,
    inp: AuthorsNotePatchIn,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    require_host(campaign, x_player_id)
    board = campaign["boards"]["authors_note"]
    previous = deep_copy(board)
    board["content"] = inp.content
    board["updated_at"] = utc_now()
    board["updated_by"] = x_player_id
    log_board_revision(campaign, board="authors_note", op="patch", updated_by=x_player_id, previous=previous, current=deep_copy(board))
    save_campaign(campaign)
    return {"campaign": build_campaign_view(campaign, x_player_id)}


@app.post("/api/campaigns/{campaign_id}/boards/story-cards")
def create_story_card(
    campaign_id: str,
    inp: StoryCardCreateIn,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    require_host(campaign, x_player_id)
    card = {
        "card_id": make_id("card"),
        "title": inp.title.strip(),
        "kind": inp.kind,
        "content": inp.content.strip(),
        "tags": inp.tags,
        "archived": False,
        "updated_at": utc_now(),
        "updated_by": x_player_id,
    }
    campaign["boards"]["story_cards"].append(card)
    log_board_revision(campaign, board="story_cards", op="create", updated_by=x_player_id, previous=None, current=deep_copy(card), item_id=card["card_id"])
    save_campaign(campaign)
    return {"campaign": build_campaign_view(campaign, x_player_id)}


@app.patch("/api/campaigns/{campaign_id}/boards/story-cards/{card_id}")
def patch_story_card(
    campaign_id: str,
    card_id: str,
    inp: StoryCardPatchIn,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    require_host(campaign, x_player_id)
    for card in campaign["boards"]["story_cards"]:
        if card["card_id"] == card_id:
            previous = deep_copy(card)
            for key, value in inp.model_dump(exclude_none=True).items():
                card[key] = value
            card["updated_at"] = utc_now()
            card["updated_by"] = x_player_id
            log_board_revision(campaign, board="story_cards", op="patch", updated_by=x_player_id, previous=previous, current=deep_copy(card), item_id=card_id)
            save_campaign(campaign)
            return {"campaign": build_campaign_view(campaign, x_player_id)}
    raise HTTPException(status_code=404, detail="Story Card nicht gefunden.")


@app.post("/api/campaigns/{campaign_id}/boards/world-info")
def create_world_info(
    campaign_id: str,
    inp: WorldInfoCreateIn,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    require_host(campaign, x_player_id)
    entry = {
        "entry_id": make_id("world"),
        "title": inp.title.strip(),
        "category": inp.category.strip(),
        "content": inp.content.strip(),
        "tags": inp.tags,
        "updated_at": utc_now(),
        "updated_by": x_player_id,
    }
    campaign["boards"]["world_info"].append(entry)
    log_board_revision(campaign, board="world_info", op="create", updated_by=x_player_id, previous=None, current=deep_copy(entry), item_id=entry["entry_id"])
    save_campaign(campaign)
    return {"campaign": build_campaign_view(campaign, x_player_id)}


@app.patch("/api/campaigns/{campaign_id}/boards/world-info/{entry_id}")
def patch_world_info(
    campaign_id: str,
    entry_id: str,
    inp: WorldInfoPatchIn,
    x_player_id: Optional[str] = Header(default=None),
    x_player_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    campaign = load_campaign(campaign_id)
    authenticate_player(campaign, x_player_id, x_player_token, required=True)
    require_host(campaign, x_player_id)
    for entry in campaign["boards"]["world_info"]:
        if entry["entry_id"] == entry_id:
            previous = deep_copy(entry)
            for key, value in inp.model_dump(exclude_none=True).items():
                entry[key] = value
            entry["updated_at"] = utc_now()
            entry["updated_by"] = x_player_id
            log_board_revision(campaign, board="world_info", op="patch", updated_by=x_player_id, previous=previous, current=deep_copy(entry), item_id=entry_id)
            save_campaign(campaign)
            return {"campaign": build_campaign_view(campaign, x_player_id)}
    raise HTTPException(status_code=404, detail="World-Info-Eintrag nicht gefunden.")
