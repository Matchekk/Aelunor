from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from app.prompts.system_prompts import TURN_RESPONSE_JSON_CONTRACT


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
        return "Antworte ausschlieÃŸlich mit gÃ¼ltigem JSON ohne Markdown."
    return (
        "Antworte ausschlieÃŸlich mit gÃ¼ltigem JSON ohne Markdown. "
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
