from __future__ import annotations

import hashlib
import json
import random
import re
from typing import Any, Callable, Dict, List, Set, Tuple


def strip_name_parenthetical(name: str) -> str:
    cleaned = re.sub(r"\s*\([^)]*\)", " ", str(name or ""))
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.;:!?")
    return cleaned


def pick_world_theme_anchor(summary: Dict[str, Any], *, normalize_codex_alias_text: Callable[[str], str]) -> str:
    theme = normalize_codex_alias_text(summary.get("theme", ""))
    if "wuest" in theme or "sand" in theme:
        return "desert"
    if "wald" in theme or "forest" in theme:
        return "forest"
    if "urban" in theme or "stadt" in theme:
        return "urban"
    if "isekai" in theme or "hybrid" in theme:
        return "hybrid"
    return "default"


def fantasy_syllables_for_anchor(anchor: str) -> Tuple[List[str], List[str], List[str]]:
    if anchor == "desert":
        return (
            ["ash", "zar", "qir", "sah", "tal", "mir", "kha"],
            ["a", "e", "o", "u", "ir", "ar"],
            ["dun", "kar", "mir", "zar", "thar", "ren"],
        )
    if anchor == "forest":
        return (
            ["sil", "tha", "fen", "lor", "ny", "ael", "bri"],
            ["a", "e", "i", "ia", "ae", "el"],
            ["wen", "lith", "rien", "vale", "dor", "mir"],
        )
    if anchor == "urban":
        return (
            ["vor", "ka", "dra", "ser", "mor", "lin", "tek"],
            ["a", "e", "i", "o", "ur", "en"],
            ["gard", "port", "vex", "tarn", "heim", "crest"],
        )
    if anchor == "hybrid":
        return (
            ["neo", "ae", "ry", "sol", "ky", "zen", "myr"],
            ["a", "e", "io", "ae", "u", "i"],
            ["flux", "lume", "veil", "core", "ryn", "nex"],
        )
    return (
        ["el", "ka", "mor", "val", "rin", "tor", "lys"],
        ["a", "e", "i", "o", "ae", "ia"],
        ["dor", "ria", "en", "or", "is", "ane"],
    )


def generate_unique_fantasy_name(
    rng: random.Random,
    used: Set[str],
    *,
    anchor: str,
    suffixes: List[str],
    normalize_codex_alias_text: Callable[[str], str],
    max_attempts: int = 40,
) -> str:
    prefixes, middles, tails = fantasy_syllables_for_anchor(anchor)
    for _ in range(max_attempts):
        parts = [rng.choice(prefixes), rng.choice(middles), rng.choice(tails)]
        if rng.random() < 0.3:
            parts.insert(2, rng.choice(["n", "r", "l", "th"]))
        base = "".join(parts).replace(" ", "")
        raw_name = f"{base}{rng.choice(suffixes)}".strip()
        name = raw_name[:1].upper() + raw_name[1:]
        key = normalize_codex_alias_text(name)
        if key and key not in used:
            used.add(key)
            return name
    fallback = f"{rng.choice(['Ael', 'Vor', 'Kael', 'Nyx'])}{rng.randint(100, 999)}"
    used.add(normalize_codex_alias_text(fallback))
    return fallback


def generate_world_name(
    summary: Dict[str, Any],
    seed_hint: str,
    *,
    normalize_codex_alias_text: Callable[[str], str],
) -> str:
    anchor = pick_world_theme_anchor(summary, normalize_codex_alias_text=normalize_codex_alias_text)
    seed_text = json.dumps(
        {
            "theme": summary.get("theme", ""),
            "tone": summary.get("tone", ""),
            "seed": seed_hint,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    rng = random.Random(int(hashlib.sha1(seed_text.encode("utf-8")).hexdigest(), 16) % (2**32))
    used: Set[str] = set()
    return generate_unique_fantasy_name(
        rng,
        used,
        anchor=anchor,
        suffixes=["", "ia", "or", "is"],
        normalize_codex_alias_text=normalize_codex_alias_text,
    )
