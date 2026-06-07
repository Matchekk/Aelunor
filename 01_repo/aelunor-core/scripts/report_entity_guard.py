from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

CORE_ROOT = Path(__file__).resolve().parents[1]
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

from app.core.paths import CAMPAIGNS_DIR


STATUSES = ("ok", "weak", "generic", "forbidden", "needs_review", "unknown")
PROBLEM_STATUSES = {"generic", "forbidden", "needs_review"}
STATUS_RANK = {"ok": 0, "weak": 1, "unknown": 2, "generic": 3, "needs_review": 4, "forbidden": 5}


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


def iter_turn_records(campaign: dict) -> list[dict]:
    return [turn for turn in (campaign.get("turns") or []) if isinstance(turn, dict)]


def extract_entity_guard_reports_from_turn(turn: dict) -> list[dict]:
    candidates = [
        turn.get("entity_guard"),
        ((turn.get("prompt_payload") or {}).get("entity_guard") if isinstance(turn.get("prompt_payload"), dict) else None),
        ((turn.get("debug") or {}).get("entity_guard") if isinstance(turn.get("debug"), dict) else None),
        ((turn.get("meta") or {}).get("entity_guard") if isinstance(turn.get("meta"), dict) else None),
    ]
    reports: list[dict] = []
    for candidate in candidates:
        reports.extend(_normalize_guard_report_shapes(candidate))
    return reports


def flatten_entity_guard_report(report: dict, *, campaign_meta: dict, turn: dict) -> list[dict]:
    rows: list[dict] = []
    campaign_id = str(campaign_meta.get("campaign_id") or "")
    title = str(campaign_meta.get("title") or "")
    turn_number = int(turn.get("turn_number", 0) or 0)
    turn_id = str(turn.get("turn_id") or "")
    for entry in (report.get("reports") or []):
        if not isinstance(entry, dict):
            continue
        score = entry.get("score", 0)
        try:
            score_int = int(score)
        except (TypeError, ValueError):
            score_int = 0
        rows.append(
            {
                "campaign_id": campaign_id,
                "campaign_title": title,
                "turn_number": turn_number,
                "turn_id": turn_id,
                "entity_type": str(entry.get("entity_type") or "unknown"),
                "name": str(entry.get("name") or ""),
                "status": _status(entry.get("status")),
                "score": score_int,
                "reasons": [str(reason) for reason in (entry.get("reasons") or []) if str(reason).strip()],
                "forbidden_terms_found": [str(term) for term in (entry.get("forbidden_terms_found") or []) if str(term).strip()],
                "avoid_terms_found": [str(term) for term in (entry.get("avoid_terms_found") or []) if str(term).strip()],
                "matched_roots": [str(term) for term in (entry.get("matched_roots") or []) if str(term).strip()],
                "source_path": str(entry.get("source_path") or ""),
                "source_paths": [str(path) for path in (entry.get("source_paths") or []) if str(path).strip()],
                "requires_review": bool(entry.get("requires_review")),
            }
        )
    return rows


def build_entity_guard_review(campaigns: list[dict]) -> dict:
    rows: list[dict] = []
    campaign_rows: list[dict] = []
    turns_scanned = 0
    guarded_turn_keys: set[tuple[str, int, str]] = set()
    for campaign in campaigns:
        meta = campaign.get("campaign_meta") if isinstance(campaign.get("campaign_meta"), dict) else {}
        campaign_id = str(meta.get("campaign_id") or "")
        campaign_turns = iter_turn_records(campaign)
        turns_scanned += len(campaign_turns)
        campaign_guarded_turns = 0
        campaign_reports: list[dict] = []
        for turn in campaign_turns:
            guard_reports = extract_entity_guard_reports_from_turn(turn)
            if guard_reports:
                campaign_guarded_turns += 1
                guarded_turn_keys.add((campaign_id, int(turn.get("turn_number", 0) or 0), str(turn.get("turn_id") or "")))
            for report in guard_reports:
                flattened = flatten_entity_guard_report(report, campaign_meta=meta, turn=turn)
                rows.extend(flattened)
                campaign_reports.extend(flattened)
        campaign_rows.append(_campaign_breakdown_row(meta, len(campaign_turns), campaign_guarded_turns, campaign_reports))
    status_counts = Counter(row["status"] for row in rows)
    summary = {
        "campaigns_scanned": len(campaigns),
        "turns_scanned": turns_scanned,
        "turns_with_guard_data": len(guarded_turn_keys),
        "entities_assessed": len(rows),
        "status_distribution": {status: int(status_counts.get(status, 0)) for status in STATUSES},
        "average_score": _avg([row["score"] for row in rows]),
        "lowest_score": min((row["score"] for row in rows), default=None),
        "highest_score": max((row["score"] for row in rows), default=None),
    }
    return {
        "summary": summary,
        "by_entity_type": _by_entity_type(rows),
        "problem_names": _problem_names(rows),
        "worst_reports": sorted(rows, key=lambda row: (row["score"], -STATUS_RANK.get(row["status"], 0), row["name"]))[:100],
        "problem_terms": _problem_terms(rows),
        "campaigns": campaign_rows,
        "examples": [row for row in rows if row["status"] in PROBLEM_STATUSES][:20],
    }


