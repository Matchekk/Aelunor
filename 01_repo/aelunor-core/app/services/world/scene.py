from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.core.ids import make_id
from app.services.world.text_normalization import normalized_eval_text


def canonical_scene_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", normalized_eval_text(name)).strip("-")
    slug = slug[:40] or make_id("scene")
    return f"scene_{slug}"


def clean_scene_name(raw_name: str) -> str:
    name = str(raw_name or "").strip(" .,:;!?\"â€œâ€â€ž'()[]{}")
    name = re.sub(r"\s+", " ", name).strip()
    stop_suffixes = (
        " und",
        " oder",
        " als",
        " wobei",
        " wÃ¤hrend",
        " doch",
        " dann",
        " dort",
        " wieder",
        " jetzt",
    )
    lowered = normalized_eval_text(name)
    for suffix in stop_suffixes:
        if lowered.endswith(suffix):
            cut = len(name) - len(suffix)
            name = name[:cut].strip(" .,:;!?\"â€œâ€â€ž'")
            lowered = normalized_eval_text(name)
    return name


def is_plausible_scene_name(name: str) -> bool:
    normalized = normalized_eval_text(name)
    if not normalized or len(normalized) < 3:
        return False
    generic = {
        "welt",
        "nacht",
        "tag",
        "morgen",
        "abend",
        "dunkelheit",
        "schatten",
        "regen",
        "wind",
        "ferne",
        "stille",
        "chaos",
        "richtung",
        "bezug",
        "ort",
        "gebiet",
        "pfad",
        "weg",
        "gang",
        "unterholz",
        "vegetation",
        "schlucht",
        "wand",
        "nische",
        "raum",
        "kammer",
    }
    if normalized in generic:
        return False
    if normalized.startswith(("scene_", "node_", "plotpoint_")):
        return False
    return True


def is_generic_scene_identifier(scene_id: str, scene_name: str) -> bool:
    normalized_id = normalized_eval_text(scene_id)
    normalized_name = normalized_eval_text(scene_name)
    generic_tokens = {
        "richtung",
        "ort",
        "gebiet",
        "pfad",
        "weg",
        "gang",
        "nische",
        "kammer",
        "raum",
        "unterholz",
        "vegetation",
        "schlucht",
        "wand",
    }
    if normalized_id in {"", "scene"}:
        return True
    if normalized_id.startswith(("scene_richtung", "scene_ort", "scene_gebiet", "scene_pfad", "scene_weg")):
        return True
    if normalized_name in generic_tokens:
        return True
    return False


