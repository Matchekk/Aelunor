#!/usr/bin/env python3
"""Compact a (possibly huge) log file into a small head+tail excerpt.

Prints the first and last N lines of a log so an agent can grasp start and
end without ingesting the whole file. Collapses the omitted middle into a
single marker. Optionally drops blank/duplicate-adjacent lines first.

Usage:
    python .agent_scripts/compact_logs.py <logfile> [--head N] [--tail N] [--squeeze]

    --head     lines to keep from the start (default 40)
    --tail     lines to keep from the end (default 60)
    --squeeze  collapse runs of identical adjacent lines before slicing

Stdlib only; safe on Windows and POSIX. No secrets printed beyond log content.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

MAX_LINE = 500


def squeeze_adjacent(lines: list[str]) -> list[str]:
    out: list[str] = []
    prev = object()
    for line in lines:
        if line != prev:
            out.append(line)
            prev = line
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("logfile")
    ap.add_argument("--head", type=int, default=40)
    ap.add_argument("--tail", type=int, default=60)
    ap.add_argument("--squeeze", action="store_true")
    args = ap.parse_args()

    path = Path(args.logfile)
    if not path.exists():
        print(f"[compact_logs] file not found: {path}", file=sys.stderr)
        return 2

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if args.squeeze:
        lines = squeeze_adjacent(lines)

    total = len(lines)
    head, tail = max(0, args.head), max(0, args.tail)

    if total <= head + tail:
        shown = lines
        omitted = 0
    else:
        shown = lines[:head] + ["..."] + lines[total - tail:]
        omitted = total - head - tail

    for line in shown:
        print(line[:MAX_LINE])
    print(f"--- showed {min(total, head + tail)}/{total} lines, {omitted} omitted ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
