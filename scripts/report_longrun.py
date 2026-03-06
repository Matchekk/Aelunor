import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGNS_DIR = ROOT / "data" / "campaigns"
RUNS_DIR = ROOT / "data" / "automation_runs"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def summarize_campaign(campaign_id: str) -> Dict[str, Any]:
    campaign = load_json(CAMPAIGNS_DIR / f"{campaign_id}.json")
    rows = load_jsonl(RUNS_DIR / f"{campaign_id}.jsonl")
    turns = campaign.get("turns") or []
    state = campaign.get("state") or {}
    characters = (state.get("characters") or {})
    slot_id = next(iter(characters.keys()), "")
    char = characters.get(slot_id) or {}
    plotpoints = state.get("plotpoints") or []
    scenes = (state.get("scenes") or {})
    items = (state.get("items") or {})
    mode_counter = Counter()
    error_counter = Counter()
    request_counter = Counter()
    for row in rows:
        if row.get("step") == "turn_ok":
            mode_counter[str(row.get("mode") or "")] += 1
            for req in row.get("requests") or []:
                request_counter[str((req or {}).get("type") or "")] += 1
        elif row.get("step") == "turn_error":
            error_counter[str(row.get("error") or "")] += 1
    class_current = char.get("class_current") or {}
    skills = char.get("skills") or {}
    injuries = char.get("injuries") or []
    scars = char.get("scars") or []
    summary = {
        "campaign_id": campaign_id,
        "title": ((campaign.get("campaign_meta") or {}).get("title")),
        "turn_count": len(turns),
        "phase": ((state.get("meta") or {}).get("phase")),
        "resource_name": ((((state.get("world") or {}).get("settings") or {}).get("resource_name"))),
        "events_count": len(state.get("events") or []),
        "plotpoints_count": len(plotpoints),
        "plotpoints_done": sum(1 for p in plotpoints if p.get("status") == "done"),
        "class_name": class_current.get("name"),
        "class_rank": class_current.get("rank"),
        "class_level": class_current.get("level"),
        "skills_count": len(skills),
        "skill_names": sorted(str((v or {}).get("name") or k) for k, v in skills.items())[:30],
        "injuries_count": len(injuries),
        "scars_count": len(scars),
        "inventory_count": len(char.get("inventory") or []),
        "scene_id": char.get("scene_id"),
        "known_scenes": len(scenes),
        "known_items": len(items),
        "mode_usage": dict(mode_counter),
        "request_usage": dict(request_counter),
        "errors": dict(error_counter),
        "recent_story_excerpt": str((turns[-1] or {}).get("gm_text_display") or "")[:1500] if turns else "",
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Kompakter Report für einen Automations-Run")
    parser.add_argument("campaign_id")
    args = parser.parse_args()
    summary = summarize_campaign(args.campaign_id)
    out_path = RUNS_DIR / f"{args.campaign_id}_report.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report_path": str(out_path), **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
