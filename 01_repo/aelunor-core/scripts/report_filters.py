from __future__ import annotations

import argparse
from datetime import datetime, timezone
from typing import Any, Iterable


def add_campaign_filter_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--exclude-empty", action="store_true", help="Skip empty or technical campaigns.")
    parser.add_argument("--only-smoke", action="store_true", help="Only include AI Smoke campaigns.")
    parser.add_argument("--min-turns", type=int, default=None, help="Only include campaigns with at least this many turns.")
    parser.add_argument("--title-contains", default=None, help="Only include campaigns whose title contains this text.")
    parser.add_argument("--exclude-title", action="append", default=[], help="Exclude campaigns whose title contains this text.")
    parser.add_argument("--created-after", default=None, help="Only include campaigns created after an ISO date or YYYY-MM-DD date.")


def build_filter_options(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "only_smoke": bool(getattr(args, "only_smoke", False)),
        "exclude_empty": bool(getattr(args, "exclude_empty", False)),
        "min_turns": getattr(args, "min_turns", None),
        "title_contains": getattr(args, "title_contains", None) or "",
        "exclude_title": list(getattr(args, "exclude_title", None) or []),
        "created_after": getattr(args, "created_after", None) or "",
    }


def active_filter_options(filters: dict[str, Any] | None) -> dict[str, Any]:
    filters = filters if isinstance(filters, dict) else {}
    active: dict[str, Any] = {}
    for key in ("only_smoke", "exclude_empty"):
        if bool(filters.get(key)):
            active[key] = True
    if filters.get("min_turns") is not None:
        active["min_turns"] = int(filters.get("min_turns") or 0)
    for key in ("title_contains", "created_after"):
        if str(filters.get(key) or "").strip():
            active[key] = str(filters.get(key)).strip()
    excluded = [str(value).strip() for value in (filters.get("exclude_title") or []) if str(value).strip()]
    if excluded:
        active["exclude_title"] = excluded
    return active


def filter_campaigns(campaigns: Iterable[dict], filters: dict[str, Any] | None = None, *, report_kind: str) -> tuple[list[dict], dict[str, Any]]:
    active = active_filter_options(filters)
    created_after = _parse_created_after(active.get("created_after"))
    included: list[dict] = []
    skipped = 0
    skip_reasons: dict[str, int] = {}
    for campaign in campaigns:
        reason = _skip_reason(campaign, active, created_after, report_kind=report_kind)
        if reason:
            skipped += 1
            skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
            continue
        included.append(campaign)
    if active.get("only_smoke"):
        included, duplicate_count = _latest_campaign_per_title(included)
        if duplicate_count:
            skipped += duplicate_count
            skip_reasons["older_smoke_run"] = skip_reasons.get("older_smoke_run", 0) + duplicate_count
    return included, {"filters": active, "campaigns_skipped": skipped, "skip_reasons": skip_reasons}


def is_smoke_campaign(campaign: dict) -> bool:
    title = _title(campaign).casefold()
    meta = _meta(campaign)
    return "ai smoke" in title or str(meta.get("source") or "").casefold() == "ai_story_smoke"


def campaign_turn_count(campaign: dict) -> int:
    return len([turn for turn in (campaign.get("turns") or []) if isinstance(turn, dict)])


def campaign_has_guard_data(campaign: dict) -> bool:
    for turn in (campaign.get("turns") or []):
        if not isinstance(turn, dict):
            continue
        for candidate in (
            turn.get("entity_guard"),
            (turn.get("prompt_payload") or {}).get("entity_guard") if isinstance(turn.get("prompt_payload"), dict) else None,
            (turn.get("debug") or {}).get("entity_guard") if isinstance(turn.get("debug"), dict) else None,
            (turn.get("meta") or {}).get("entity_guard") if isinstance(turn.get("meta"), dict) else None,
        ):
            if isinstance(candidate, dict) and (isinstance(candidate.get("reports"), list) or any(isinstance(candidate.get(key), dict) for key in ("narrator", "extractor", "merged"))):
                return True
    return False


def campaign_has_real_world_bible(campaign: dict) -> bool:
    bible = (((campaign.get("state") or {}).get("world") or {}).get("bible") or {})
    if not isinstance(bible, dict) or not bible:
        return False
    identity = bible.get("identity") if isinstance(bible.get("identity"), dict) else {}
    created = bible.get("created_from_setup") if isinstance(bible.get("created_from_setup"), dict) else {}
    naming = bible.get("naming_rules") if isinstance(bible.get("naming_rules"), dict) else {}
    return bool(
        str(identity.get("world_name") or identity.get("core_pitch") or identity.get("genre_shape") or "").strip()
        or any(str(value or "").strip() for value in created.values())
        or any(isinstance(value, dict) and (value.get("examples") or value.get("patterns")) for value in naming.values())
    )


def _skip_reason(campaign: dict, filters: dict[str, Any], created_after: datetime | None, *, report_kind: str) -> str:
    title = _title(campaign)
    if filters.get("only_smoke") and not is_smoke_campaign(campaign):
        return "not_smoke"
    title_contains = str(filters.get("title_contains") or "").strip()
    if title_contains and title_contains.casefold() not in title.casefold():
        return "title_missing"
    for excluded in filters.get("exclude_title") or []:
        if str(excluded).strip() and str(excluded).casefold() in title.casefold():
            return "excluded_title"
    min_turns = filters.get("min_turns")
    if min_turns is not None and campaign_turn_count(campaign) < int(min_turns or 0):
        return "min_turns"
    if created_after is not None:
        created_at = _parse_date(str(_meta(campaign).get("created_at") or ""))
        if created_at is None or created_at <= created_after:
            return "created_before"
    if filters.get("exclude_empty") and _is_empty_for_report(campaign, report_kind=report_kind):
        return "empty"
    return ""


def _is_empty_for_report(campaign: dict, *, report_kind: str) -> bool:
    if campaign_turn_count(campaign) == 0:
        return True
    if report_kind == "entity_guard":
        return not campaign_has_guard_data(campaign) or _looks_like_pipeline_without_bible(campaign)
    if report_kind == "world_bible":
        return not campaign_has_real_world_bible(campaign) or _looks_like_pipeline_without_bible(campaign)
    return False


def _looks_like_pipeline_without_bible(campaign: dict) -> bool:
    return "pipeline campaign" in _title(campaign).casefold() and not campaign_has_real_world_bible(campaign)


def _parse_created_after(value: Any) -> datetime | None:
    text = str(value or "").strip()
    return _parse_date(text) if text else None


def _latest_campaign_per_title(campaigns: list[dict]) -> tuple[list[dict], int]:
    latest: dict[str, tuple[int, datetime, dict]] = {}
    for index, campaign in enumerate(campaigns):
        title_key = _title(campaign).casefold()
        created = _parse_date(str(_meta(campaign).get("created_at") or "")) or datetime.fromtimestamp(0, tz=timezone.utc)
        current = latest.get(title_key)
        if current is None or (created, index) > (current[1], current[0]):
            latest[title_key] = (index, created, campaign)
    kept_ids = {id(row[2]) for row in latest.values()}
    return [campaign for campaign in campaigns if id(campaign) in kept_ids], max(0, len(campaigns) - len(kept_ids))


def _parse_date(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.fromisoformat(text + "T00:00:00")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _meta(campaign: dict) -> dict:
    return campaign.get("campaign_meta") if isinstance(campaign.get("campaign_meta"), dict) else {}


def _title(campaign: dict) -> str:
    return str(_meta(campaign).get("title") or "")
