"""Inbox watcher: drop rough cutouts in, get clean PNGs out.

Watches ``inbox/`` (next to package.json). Every new PNG is refined with
refine_edges (``--bg auto``, automatic retry) and produces:

    inbox/<name>.clean.png     the cleaned asset
    inbox/<name>.compare.png   before/after sheet for a quick look

Usage:
    python scripts/refine_watch.py [--inbox DIR] [--once]

--once processes whatever is currently in the inbox and exits (used by tests
and CI); without it the watcher polls every 2 seconds until Ctrl+C.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import refine_edges


def is_pending(path: Path) -> bool:
    if path.suffix.lower() != ".png":
        return False
    if path.stem.endswith(".clean") or path.stem.endswith(".compare"):
        return False
    return not path.with_name(f"{path.stem}.clean.png").exists()


def is_stable(path: Path, snapshots: dict[Path, tuple[int, float]]) -> bool:
    """Only touch a file once its size/mtime stopped changing (copy finished)."""
    stat = path.stat()
    current = (stat.st_size, stat.st_mtime)
    previous = snapshots.get(path)
    snapshots[path] = current
    return previous == current


def process(path: Path) -> None:
    args = refine_edges.build_parser().parse_args(
        [str(path), "--bg", "auto", "--compare"]
    )
    try:
        refine_edges.refine(path, args)
    except SystemExit as error:
        print(f"[watch] skipped {path.name}: {error}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--inbox", type=Path, default=Path(__file__).resolve().parents[1] / "inbox")
    parser.add_argument("--once", action="store_true", help="process current files and exit")
    args = parser.parse_args()

    args.inbox.mkdir(parents=True, exist_ok=True)
    print(f"[watch] watching {args.inbox} (Ctrl+C to stop)")

    snapshots: dict[Path, tuple[int, float]] = {}
    while True:
        for path in sorted(args.inbox.glob("*.png")):
            if is_pending(path) and (args.once or is_stable(path, snapshots)):
                process(path)
        if args.once:
            return 0
        time.sleep(2)


if __name__ == "__main__":
    raise SystemExit(main())
