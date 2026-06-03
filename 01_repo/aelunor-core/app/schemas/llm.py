import json
from typing import Any, Dict


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


def build_canon_extractor_schema(response_schema: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "patch": json.loads(json.dumps(response_schema["properties"]["patch"])),
        },
        "required": ["patch"],
        "additionalProperties": False,
        "$defs": json.loads(json.dumps(response_schema.get("$defs", {}))),
    }


def build_progression_extractor_schema(response_schema: Dict[str, Any]) -> Dict[str, Any]:
    char_patch_properties = (((response_schema.get("$defs") or {}).get("char_patch") or {}).get("properties") or {})
    return {
        "type": "object",
        "properties": {
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "reason": {"type": "string"},
            "character_patch": {
                "type": "object",
                "properties": {
                    "skills_set": json.loads(json.dumps(char_patch_properties.get("skills_set", {"type": "object", "additionalProperties": True}))),
                    "skills_delta": json.loads(json.dumps(char_patch_properties.get("skills_delta", {"type": "object", "additionalProperties": True}))),
                    "progression_events": json.loads(
                        json.dumps(char_patch_properties.get("progression_events", {"type": "array", "items": {"type": "object", "additionalProperties": True}}))
                    ),
                    "class_set": json.loads(json.dumps(char_patch_properties.get("class_set", {"type": "object", "additionalProperties": True}))),
                    "class_update": json.loads(json.dumps(char_patch_properties.get("class_update", {"type": "object", "additionalProperties": True}))),
                    "progression_set": json.loads(json.dumps(char_patch_properties.get("progression_set", {"type": "object", "additionalProperties": True}))),
                },
                "additionalProperties": False,
            },
        },
        "required": ["confidence", "character_patch"],
        "additionalProperties": False,
    }


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

STORY_REWRITE_SCHEMA = {
    "type": "object",
    "properties": {"story": {"type": "string"}},
    "required": ["story"],
    "additionalProperties": False,
}

SETUP_RANDOM_SCHEMA = {
    "type": "object",
    "properties": {
        "value": {"type": ["string", "boolean", "number", "null"]},
        "selected": {
            "oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}, {"type": "null"}]
        },
        "other_text": {"type": "string"},
        "other_values": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["value", "selected", "other_text", "other_values"],
    "additionalProperties": False,
}

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
    "required": ["status", "intent", "target", "confidence", "entity_type", "entity_id", "title", "explanation", "facts", "sources", "suggestions"],
    "additionalProperties": False,
}

CHARACTER_ATTRIBUTE_SCHEMA = {
    "type": "object",
    "properties": {key: {"type": "integer"} for key in ("str", "dex", "con", "int", "wis", "cha", "luck")},
    "required": ["str", "dex", "con", "int", "wis", "cha", "luck"],
    "additionalProperties": False,
}

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
                "required": ["name", "description", "theme"], "additionalProperties": False,
            },
        }
    },
    "required": ["elements"],
    "additionalProperties": False,
}

MANIFESTATION_SKILL_NAME_SCHEMA = {
    "type": "object",
    "properties": {"name": {"type": "string"}},
    "required": ["name"],
    "additionalProperties": False,
}
