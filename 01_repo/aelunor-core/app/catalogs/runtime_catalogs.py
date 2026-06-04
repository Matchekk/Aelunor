import json
import os
from typing import Any, Dict

from app.core.paths import BASE_DIR
from app.schemas.llm import (
    build_canon_extractor_schema,
    build_progression_extractor_schema,
    extend_turn_patch_schema,
)


def load_json_catalog(filename: str) -> Dict[str, Any]:
    with open(os.path.join(BASE_DIR, filename), "r", encoding="utf-8") as f:
        return json.load(f)


PROMPTS = load_json_catalog("prompts.json")
SETUP_CATALOG = load_json_catalog("setup_catalog.json")

SYSTEM_PROMPT = PROMPTS["system_prompt"]
RESPONSE_SCHEMA = extend_turn_patch_schema(PROMPTS["response_schema"])
INITIAL_STATE = PROMPTS["initial_state"]
CATALOG_VERSION = SETUP_CATALOG["version"]
WORLD_FORM_CATALOG = SETUP_CATALOG["world_form_catalog"]
CHARACTER_FORM_CATALOG = SETUP_CATALOG["character_form_catalog"]
WORLD_QUESTION_MAP = {entry["id"]: entry for entry in WORLD_FORM_CATALOG}
CHARACTER_QUESTION_MAP = {entry["id"]: entry for entry in CHARACTER_FORM_CATALOG}

CANON_EXTRACTOR_SCHEMA = build_canon_extractor_schema(RESPONSE_SCHEMA)
PROGRESSION_EXTRACTOR_SCHEMA = build_progression_extractor_schema(RESPONSE_SCHEMA)
