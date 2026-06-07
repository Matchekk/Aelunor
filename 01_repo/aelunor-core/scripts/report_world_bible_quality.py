from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

CORE_ROOT = Path(__file__).resolve().parents[1]
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

from app.core.paths import CAMPAIGNS_DIR
from app.services.world.entity_guard import infer_world_naming_mode, looks_like_generic_fantasy_name
from scripts.report_filters import add_campaign_filter_args, build_filter_options, filter_campaigns


CATEGORY_MAX = {
    "identity": 10,
    "linguistics": 20,
    "naming_rules": 20,
    "metaphysics": 15,
    "progression": 10,
    "races_and_beasts": 10,
    "items": 10,
    "tone_and_style": 5,
}
NAMING_BLOCKS = ("people", "settlements", "regions", "ruins", "factions", "skills", "items", "beasts", "titles")
MODERN_MODES = {"modern_japanese", "modern_global", "superhero_academy", "cyberpunk", "sci_fi", "mystery"}
FANTASY_MODES = {"invented_fantasy", "dark_fantasy", "isekai_fantasy"}


def iter_campaign_files(campaign_id: str | None = None) -> list[Path]:
    campaigns_dir = Path(CAMPAIGNS_DIR)
    if campaign_id:
        path = campaigns_dir / f"{campaign_id}.json"
        return [path] if path.exists() else []
    if not campaigns_dir.exists():
        return []
    return sorted(campaigns_dir.glob("*.json"))


