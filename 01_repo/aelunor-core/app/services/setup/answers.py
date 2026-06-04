from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Dict, List

from app.catalogs.runtime_catalogs import SETUP_CATALOG
from app.config.setup import LEGACY_SELECT_ALIASES
from app.services.characters.appearance_state import infer_age_years
from app.services.world.text_normalization import normalized_eval_text


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


def split_creator_item_blocks(value: str) -> List[str]:
    text = str(value or "").replace("\r", "\n").strip()
    if not text:
        return []
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    blocks: List[str] = []
    current = ""
    bullet_pattern = re.compile(r"^\s*(?:\d+[\.\)]|[-*â€¢])\s+")
    for line in lines:
        if bullet_pattern.match(line):
            if current:
                blocks.append(current.strip())
            current = bullet_pattern.sub("", line).strip()
            continue
        if current:
            current = f"{current} {line}".strip()
        else:
            current = line
    if current:
        blocks.append(current.strip())
    if len(blocks) > 1:
        return blocks

    parts: List[str] = []
    buffer = ""
    depth = 0
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")" and depth > 0:
            depth -= 1
        if char == ";" and depth == 0:
            if buffer.strip():
                parts.append(buffer.strip())
            buffer = ""
            continue
        if char == "," and depth == 0:
            lookback = buffer.rstrip()
            if re.search(r"\b(?:und|oder)$", lookback, flags=re.IGNORECASE):
                buffer += char
                continue
            if buffer.strip():
                parts.append(buffer.strip())
            buffer = ""
            continue
        buffer += char
    if buffer.strip():
        parts.append(buffer.strip())
    return parts if len(parts) > 1 else [text]


def summarize_creator_item_name(raw_name: str) -> str:
    text = str(raw_name or "").replace("\n", " ").strip()
    text = re.sub(r"^\s*(?:\d+[\.\)]|[-*â€¢])\s+", "", text)
    text = re.sub(r"\s+", " ", text).strip(" ,-")
    text = re.sub(r"\((.*?)\)", "", text).strip(" ,-")
    text = re.sub(r"\s+(?:der|die|das)\s+in\s+dieser\s+welt\b.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+(?:welche|welcher|welches)\b.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+(?:fÃ¼r|fuer)\s+.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" ,-.")
    text = re.sub(r"^(?:ein|eine|einen|einem|einer)\s+", "", text, flags=re.IGNORECASE)
    text = text[:72].strip(" ,-.\"'")
    return text


def parse_earth_items(value: str) -> List[str]:
    items = []
    for chunk in split_creator_item_blocks(value):
        text = summarize_creator_item_name(chunk)
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
                factions.append({"name": name, "goal": goal_match.group(1).strip(), "methods": (goal_match.group(2) or "").strip()})
                continue
            factions.append({"name": name, "goal": detail, "methods": ""})
            continue
        parts = [part.strip() for part in re.split(r"\s+\|\s+|\s+-\s+", cleaned, maxsplit=2) if part.strip()]
        if not parts:
            parts = [part.strip() for part in cleaned.split(":", 1) if part.strip()]
        if parts:
            factions.append({"name": parts[0], "goal": parts[1] if len(parts) > 1 else cleaned, "methods": parts[2] if len(parts) > 2 else ""})
    return factions[:6]


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
            return {"selected": "Ã„lter (36+)", "other_text": ""}

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
