#!/usr/bin/env python3
"""Compact repo map for token-efficient agent sessions.

Prints a small, high-signal map of the repo: top-level layout (with code-file
counts), entry points, config files, test files, and the largest "key" source
modules. Skips node_modules, caches, build output, runtime data, the agent
scratch dir, and binary assets.

Usage:
    python .agent_scripts/repo_map.py [root] [--depth N] [--top N] [--max-bytes N]

Default root = repo root (the parent of this script's folder).
Stdlib only; safe on Windows and POSIX.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build",
    "release", ".vite", "coverage", "htmlcov", ".idea", ".vscode",
    ".runtime", ".runtime-verify", ".agent_tmp", ".tmp-check", "_tmp",
}
BIN_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".tif", ".tiff",
    ".mp3", ".wav", ".ogg", ".m4a", ".mp4", ".webm", ".mov",
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    ".pdf", ".zip", ".gz", ".7z", ".rar", ".exe", ".dll", ".bin", ".lock",
}
CONFIG_NAMES = {
    "package.json", "tsconfig.json", "vite.config.ts", "vite.config.js",
    "docker-compose.yml", "dockerfile", ".env.example", "benchmark.toml",
    "pyproject.toml", "pytest.ini", "setup.cfg", "conftest.py",
}
ENTRY_HINTS = {
    "main.py", "app.py", "__main__.py", "index.tsx", "index.ts",
    "main.tsx", "main.ts",
}
SRC_EXT = {".py", ".ts", ".tsx", ".js", ".jsx"}


def count_lines(path: Path) -> int:
    try:
        with open(path, "rb") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def is_test(rel_lower: str, name_lower: str) -> bool:
    return (
        name_lower == "conftest.py"
        or name_lower.startswith("test_")
        or name_lower.endswith("_test.py")
        or ".test." in name_lower
        or ".spec." in name_lower
        or "/tests/" in "/" + rel_lower
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=None)
    ap.add_argument("--depth", type=int, default=3)
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--max-bytes", type=int, default=18000)
    args = ap.parse_args()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent

    dirs: list[tuple[str, int]] = []
    entries: list[str] = []
    configs: list[str] = []
    tests: list[str] = []
    sources: list[tuple[int, str]] = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        rel = Path(dirpath).relative_to(root)
        parts = rel.parts
        depth = len(parts)
        if depth <= args.depth:
            code = [f for f in filenames if Path(f).suffix.lower() not in BIN_EXT]
            dirs.append((rel.as_posix() or ".", len(code)))
        for f in filenames:
            ext = Path(f).suffix.lower()
            if ext in BIN_EXT:
                continue
            name_lower = f.lower()
            relf = (rel / f).as_posix()
            rel_lower = relf.lower()
            if name_lower in CONFIG_NAMES or name_lower.startswith("requirements") or ext == ".toml":
                configs.append(relf)
            if name_lower in ENTRY_HINTS:
                entries.append(relf)
            if is_test(rel_lower, name_lower):
                tests.append(relf)
            elif ext in SRC_EXT:
                sources.append((count_lines(root / relf), relf))

    sources.sort(reverse=True)
    lines: list[str] = []
    lines.append(f"# Repo map: {root}")
    lines.append("")
    lines.append(f"## Directories (depth<={args.depth}, code-file counts)")
    for path, n in dirs[:80]:
        lines.append(f"  {n:>4}  {path}")
    lines.append("")
    lines.append("## Entry points")
    for p in sorted(set(entries))[:40]:
        lines.append(f"  {p}")
    lines.append("")
    lines.append("## Config files")
    for p in sorted(set(configs))[:60]:
        lines.append(f"  {p}")
    lines.append("")
    lines.append(f"## Test files ({len(tests)} total, first 40)")
    for p in sorted(set(tests))[:40]:
        lines.append(f"  {p}")
    lines.append("")
    lines.append(f"## Key modules (largest {args.top} source files by lines)")
    for n, p in sources[:args.top]:
        lines.append(f"  {n:>5}  {p}")

    out = "\n".join(lines)
    data = out.encode("utf-8")
    if len(data) > args.max_bytes:
        out = data[:args.max_bytes].decode("utf-8", "ignore") + "\n...[truncated]"
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