def render_markdown_report(review: dict, *, limit: int = 50) -> str:
    summary = review.get("summary") or {}
    limit = max(1, int(limit or 50))
    lines = [
        "# Entity Guard Review",
        "",
        f"Campaigns scanned: {summary.get('campaigns_scanned', 0)}",
        f"Turns scanned: {summary.get('turns_scanned', 0)}",
        f"Turns with guard data: {summary.get('turns_with_guard_data', 0)}",
        f"Entities assessed: {summary.get('entities_assessed', 0)}",
        f"Average score: {_fmt_score(summary.get('average_score'))}",
        f"Lowest score: {_fmt_score(summary.get('lowest_score'))}",
        f"Highest score: {_fmt_score(summary.get('highest_score'))}",
        "",
        "## Status Distribution",
    ]
    distribution = summary.get("status_distribution") or {}
    lines.extend(f"{status}: {distribution.get(status, 0)}" for status in STATUSES)
    lines.extend(["", "## By Entity Type", "entity_type | total | ok | weak | generic | forbidden | needs_review | unknown | avg_score", "--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---:"])
    for row in sorted((review.get("by_entity_type") or {}).values(), key=lambda item: str(item.get("entity_type"))):
        lines.append(
            f"{row['entity_type']} | {row['total']} | {row.get('ok', 0)} | {row.get('weak', 0)} | {row.get('generic', 0)} | {row.get('forbidden', 0)} | {row.get('needs_review', 0)} | {row.get('unknown', 0)} | {_fmt_score(row.get('avg_score'))}"
        )
    lines.extend(["", "## Problem Names", "name | entity_type | count | worst_status | worst_score | example_campaign | example_turn", "--- | --- | ---: | --- | ---: | --- | ---"])
    for row in (review.get("problem_names") or [])[:limit]:
        lines.append(f"{row['name']} | {row['entity_type']} | {row['count']} | {row['worst_status']} | {row['worst_score']} | {row['example_campaign']} | {row['example_turn']}")
    lines.extend(["", "## Worst Reports", "score | status | entity_type | name | campaign_id | turn_number | reasons", "---: | --- | --- | --- | --- | ---: | ---"])
    for row in (review.get("worst_reports") or [])[:limit]:
        lines.append(f"{row['score']} | {row['status']} | {row['entity_type']} | {row['name']} | {row['campaign_id']} | {row['turn_number']} | {'; '.join(row.get('reasons') or [])[:240]}")
    lines.extend(["", "## Problem Terms", "term | count | examples", "--- | ---: | ---"])
    for row in (review.get("problem_terms") or [])[:limit]:
        lines.append(f"{row['term']} | {row['count']} | {', '.join(row.get('examples') or [])}")
    lines.extend(["", "## Campaign Breakdown", "campaign_id | title | turns_scanned | guarded_turns | total_entities | ok | weak | generic | forbidden | needs_review | unknown | avg_score", "--- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---:"])
    for row in review.get("campaigns") or []:
        lines.append(
            f"{row['campaign_id']} | {row['title']} | {row['turns_scanned']} | {row['guarded_turns']} | {row['total_entities']} | {row.get('ok', 0)} | {row.get('weak', 0)} | {row.get('generic', 0)} | {row.get('forbidden', 0)} | {row.get('needs_review', 0)} | {row.get('unknown', 0)} | {_fmt_score(row.get('avg_score'))}"
        )
    lines.extend(["", "## Examples"])
    for row in (review.get("examples") or [])[: min(limit, 12)]:
        paths = row.get("source_paths") or ([row.get("source_path")] if row.get("source_path") else [])
        lines.extend(
            [
                f"Campaign: {row['campaign_id']} ({row['campaign_title']})",
                f"Turn: {row['turn_number']}",
                f"Entity: {row['name']} ({row['entity_type']})",
                f"Status: {row['status']}, Score: {row['score']}",
                "Reasons:",
                *[f"- {reason}" for reason in (row.get("reasons") or [])[:3]],
                "Source Paths:",
                *[f"- {path}" for path in paths],
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Entity-Guard-Review ueber gespeicherte Campaign-Turns.")
    parser.add_argument("--campaign-id", default=None)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--out", default=None)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--min-status", default=None, choices=STATUSES)
    args = parser.parse_args()
    campaigns = [campaign for path in iter_campaign_files(args.campaign_id) if (campaign := load_campaign_json(path)) is not None]
    review = build_entity_guard_review(campaigns)
    if args.min_status:
        review = _filter_review_min_status(review, args.min_status)
    output = json.dumps(review, ensure_ascii=False, indent=2) + "\n" if args.as_json else render_markdown_report(review, limit=args.limit)
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


def _normalize_guard_report_shapes(candidate: Any) -> list[dict]:
    if not isinstance(candidate, dict):
        return []
    if isinstance(candidate.get("reports"), list):
        return [candidate]
    reports = []
    for key in ("narrator", "extractor", "merged"):
        value = candidate.get(key)
        if isinstance(value, dict) and isinstance(value.get("reports"), list):
            reports.append(value)
    return reports


def _campaign_breakdown_row(meta: dict, turns_scanned: int, guarded_turns: int, rows: list[dict]) -> dict:
    counts = Counter(row["status"] for row in rows)
    row = {
        "campaign_id": str(meta.get("campaign_id") or ""),
        "title": str(meta.get("title") or ""),
        "turns_scanned": turns_scanned,
        "guarded_turns": guarded_turns,
        "total_entities": len(rows),
        "avg_score": _avg([entry["score"] for entry in rows]),
    }
    row.update({status: int(counts.get(status, 0)) for status in STATUSES})
    return row


def _by_entity_type(rows: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["entity_type"]].append(row)
    output = {}
    for entity_type, entries in grouped.items():
        counts = Counter(entry["status"] for entry in entries)
        output[entity_type] = {
            "entity_type": entity_type,
            "total": len(entries),
            "avg_score": _avg([entry["score"] for entry in entries]),
            **{status: int(counts.get(status, 0)) for status in STATUSES},
        }
    return output


def _problem_names(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        if row["status"] in PROBLEM_STATUSES:
            grouped[(row["entity_type"], row["name"])].append(row)
    output = []
    for (entity_type, name), entries in grouped.items():
        worst = sorted(entries, key=lambda row: (row["score"], -STATUS_RANK.get(row["status"], 0)))[0]
        output.append(
            {
                "name": name,
                "entity_type": entity_type,
                "count": len(entries),
                "worst_status": worst["status"],
                "worst_score": worst["score"],
                "example_campaign": worst["campaign_id"],
                "example_turn": worst["turn_number"],
            }
        )
    return sorted(output, key=lambda row: (-row["count"], row["worst_score"], row["name"]))


def _problem_terms(rows: list[dict]) -> list[dict]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        for term in (row.get("forbidden_terms_found") or []) + (row.get("avoid_terms_found") or []):
            grouped[str(term)].append(f"{row['campaign_id']}#{row['turn_number']}:{row['name']}")
    return sorted(
        [{"term": term, "count": len(examples), "examples": examples[:5]} for term, examples in grouped.items()],
        key=lambda row: (-row["count"], row["term"]),
    )


def _filter_review_min_status(review: dict, min_status: str) -> dict:
    minimum = STATUS_RANK[min_status]
    filtered = dict(review)
    filtered["problem_names"] = [row for row in review.get("problem_names", []) if STATUS_RANK.get(row.get("worst_status"), 0) >= minimum]
    filtered["worst_reports"] = [row for row in review.get("worst_reports", []) if STATUS_RANK.get(row.get("status"), 0) >= minimum]
    filtered["examples"] = [row for row in review.get("examples", []) if STATUS_RANK.get(row.get("status"), 0) >= minimum]
    return filtered


def _status(value: Any) -> str:
    text = str(value or "unknown")
    return text if text in STATUSES else "unknown"


def _avg(values: Iterable[int]) -> Optional[float]:
    values = list(values)
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _fmt_score(value: Any) -> str:
    return "-" if value is None else str(value)


if __name__ == "__main__":
    raise SystemExit(main())