def load_campaign_json(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def get_world_bible_from_campaign(campaign: dict) -> dict:
    bible = (((campaign.get("state") or {}).get("world") or {}).get("bible") or {})
    return bible if isinstance(bible, dict) else {}


def assess_world_bible_quality(bible: dict, *, campaign: dict | None = None) -> dict:
    bible = bible if isinstance(bible, dict) else {}
    naming_mode = infer_world_naming_mode(bible) if bible else "unknown"
    category_scores = {
        "identity": assess_identity_quality(bible),
        "linguistics": assess_linguistics_quality(bible, campaign=campaign),
        "naming_rules": assess_naming_rules_quality(bible, naming_mode=naming_mode),
        "metaphysics": assess_metaphysics_quality(bible, naming_mode=naming_mode),
        "progression": assess_progression_quality(bible, naming_mode=naming_mode),
        "races_and_beasts": assess_races_and_beasts_quality(bible, campaign=campaign),
        "items": assess_items_quality(bible, naming_mode=naming_mode),
        "tone_and_style": assess_tone_and_style_quality(bible),
    }
    total = sum(int(row["score"]) for row in category_scores.values())
    weak_areas = []
    warnings = []
    missing_blocks = []
    for name, row in category_scores.items():
        if row["score"] < int(row["max"] * 0.65):
            weak_areas.append(name)
        warnings.extend(row.get("warnings") or [])
        missing_blocks.extend(row.get("missing_blocks") or [])
    if not bible:
        warnings.append("World Bible missing.")
        missing_blocks.append("state.world.bible")
    return {
        "score": max(0, min(100, int(total))),
        "naming_mode": naming_mode,
        "category_scores": category_scores,
        "weak_areas": _unique(weak_areas),
        "warnings": _unique(warnings),
        "missing_blocks": _unique(missing_blocks),
    }


def assess_identity_quality(bible: dict) -> dict:
    identity = _dict(bible.get("identity"))
    created = _dict(bible.get("created_from_setup"))
    result = _category("identity")
    _add_if(result, identity.get("world_name"), 2, "identity.world_name", "world_name missing")
    _add_if(result, identity.get("core_pitch"), 2, "identity.core_pitch", "core_pitch missing")
    _add_if(result, identity.get("genre_shape") or created.get("theme"), 2, "identity.genre_shape", "genre/theme missing")
    _add_if(result, identity.get("dominant_mood"), 2, "identity.dominant_mood", "dominant_mood missing")
    _add_if(result, _list(identity.get("forbidden_generic_feel")), 2, "identity.forbidden_generic_feel", "forbidden_generic_feel empty")
    return result


def assess_linguistics_quality(bible: dict, *, campaign: dict | None = None) -> dict:
    result = _category("linguistics")
    linguistics = _dict(bible.get("linguistics"))
    languages = _dict(linguistics.get("world_languages"))
    roots = []
    has_named_language = False
    has_examples = False
    for language in languages.values():
        language = _dict(language)
        has_named_language = has_named_language or bool(_text(language.get("name") or language.get("sound")))
        roots.extend(_list(language.get("common_roots")))
        has_examples = has_examples or bool(_dict(language.get("example_words")))
    _add_if(result, languages, 3, "linguistics.world_languages", "world_languages missing")
    _add_if(result, has_named_language, 3, "language name/sound", "no language has name or sound")
    _add_if(result, len(roots) >= 5, 4, "world-language roots >= 5", f"world-language roots too few ({len(roots)})")
    _add_if(result, has_examples, 2, "example_words", "example_words missing")
    race_needed = _campaign_suggests_races(campaign) and infer_world_naming_mode(bible) not in MODERN_MODES
    race_languages = _dict(linguistics.get("race_languages"))
    if race_needed:
        _add_if(result, race_languages, 3, "race_languages", "race_languages missing despite race/beast hints")
    else:
        result["score"] += 3
    controls = _dict(bible.get("runtime_controls"))
    aliases = _dict(linguistics.get("place_name_aliases"))
    _add_if(result, aliases or controls.get("allow_runtime_extensions"), 2, "place_name_aliases/runtime extensions", "place_name_aliases empty")
    _add_if(result, _dict(linguistics.get("translation_rules")), 2, "translation_rules", "translation_rules missing")
    _add_if(result, _list(linguistics.get("comprehension_rules")), 1, "comprehension_rules", "comprehension_rules empty")
    return _clamp_category(result)


def assess_naming_rules_quality(bible: dict, *, naming_mode: str = "unknown") -> dict:
    result = _category("naming_rules")
    rules = _dict(bible.get("naming_rules"))
    existing = [key for key in NAMING_BLOCKS if isinstance(rules.get(key), dict)]
    patterns = [key for key in NAMING_BLOCKS if _list(_dict(rules.get(key)).get("patterns"))]
    examples = [key for key in NAMING_BLOCKS if _list(_dict(rules.get(key)).get("examples"))]
    avoids = [key for key in NAMING_BLOCKS if _list(_dict(rules.get(key)).get("avoid"))]
    result["score"] += min(5, round(len(existing) / len(NAMING_BLOCKS) * 5))
    result["score"] += min(5, round(len(patterns) / len(NAMING_BLOCKS) * 5))
    result["score"] += min(5, round(len(examples) / len(NAMING_BLOCKS) * 5))
    result["score"] += min(3, round(len(avoids) / len(NAMING_BLOCKS) * 3))
    if len(existing) < len(NAMING_BLOCKS):
        result["missing_blocks"].append("naming_rules incomplete")
    if not patterns:
        result["warnings"].append("naming_rules patterns empty")
    if not examples:
        result["warnings"].append("naming_rules examples empty")
    if _mode_has_key_examples(rules, naming_mode):
        result["score"] += 2
    else:
        result["warnings"].append(f"{naming_mode} mode lacks central naming examples")
    if naming_mode in FANTASY_MODES and _generic_only_examples(rules.get("skills")):
        result["warnings"].append("fantasy skill examples look generic")
    return _clamp_category(result)


def assess_metaphysics_quality(bible: dict, *, naming_mode: str = "unknown") -> dict:
    result = _category("metaphysics")
    meta = _dict(bible.get("metaphysics"))
    low_magic = naming_mode in {"modern_global", "mystery"} and _text(meta.get("main_power_description") or meta.get("power_limitations"))
    _add_if(result, meta.get("main_power_name") or low_magic, 3, "main_power_name/low-magic explanation", "main_power_name missing")
    _add_if(result, meta.get("main_power_description"), 3, "main_power_description", "main_power_description missing")
    _add_if(result, meta.get("power_source") or meta.get("power_cost"), 3, "power_source/power_cost", "power_source and power_cost missing")
    _add_if(result, _list(meta.get("power_limitations")), 2, "power_limitations", "power_limitations empty")
    _add_if(result, _list(meta.get("world_laws")), 2, "world_laws", "world_laws empty")
    _add_if(result, _list(meta.get("taboos")) or meta.get("death_rule") or meta.get("healing_rule") or meta.get("corruption_rule"), 2, "taboos/death/healing/corruption", "taboo/death/healing/corruption rules missing")
    return result


def assess_progression_quality(bible: dict, *, naming_mode: str = "unknown") -> dict:
    result = _category("progression")
    progression = _dict(bible.get("progression"))
    _add_if(result, _dict(progression.get("rank_language")), 2, "rank_language", "rank_language missing")
    _add_if(result, progression.get("class_origin_rules"), 2, "class_origin_rules", "class_origin_rules missing")
    _add_if(result, _list(progression.get("class_naming_rules")), 2, "class_naming_rules", "class_naming_rules empty")
    _add_if(result, _list(progression.get("skill_manifestation_rules")), 2, "skill_manifestation_rules", "skill_manifestation_rules empty")
    _add_if(result, _list(progression.get("skill_cost_rules")) or progression.get("ascension_rules"), 2, "skill_cost_rules/ascension_rules", "skill cost/ascension rules missing")
    if naming_mode in {"superhero_academy", "cyberpunk"} and result["score"] < 7:
        result["warnings"].append(f"{naming_mode} mode needs power/training/gear progression rules")
    return result


def assess_races_and_beasts_quality(bible: dict, *, campaign: dict | None = None) -> dict:
    result = _category("races_and_beasts")
    data = _dict(bible.get("races_and_beasts"))
    race_needed = _campaign_suggests_races(campaign) or infer_world_naming_mode(bible) not in MODERN_MODES
    checks = [
        ("race_origin_rules", 2),
        ("race_naming_rules", 2),
        ("beast_origin_rules", 2),
        ("beast_naming_rules", 2),
    ]
    for key, points in checks:
        value = _list(data.get(key)) if key.endswith("_rules") and isinstance(data.get(key), list) else data.get(key)
        if value:
            result["score"] += points
        elif race_needed:
            result["warnings"].append(f"{key} missing")
    if _list(data.get("ecology_rules")) or _list(data.get("knowledge_discovery_rules")):
        result["score"] += 2
    elif race_needed:
        result["warnings"].append("ecology/knowledge discovery rules missing")
    if not race_needed:
        result["score"] = max(result["score"], 7)
        result["warnings"].append("races/beasts less central for inferred modern mode")
    return _clamp_category(result)


def assess_items_quality(bible: dict, *, naming_mode: str = "unknown") -> dict:
    result = _category("items")
    items = _dict(bible.get("items"))
    _add_if(result, _list(items.get("item_naming_rules")), 2, "item_naming_rules", "item_naming_rules empty")
    _add_if(result, _dict(items.get("rarity_language")), 2, "rarity_language", "rarity_language missing")
    materials = _list(items.get("material_vocabulary"))
    _add_if(result, len(materials) >= 3, 3, "material_vocabulary >= 3", f"item.material_vocabulary has only {len(materials)} entries")
    _add_if(result, _list(items.get("curse_rules")) or _list(items.get("relic_rules")) or _has_setting_item_rules(items, naming_mode), 2, "curse/relic/setting item rules", "curse/relic/setting item rules missing")
    _add_if(result, _list(items.get("earth_item_transformation_rules")) or _has_setting_upgrade_rules(items, naming_mode), 1, "transformation/upgrade rules", "transformation/upgrade rules missing")
    return result


def assess_tone_and_style_quality(bible: dict) -> dict:
    result = _category("tone_and_style")
    tone = _dict(bible.get("tone_and_style"))
    _add_if(result, _list(tone.get("narration_rules")), 1, "narration_rules", "narration_rules empty")
    _add_if(result, _list(tone.get("forbidden_words")), 1, "forbidden_words", "forbidden_words empty")
    _add_if(result, _list(tone.get("preferred_motifs")), 1, "preferred_motifs", "preferred_motifs empty")
    senses = sum(1 for values in _dict(tone.get("sensory_palette")).values() if _list(values))
    _add_if(result, senses >= 2, 2, "sensory_palette >= 2 senses", "sensory_palette has fewer than 2 filled senses")
    return result


def build_world_bible_quality_review(campaigns: list[dict], *, filter_meta: dict | None = None) -> dict:
    rows = []
    for campaign in campaigns:
        meta = _dict(campaign.get("campaign_meta"))
        quality = assess_world_bible_quality(get_world_bible_from_campaign(campaign), campaign=campaign)
        rows.append(
            {
                "campaign_id": _text(meta.get("campaign_id")),
                "title": _text(meta.get("title")),
                **quality,
            }
        )
    average = round(sum(row["score"] for row in rows) / len(rows), 2) if rows else None
    summary = {"campaigns_scanned": len(rows), "average_score": average}
    if isinstance(filter_meta, dict):
        summary.update(filter_meta)
    return {"summary": summary, "campaigns": rows}


def render_markdown_report(review: dict, *, limit: int = 50) -> str:
    campaigns = (review.get("campaigns") or [])[: max(1, int(limit or 50))]
    summary = review.get("summary") or {}
    lines = [
        "# World Bible Quality Report",
        "",
        f"Campaigns scanned: {summary.get('campaigns_scanned', 0)}",
        f"Average score: {_fmt(summary.get('average_score'))}",
    ]
    if summary.get("filters"):
        lines.extend(["", "Filters:"])
        filters = summary.get("filters") or {}
        for key in sorted(filters):
            lines.append(f"- {key}: {_fmt_filter(filters[key])}")
    if summary.get("campaigns_skipped"):
        lines.append(f"Campaigns skipped: {summary.get('campaigns_skipped')}")
    lines.extend(["", "## Campaign Breakdown", "", "| Campaign | Title | Score | Naming Mode | Main Weak Areas |", "| --- | --- | ---: | --- | --- |"])
    for row in campaigns:
        lines.append(f"| {row['campaign_id']} | {row['title']} | {row['score']} | {row['naming_mode']} | {', '.join(row.get('weak_areas') or []) or '-'} |")
    lines.extend(["", "## Detailed Findings"])
    for row in campaigns:
        lines.extend(["", f"### {row['title'] or row['campaign_id'] or 'Unknown'} - {row['score']}/100", "", f"Naming Mode: {row['naming_mode']}", "", "Category Scores:"])
        for name, category in row.get("category_scores", {}).items():
            lines.append(f"- {name}: {category['score']}/{category['max']}")
        lines.extend(["", "Weak Areas:"])
        lines.extend(f"- {area}" for area in (row.get("weak_areas") or ["-"]))
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning}" for warning in (row.get("warnings") or ["-"]))
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only World-Bible-Quality-Report ueber gespeicherte Campaigns.")
    parser.add_argument("--campaign-id", default=None)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--out", default=None)
    parser.add_argument("--limit", type=int, default=50)
    add_campaign_filter_args(parser)
    args = parser.parse_args()
    campaigns = [campaign for path in iter_campaign_files(args.campaign_id) if (campaign := load_campaign_json(path)) is not None]
    campaigns, filter_meta = filter_campaigns(campaigns, build_filter_options(args), report_kind="world_bible")
    review = build_world_bible_quality_review(campaigns, filter_meta=filter_meta)
    output = json.dumps(review, ensure_ascii=False, indent=2) + "\n" if args.as_json else render_markdown_report(review, limit=args.limit)
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


