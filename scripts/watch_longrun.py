import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGNS_DIR = ROOT / "data" / "campaigns"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def turn_count(campaign_id: str) -> int:
    path = CAMPAIGNS_DIR / f"{campaign_id}.json"
    if not path.exists():
        return 0
    return len((load_json(path).get("turns") or []))


def main() -> int:
    parser = argparse.ArgumentParser(description="Überwacht einen Longrun und erzeugt nach Abschluss einen Report.")
    parser.add_argument("campaign_id")
    parser.add_argument("--target-turns", type=int, default=300)
    parser.add_argument("--poll-seconds", type=int, default=30)
    args = parser.parse_args()

    last_count = -1
    while True:
        count = turn_count(args.campaign_id)
        if count != last_count:
            print(json.dumps({"campaign_id": args.campaign_id, "turn_count": count}, ensure_ascii=False))
            last_count = count
        if count >= args.target_turns:
            break
        time.sleep(max(5, args.poll_seconds))

    result = subprocess.run(
        ["python", str(ROOT / "scripts" / "report_longrun.py"), args.campaign_id],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
