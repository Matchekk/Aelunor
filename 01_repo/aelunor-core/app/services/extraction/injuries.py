from __future__ import annotations

import re
from typing import Any, Dict, List

from app.core.ids import deep_copy, make_id
from app.services.campaigns.party import display_name_for_slot
from app.services.extraction.items import sentence_mentions_actor_name
from app.services.world.scene import clean_scene_name
from app.services.world.text_normalization import normalized_eval_text
from app.text.patterns import AUTO_INJURY_PATTERNS

def infer_injury_severity(sentence: str, title: str) -> str:
    lowered = normalized_eval_text(f"{sentence} {title}")
    if any(marker in lowered for marker in ("gebrochen", "klaffend", "offen", "tiefer", "schwere", "schwerer", "schweren")):
        return "schwer"
    if any(marker in lowered for marker in ("blut", "brand", "biss", "schnitt", "stich", "prell", "verstauch")):
        return "mittel"
    return "leicht"

def infer_injury_effects(title: str, severity: str) -> List[str]:
    normalized_title = normalized_eval_text(title)
    effects: List[str] = []
    if any(marker in normalized_title for marker in ("arm", "hand", "schulter")):
        effects.append("Schmerz bei Kraft")
    if any(marker in normalized_title for marker in ("bein", "knie", "fuss", "fuß", "huefte", "hüfte")):
        effects.append("Schmerz bei Bewegung")
    if any(marker in normalized_title for marker in ("brust", "rippe", "bauch")):
        effects.append("Atemnot unter Belastung")
    if severity == "schwer":
        effects.append("Erschwert konzentrierte Aktionen")
    elif severity == "mittel":
        effects.append("Belastung verschlimmert den Schmerz")
    return list(dict.fromkeys([entry for entry in effects if entry])) or ["Schmerz bei Belastung"]

def clean_auto_injury_title(raw_title: str) -> str:
    title = clean_scene_name(raw_title)
    title = re.sub(
        r"\s+(zwingt|laesst|lässt|macht|verursacht|hindert|bringt|treibt|wirft)\b.*$",
        "",
        title,
        flags=re.IGNORECASE,
    ).strip()
    return title

def extract_auto_story_injuries(story_text: str, actor_display: str) -> List[Dict[str, Any]]:
    actor_name = normalized_eval_text(actor_display)
    story_mentions_actor = actor_name in normalized_eval_text(story_text)
    candidates: List[Dict[str, Any]] = []
    seen = set()
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", str(story_text or "")):
        sentence = sentence.strip()
        if not sentence:
            continue
        normalized_sentence = normalized_eval_text(sentence)
        if actor_name and not sentence_mentions_actor_name(sentence, actor_display) and not normalized_sentence.startswith(("er ", "sie ", "es ")) and not story_mentions_actor:
            continue
        for pattern in AUTO_INJURY_PATTERNS:
            for match in pattern.findall(sentence):
                raw_match = " ".join(part for part in match) if isinstance(match, tuple) else str(match or "")
                title = clean_auto_injury_title(raw_match)
                normalized_title = normalized_eval_text(title)
                if not title or normalized_title in seen:
                    continue
                seen.add(normalized_title)
                severity = infer_injury_severity(sentence, title)
                candidates.append(
                    {
                        "id": make_id("inj"),
                        "title": title[:80],
                        "severity": severity,
                        "effects": infer_injury_effects(title, severity),
                        "healing_stage": "frisch",
                        "will_scar": severity != "leicht" or any(marker in normalized_title for marker in ("schnitt", "stich", "biss", "brand", "gebrochen")),
                        "created_turn": 0,
                        "notes": sentence[:220].strip(),
                    }
                )
                if len(candidates) >= 2:
                    return candidates
    return candidates

def inject_story_injuries(
    campaign: Dict[str, Any],
    working_state: Dict[str, Any],
    actor: str,
    story_text: str,
    patch: Dict[str, Any],
    *,
    seed_text: str = "",
) -> Dict[str, Any]:
    if actor not in (working_state.get("characters") or {}):
        return patch
    actor_display = display_name_for_slot(campaign, actor)
    candidates = extract_auto_story_injuries(story_text, actor_display)
    if seed_text:
        known = {normalized_eval_text(entry.get("title", "")) for entry in candidates}
        for candidate in extract_auto_story_injuries(seed_text, actor_display):
            normalized_title = normalized_eval_text(candidate.get("title", ""))
            if normalized_title and normalized_title not in known:
                known.add(normalized_title)
                candidates.append(candidate)
    if not candidates:
        return patch
    character = (working_state.get("characters", {}).get(actor) or {})
    existing_titles = {
        normalized_eval_text((entry or {}).get("title", ""))
        for entry in (character.get("injuries") or [])
        if isinstance(entry, dict)
    }
    target_patch = patch.setdefault("characters", {}).setdefault(actor, {})
    target_patch.setdefault("injuries_add", [])
    existing_titles.update(
        normalized_eval_text((entry or {}).get("title", ""))
        for entry in (target_patch.get("injuries_add") or [])
        if isinstance(entry, dict)
    )
    next_turn = int((working_state.get("meta", {}) or {}).get("turn", 0) or 0)
    for candidate in candidates:
        normalized_title = normalized_eval_text(candidate.get("title", ""))
        if not normalized_title or normalized_title in existing_titles:
            continue
        existing_titles.add(normalized_title)
        injury_payload = deep_copy(candidate)
        injury_payload["created_turn"] = next_turn
        target_patch["injuries_add"].append(injury_payload)
    return patch
