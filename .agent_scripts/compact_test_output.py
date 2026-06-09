#!/usr/bin/env python3
"""Compress long pytest / vitest output to only the parts that matter.

Keeps: summary lines, FAILED/ERROR names, assertion messages, and traceback
ends. Drops the noisy bulk. Hard line + byte caps. Reads a file or stdin.

Usage:
    python .agent_scripts/compact_test_output.py <file> [--max N]
    <some command> | python .agent_scripts/compact_test_output.py -

Stdlib only; safe on Windows and POSIX.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

KEEP = re.compile(
    r"(=+ .*(passed|failed|error|skipped|warning).* =+|"
    r"^\d+ (passed|failed|error|skipped|xfailed|deselected|warning)|"
    r"^FAILED |^ERROR |^PASSED |short test summary|"
    r"AssertionError|^E\s|assert |"
    r"Test Files|Tests\s+\d|^\s*[✓✗×]|FAIL |"
    r"expected|received|"
    r"Traceback|^\S*Error:|^\s+File \")",
    re.IGNORECASE,
)
SUMMARY = re.compile(
    r"(=+ .*(passed|failed|error).* =+|^\d+ (passed|failed|error|skipped))",
    re.IGNORECASE,
)


def read_source(src: str) -> str:
    if src in ("-", None):
        return sys.stdin.read()
    return Path(src).read_text(encoding="utf-8", errors="replace")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", default="-")
    ap.add_argument("--max", type=int, default=120)
    ap.add_argument("--max-bytes", type=int, default=12000)
    args = ap.parse_args()

    text = read_source(args.file)
    lines = text.splitlines()
    kept = [ln for ln in lines if KEEP.search(ln)]

    # Always surface final summary lines even if the cap would drop them.
    for s in (ln for ln in lines if SUMMARY.search(ln)):
        if s not in kept[-5:]:
            kept.append(s)

    kept = kept[:args.max]
    buf = "\n".join(kept)
    data = buf.encode("utf-8")
    if len(data) > args.max_bytes:
        buf = data[:args.max_bytes].decode("utf-8", "ignore") + "\n...[truncated]"
    print(buf if buf.strip() else "[compact_test_output] no notable lines found")
    print(f"--- compacted {len(lines)} -> {len(kept)} lines ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
