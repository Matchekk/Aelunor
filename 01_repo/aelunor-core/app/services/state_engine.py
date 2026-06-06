"""Thin public facade for the extracted Aelunor state runtime.

Domain implementations live in service modules. The temporary runtime core keeps
legacy wiring available while factories and tests are moved to explicit ports.
"""
from typing import Any, Dict, Mapping

from app.services.state.dependencies import StateEngineDependencies
from app.services.state import runtime_core as _runtime_core

EXPORTED_SYMBOLS = ["public_turn", "build_campaign_view"]

# Prompt/config globals intentionally remain import-compatible for app.main and
# prompt wiring tests while the runtime bridge is retired.
CANON_EXTRACTOR_JSON_CONTRACT = _runtime_core.CANON_EXTRACTOR_JSON_CONTRACT
CANON_EXTRACTOR_SYSTEM_PROMPT = _runtime_core.CANON_EXTRACTOR_SYSTEM_PROMPT
CHARACTER_ATTRIBUTE_SYSTEM_PROMPT = _runtime_core.CHARACTER_ATTRIBUTE_SYSTEM_PROMPT
CONTEXT_ASSISTANT_SYSTEM_PROMPT = _runtime_core.CONTEXT_ASSISTANT_SYSTEM_PROMPT
MANIFESTATION_SKILL_NAME_SYSTEM_PROMPT = _runtime_core.MANIFESTATION_SKILL_NAME_SYSTEM_PROMPT
MEMORY_SYSTEM_PROMPT = _runtime_core.MEMORY_SYSTEM_PROMPT
NPC_EXTRACTOR_JSON_CONTRACT = _runtime_core.NPC_EXTRACTOR_JSON_CONTRACT
NPC_EXTRACTOR_SYSTEM_PROMPT = _runtime_core.NPC_EXTRACTOR_SYSTEM_PROMPT
PROGRESSION_EXTRACTOR_JSON_CONTRACT = _runtime_core.PROGRESSION_EXTRACTOR_JSON_CONTRACT
PROGRESSION_EXTRACTOR_SYSTEM_PROMPT = _runtime_core.PROGRESSION_EXTRACTOR_SYSTEM_PROMPT
SETUP_QUESTION_SYSTEM_PROMPT = _runtime_core.SETUP_QUESTION_SYSTEM_PROMPT
SETUP_RANDOM_SYSTEM_PROMPT = _runtime_core.SETUP_RANDOM_SYSTEM_PROMPT
TURN_RESPONSE_JSON_CONTRACT = _runtime_core.TURN_RESPONSE_JSON_CONTRACT

_CONFIGURED = False
DATA_DIR = _runtime_core.DATA_DIR
CAMPAIGNS_DIR = _runtime_core.CAMPAIGNS_DIR

_RUNTIME_SYMBOL_NAMES = (
    "append_character_change_events",
    "current_question_id",
    "deep_copy",
    "emit_turn_phase_event",
    "ensure_question_ai_copy",
    "normalize_class_current",
    "rebuild_memory_summary",
    "remember_recent_story",
    "try_generate_adventure_intro",
    "utc_now",
)


def configure_dependencies(deps: StateEngineDependencies) -> None:
    global _CONFIGURED
    _runtime_core.configure_dependencies(deps)
    _CONFIGURED = bool(getattr(_runtime_core, "_CONFIGURED", False))


def configure(main_globals: Mapping[str, Any] | StateEngineDependencies) -> None:
    global _CONFIGURED
    _runtime_core.configure(main_globals)
    _CONFIGURED = bool(getattr(_runtime_core, "_CONFIGURED", False))


def runtime_symbols() -> Dict[str, Any]:
    runtime = _runtime_core.runtime_symbols()
    return {name: globals().get(name, runtime[name]) for name in _RUNTIME_SYMBOL_NAMES if name in runtime}


def public_turn(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return _runtime_core.public_turn(*args, **kwargs)


def build_campaign_view(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    return _runtime_core.build_campaign_view(*args, **kwargs)


def _sync_runtime_paths() -> None:
    _runtime_core.DATA_DIR = DATA_DIR
    _runtime_core.CAMPAIGNS_DIR = CAMPAIGNS_DIR


def ensure_campaign_storage(*args: Any, **kwargs: Any) -> Any:
    _sync_runtime_paths()
    return _runtime_core.ensure_campaign_storage(*args, **kwargs)


def create_campaign_record(*args: Any, **kwargs: Any) -> Any:
    _sync_runtime_paths()
    return _runtime_core.create_campaign_record(*args, **kwargs)


def load_campaign(*args: Any, **kwargs: Any) -> Any:
    _sync_runtime_paths()
    return _runtime_core.load_campaign(*args, **kwargs)


def __getattr__(name: str) -> Any:
    return getattr(_runtime_core, name)