def _category(name: str) -> dict:
    return {"score": 0, "max": CATEGORY_MAX[name], "warnings": [], "missing_blocks": []}


def _add_if(result: dict, condition: Any, points: int, _label: str, warning: str) -> None:
    if condition:
        result["score"] += points
    else:
        result["warnings"].append(warning)


def _clamp_category(result: dict) -> dict:
    result["score"] = min(int(result["score"]), int(result["max"]))
    return result


def _mode_has_key_examples(rules: dict, naming_mode: str) -> bool:
    if naming_mode in {"modern_japanese", "superhero_academy", "modern_global"}:
        keys = ("people", "factions", "settlements")
    elif naming_mode == "cyberpunk":
        keys = ("people", "factions", "items")
    else:
        keys = ("skills", "items", "settlements", "regions")
    return any(_list(_dict(rules.get(key)).get("examples")) for key in keys)


def _generic_only_examples(rule: Any) -> bool:
    examples = _list(_dict(rule).get("examples"))
    return bool(examples) and all(looks_like_generic_fantasy_name(example) for example in examples)


def _campaign_suggests_races(campaign: dict | None) -> bool:
    state = _dict((campaign or {}).get("state"))
    world = _dict(state.get("world"))
    codex = _dict(state.get("codex"))
    setup = _dict(_dict((campaign or {}).get("setup")).get("world"))
    setup_text = json.dumps(setup.get("summary") or {}, ensure_ascii=False).lower()
    return bool(world.get("races") or world.get("beast_types") or _dict(codex.get("races")) or _dict(codex.get("beasts")) or "race" in setup_text or "spezies" in setup_text or "monster" in setup_text)


def _has_setting_item_rules(items: dict, naming_mode: str) -> bool:
    text = json.dumps(items, ensure_ascii=False).lower()
    if naming_mode in {"superhero_academy", "modern_japanese"}:
        return "support" in text or "gear" in text or "costume" in text
    if naming_mode == "cyberpunk":
        return "implant" in text or "gear" in text or "mod" in text
    return False


def _has_setting_upgrade_rules(items: dict, naming_mode: str) -> bool:
    text = json.dumps(items, ensure_ascii=False).lower()
    return any(token in text for token in ("upgrade", "transformation", "support", "implant", "mod", "gear")) and naming_mode in MODERN_MODES | {"cyberpunk"}


def _dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return [entry for entry in value if entry not in (None, "")]
    if isinstance(value, tuple):
        return [entry for entry in value if entry not in (None, "")]
    if isinstance(value, dict):
        return [entry for entry in value.values() if entry not in (None, "")]
    return [value] if value not in (None, "") else []


def _text(value: Any) -> str:
    return str(value or "").strip()


def _unique(values: Iterable[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        key = str(value).casefold()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _fmt(value: Any) -> str:
    return "-" if value is None else str(value)


def _fmt_filter(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, list):
        return ", ".join(str(entry) for entry in value)
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
