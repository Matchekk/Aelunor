from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.services.world.text_normalization import first_sentences, normalized_eval_text

def infer_auto_class_tags(text: str) -> List[str]:
    lowered = normalized_eval_text(text)
    tags: List[str] = []
    if any(marker in lowered for marker in ("schatten", "nacht", "dunkel")):
        tags.append("schatten")
    if any(marker in lowered for marker in ("rune", "sigille", "glyph")):
        tags.append("rune")
    if any(marker in lowered for marker in ("heilig", "licht", "paladin")):
        tags.append("heilig")
    if any(marker in lowered for marker in ("klinge", "schwert", "krieger", "kämpfer", "kampf")):
        tags.append("kampf")
    if any(marker in lowered for marker in ("arkan", "magie", "zauber", "mana", "aether", "qi")):
        tags.append("magie")
    if any(marker in lowered for marker in ("blut", "opfer")):
        tags.append("blut")
    return list(dict.fromkeys(tags or ["allgemein"]))

def normalize_class_rank_text(value: str) -> str:
    text = normalized_eval_text(value).replace("-", " ")
    match = re.search(r"\b([fedcbas])\s*rang\b", text) or re.search(r"\b([fedcbas])\b", text)
    if not match:
        return "F"
    return str(match.group(1) or "F").upper()

def clean_auto_class_name(name: str) -> str:
    text = str(name or "").strip(" .,:;!?\"“”„'()[]{}")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s*\(([A-FS])\s*-?\s*Rang\)\s*$", "", text, flags=re.IGNORECASE).strip()
    if text.startswith("des "):
        text = text[4:].strip()
    if text.startswith("der "):
        text = text[4:].strip()
    if text.startswith("des "):
        text = text[4:].strip()
    if len(text) > 4 and text.endswith("s") and not text.endswith(("ss", "us", "is", "os", "as", "es", "ys")):
        text = text[:-1]
    return text.strip()

def extract_auto_class_change(text: str, actor_display: str) -> Optional[Dict[str, Any]]:
    content = str(text or "").strip()
    if not content:
        return None
    actor_display = str(actor_display or "").strip()
    if actor_display:
        subject_pattern = rf"(?:\b{re.escape(actor_display)}\b|\b(?:er|sie)\b)"
    else:
        # Empty actor_display would make `\b{actor}\b` an empty-string match that
        # fires on any subject; restrict to pronouns so a class is not mis-attributed.
        subject_pattern = r"\b(?:er|sie)\b"
    class_name_pattern = r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9'’\-]+(?:\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9'’\-]+){0,3})"
    rank_pattern = r"(?:\s*\(([A-FS])\s*-?\s*Rang\))?"
    patterns = [
        rf"{subject_pattern}[^.!?\n]*?\bwird(?:\s+wie\s+einst)?(?:\s+wieder)?\s+zur Klasse des\s+{class_name_pattern}{rank_pattern}",
        rf"{subject_pattern}[^.!?\n]*?\bwird(?:\s+wie\s+einst)?(?:\s+wieder)?\s+zum\s+{class_name_pattern}{rank_pattern}",
        rf"{subject_pattern}[^.!?\n]*?\bist jetzt(?:\s+wieder)?\s+(?:ein|eine)\s+{class_name_pattern}{rank_pattern}",
        rf"{subject_pattern}[^.!?\n]*?\berlangt die Klasse\s+{class_name_pattern}{rank_pattern}",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        class_name = clean_auto_class_name(match.group(1) or "")
        if not class_name:
            continue
        rank = normalize_class_rank_text(match.group(2) or "")
        class_id = f"class_{re.sub(r'[^a-z0-9]+', '_', normalized_eval_text(class_name)).strip('_') or 'unknown'}"
        return {
            "id": class_id,
            "name": class_name,
            "rank": rank,
            "level": 1,
            "level_max": 10,
            "xp": 0,
            "xp_next": 100,
            "affinity_tags": infer_auto_class_tags(class_name + " " + content),
            "description": first_sentences(content, 2)[:220],
            "ascension": {
                "status": "none",
                "quest_id": None,
                "requirements": [],
                "result_hint": None,
            },
        }
    return None
