#!/usr/bin/env python3
"""Extract only error/warning lines from a (possibly huge) log file.

Reads a log file and prints just the relevant error/warning/traceback lines
with line numbers and a hard cap. Use this instead of dumping a whole log into
an agent's context.

Usage:
    python .agent_scripts/scan_errors.py <logfile> [--max N] [--ctx N]

    --max  max number of matching lines to print (default 80)
    --ctx  lines of context to include around each match (default 0)

Stdlib only; safe on Windows and POSIX.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PAT = re.compile(
    r"(error|traceback|exception|fail(ed|ure)?|assert|warning|fatal|panic|"
    r"unhandled|cannot |not found|refused|\bE\d{2,}\b|^\s*File \")",
    re.IGNORECASE,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("logfile")
    ap.add_argument("--max", type=int, default=80)
    ap.add_argument("--ctx", type=int, default=0)
    args = ap.parse_args()

    path = Path(args.logfile)
    if not path.exists():
        print(f"[scan_errors] file not found: {path}", file=sys.stderr)
        return 2

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    keep_idx: list[int] = []
    seen: set[int] = set()
    for i, line in enumerate(lines):
        if PAT.search(line):
            lo = max(0, i - args.ctx)
            hi = min(len(lines), i + args.ctx + 1)
            for j in range(lo, hi):
                if j not in seen:
                    seen.add(j)
                    keep_idx.append(j)

    keep_idx.sort()
    total = len(keep_idx)
    for j in keep_idx[:args.max]:
        print(f"{j + 1:>6}: {lines[j][:500]}")
    shown = min(total, args.max)
    print(f"--- {shown}/{total} matching lines ({len(lines)} lines scanned) ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