def extract_scene_candidates(text: str, actor_display: str) -> List[Dict[str, str]]:
    content = str(text or "")
    if not content.strip():
        return []
    name_pattern = r"([A-ZÃ„Ã–Ãœ][A-Za-zÃ„Ã–ÃœÃ¤Ã¶Ã¼ÃŸ0-9'â€™\-]+(?:\s+[A-ZÃ„Ã–Ãœ][A-Za-zÃ„Ã–ÃœÃ¤Ã¶Ã¼ÃŸ0-9'â€™\-]+){0,5})"
    article_prefix = r"(?:den|die|das|dem|der|ein|eine|einen|einem|einer)\s+"
    arrival_patterns = (
        (rf"\bDie Gruppe (?:ist jetzt in|erreicht|betritt|gelangt nach|geht nach|zieht nach|kommt in|kommt nach)\s+(?:{article_prefix})?{name_pattern}", "group"),
        (rf"\bIhr (?:erreicht|betretet|gelangt nach|geht nach|kommt in|kommt nach|zieht nach)\s+(?:{article_prefix})?{name_pattern}", "group"),
        (rf"\bDie Gruppe [^.!?\n]*?\b(?:steht|steht jetzt|befindet sich|lagert|ruht|kÃ¤mpft)\s+(?:in|an|auf|unter)\s+(?:{article_prefix})?{name_pattern}", "group"),
        (rf"\bIhr [^.!?\n]*?\b(?:steht|steht jetzt|befindet euch|seid|lagert|ruht|kÃ¤mpft)\s+(?:in|an|auf|unter)\s+(?:{article_prefix})?{name_pattern}", "group"),
        (rf"\bDie Gruppe [^.!?\n]*?\bin den Ruinen von\s+(?:{article_prefix})?{name_pattern}", "group"),
        (rf"\bIhr [^.!?\n]*?\bin den Ruinen von\s+(?:{article_prefix})?{name_pattern}", "group"),
        (rf"\b{re.escape(actor_display)} (?:ist jetzt in|erreicht|betritt|gelangt nach|geht nach|zieht nach|kommt in|kommt nach)\s+(?:{article_prefix})?{name_pattern}", "actor"),
        (rf"\b{re.escape(actor_display)} [^.!?\n]*?\b(?:steht|steht jetzt|befindet sich|lagert|ruht|kÃ¤mpft)\s+(?:in|an|auf|unter)\s+(?:{article_prefix})?{name_pattern}", "actor"),
        (rf"\b{re.escape(actor_display)} [^.!?\n]*?\bin den Ruinen von\s+(?:{article_prefix})?{name_pattern}", "actor"),
        (rf"\b(?:er|sie) (?:ist jetzt in|erreicht|betritt|gelangt nach|geht nach|zieht nach|kommt in|kommt nach)\s+(?:{article_prefix})?{name_pattern}", "actor"),
        (rf"\b(?:er|sie) [^.!?\n]*?\b(?:steht|steht jetzt|befindet sich|lagert|ruht|kÃ¤mpft)\s+(?:in|an|auf|unter)\s+(?:{article_prefix})?{name_pattern}", "actor"),
        (rf"\b(?:er|sie) [^.!?\n]*?\bin den Ruinen von\s+(?:{article_prefix})?{name_pattern}", "actor"),
    )
    mention_patterns = (
        (rf"\bin den Ruinen von\s+{name_pattern}", "mention"),
        (rf"\bin der NÃ¤he von\s+{name_pattern}", "mention"),
        (rf"\bnahe\s+{name_pattern}", "mention"),
        (rf"\bam\s+{name_pattern}", "mention"),
        (rf"\bauf dem\s+{name_pattern}", "mention"),
        (rf"\bauf der\s+{name_pattern}", "mention"),
        (rf"\bentlang der\s+{name_pattern}", "mention"),
        (rf"\bvor euch liegt\s+{name_pattern}", "mention"),
        (rf"\bvor ihnen liegt\s+{name_pattern}", "mention"),
        (rf"\bdie Stadt\s+{name_pattern}", "mention"),
        (rf"\bdas Dorf\s+{name_pattern}", "mention"),
        (rf"\bdie Festung\s+{name_pattern}", "mention"),
        (rf"\bdie Ruinen von\s+{name_pattern}", "mention"),
        (rf"\bdas Gebiet\s+{name_pattern}", "mention"),
        (rf"\bam Ort\s+{name_pattern}", "mention"),
    )
    found: List[Dict[str, str]] = []
    seen = set()
    for pattern, scope in (*arrival_patterns, *mention_patterns):
        for match in re.finditer(pattern, content):
            raw_name = clean_scene_name(match.group(1) or "")
            normalized_name = normalized_eval_text(raw_name)
            if not raw_name or len(normalized_name) < 3 or not is_plausible_scene_name(raw_name):
                continue
            key = (scope, normalized_name)
            if key in seen:
                continue
            seen.add(key)
            found.append({"scope": scope, "name": raw_name})
    return found


def extract_descriptive_scene_name(text: str) -> Optional[str]:
    content = str(text or "")
    descriptor_patterns = (
        r"\bin (?:einer|einem|der|dem|eine|ein)\s+([a-zÃ¤Ã¶Ã¼ÃŸ][a-zÃ¤Ã¶Ã¼ÃŸ\-\s]{2,48}?(?:nische|kammer|gang|krypta|ruine|tempel|lichtung|schlucht))\b",
        r"\bam (?:rand|eingang) (?:von|der)\s+([a-zÃ¤Ã¶Ã¼ÃŸ][a-zÃ¤Ã¶Ã¼ÃŸ\-\s]{2,48}?(?:ruine|krypta|lichtung|schlucht|festung|tempel))\b",
    )
    for pattern in descriptor_patterns:
        match = re.search(pattern, content, flags=re.IGNORECASE)
        if not match:
            continue
        candidate = clean_scene_name(match.group(1) or "")
        if not candidate:
            continue
        normalized = normalized_eval_text(candidate)
        if not normalized or not is_plausible_scene_name(candidate):
            continue
        return candidate[:80].strip()
    return None
