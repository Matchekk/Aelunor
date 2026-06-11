from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable
import json


ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = [ROOT / "ui" / "src", ROOT / "app" / "static"]
SKIP_DIRS = {".git", "dist", "node_modules", "__pycache__", "07_runtime"}
TEXT_SUFFIXES = {".css", ".html", ".js", ".jsx", ".md", ".ts", ".tsx"}
VALID_ROLES = {"background", "texture", "frame", "corner", "divider", "icon", "logo", "illustration", "animation", "unknown"}
CRITICAL_ROLES = {"background", "texture", "frame", "corner", "divider"}
APPROVED_DIRECT_REFERENCES = {
    ROOT / "ui" / "src" / "shared" / "styles" / "aelunor-ui-assets.css",
    ROOT / "ui" / "src" / "shared" / "ui" / "aelunorAssets.tsx",
    ROOT / "ui" / "src" / "shared" / "design" / "aelunor.asset-manifest.json",
    ROOT / "ui" / "src" / "shared" / "design" / "AELUNOR_ASSET_USAGE.md",
    ROOT / "ui" / "src" / "shared" / "design" / "AELUNOR_ASSET_REHAUL_VERIFICATION.md",
    ROOT / "ui" / "src" / "shared" / "design" / "AELUNOR_ASSET_PRODUCTION_PROTOCOL.md",
    ROOT / "ui" / "src" / "shared" / "design" / "AELUNOR_ASSET_REQUEST_TEMPLATE.md",
}

PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"background(?:-image)?\s*:[^;{}]*panel-corner-[^;{}]*|"
            r"backgroundImage\s*[:=][^;\n{}]*panel-corner-",
            re.IGNORECASE,
        ),
        "corner assets must not be parent backgrounds; use AelunorPanelFrame",
    ),
    (
        re.compile(
            r"background(?:-image)?\s*:[^;{}]*panel-edge-[^;{}]*|"
            r"backgroundImage\s*[:=][^;\n{}]*panel-edge-",
            re.IGNORECASE,
        ),
        "panel-edge assets must not be parent backgrounds; use AelunorPanelFrame edge overlays",
    ),
    (
        re.compile(r"panel-corner-[\s\S]{0,180}background-size\s*:\s*100%\s+100%", re.IGNORECASE),
        "corner assets must not be stretched with background-size 100% 100%",
    ),
    (
        re.compile(r"frame-(?:card|hero)\.png[\s\S]{0,180}background-size\s*:\s*100%\s+100%", re.IGNORECASE),
        "frame-card/frame-hero must not be blindly stretched; use AelunorPanelFrame contain overlay",
    ),
    (
        re.compile(
            r"\.(?:card|button|modal|sidebar)[^{]{0,80}\{[^}]*brand/wallpapers/|"
            r"brand/wallpapers/[^;{}]*(?:card|button|modal|sidebar)",
            re.IGNORECASE,
        ),
        "wallpapers are page-level backgrounds, not card/button/modal/sidebar assets",
    ),
    (
        re.compile(
            r"<img(?=[^>]*(?:brand/ui-kit|divider-arcane|frame-card|frame-hero|panel-corner|panel-edge))"
            r"(?!(?:[^>]*\salt=['\"]{2}|[^>]*\saria-hidden=['\"]true['\"]))[^>]*>",
            re.IGNORECASE,
        ),
        "decorative UI-kit img needs alt=\"\" or aria-hidden",
    ),
    (
        re.compile(r"<img(?=[^>]*panel-edge-)[^>]*>", re.IGNORECASE),
        "panel-edge assets must not be content images; use AelunorPanelFrame edge overlays",
    ),
    (
        re.compile(r"['\"](?:/static)?/brand/ui-kit/[^'\"]+['\"]|url\(['\"]?(?:/static)?/brand/ui-kit/[^)'\"\s]+", re.IGNORECASE),
        "direct UI-kit path outside approved wrappers/docs",
    ),
)

UI_SRC_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"z-index\s*:\s*(?:[4-9]\d|\d{3,})\s*;", re.IGNORECASE),
        "high numeric z-index detected; use --ael-z-* layer tokens",
    ),
)


def iter_source_files(scan_roots: Iterable[Path] = SCAN_ROOTS) -> list[Path]:
    files: list[Path] = []
    for root in scan_roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            files.append(path)
    return files


def line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def format_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def report(findings: list[str], root: Path, path: Path, text: str, pattern: re.Pattern[str], message: str) -> None:
    for match in pattern.finditer(text):
        findings.append(f"{format_path(path, root)}:{line_number(text, match.start())}: {message}")


def analyze_source_files(
    root: Path = ROOT,
    scan_roots: Iterable[Path] = SCAN_ROOTS,
    approved_direct_references: Iterable[Path] = APPROVED_DIRECT_REFERENCES,
) -> list[str]:
    findings: list[str] = []
    approved = {path.resolve() for path in approved_direct_references}

    for path in iter_source_files(scan_roots):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if path.resolve() in approved:
            continue

        for pattern, message in PATTERNS:
            report(findings, root, path, text, pattern, message)
        if root / "ui" / "src" in path.parents:
            for pattern, message in UI_SRC_PATTERNS:
                report(findings, root, path, text, pattern, message)

    return findings


def asset_path_exists(root: Path, asset_path: str) -> bool:
    if asset_path.startswith("/static/icons/"):
        return (root / "app" / "static" / "icons" / asset_path.removeprefix("/static/icons/")).exists()
    if asset_path.startswith("/static/brand/"):
        return (root / "app" / "static" / "brand" / asset_path.removeprefix("/static/brand/")).exists()
    if asset_path.startswith("/icons/"):
        return (root / "ui" / "public" / "icons" / asset_path.removeprefix("/icons/")).exists()
    if asset_path.startswith("/brand/"):
        return (root / "ui" / "public" / "brand" / asset_path.removeprefix("/brand/")).exists()
    return False


def validate_manifest(root: Path = ROOT) -> list[str]:
    findings: list[str] = []
    manifest_path = root / "ui" / "src" / "shared" / "design" / "aelunor.asset-manifest.json"
    if not manifest_path.exists():
        return [f"{format_path(manifest_path, root)}: manifest is missing"]

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"{format_path(manifest_path, root)}:{error.lineno}: invalid JSON: {error.msg}"]

    assets = manifest.get("assets")
    if not isinstance(assets, list):
        return [f"{format_path(manifest_path, root)}: assets must be a list"]

    for index, asset in enumerate(assets):
        label = asset.get("id") if isinstance(asset, dict) else f"asset[{index}]"
        if not isinstance(asset, dict):
            findings.append(f"{format_path(manifest_path, root)}: asset[{index}] must be an object")
            continue

        role = asset.get("role")
        path = asset.get("path")
        mirrored_path = asset.get("mirroredPath")
        allowed_usage = asset.get("allowedUsage")
        forbidden_usage = asset.get("forbiddenUsage")

        if role not in VALID_ROLES:
            findings.append(f"{format_path(manifest_path, root)}: {label} has invalid role {role!r}")
        if isinstance(path, str) and not asset_path_exists(root, path):
            findings.append(f"{format_path(manifest_path, root)}: {label} path does not exist: {path}")
        if isinstance(mirrored_path, str) and not asset_path_exists(root, mirrored_path):
            findings.append(f"{format_path(manifest_path, root)}: {label} mirroredPath does not exist: {mirrored_path}")
        if role in CRITICAL_ROLES:
            if not isinstance(allowed_usage, list) or not allowed_usage:
                findings.append(f"{format_path(manifest_path, root)}: {label} critical asset needs allowedUsage")
            if not isinstance(forbidden_usage, list) or not forbidden_usage:
                findings.append(f"{format_path(manifest_path, root)}: {label} critical asset needs forbiddenUsage")
        if str(label).startswith("panel-corner-") and role != "corner":
            findings.append(f"{format_path(manifest_path, root)}: {label} must use role corner")
        if str(label).startswith("wallpaper-") and role != "background":
            findings.append(f"{format_path(manifest_path, root)}: {label} must use role background")
        if label == "texture-arcane-noise" and role != "texture":
            findings.append(f"{format_path(manifest_path, root)}: texture-arcane-noise must use role texture")

    return findings


def run_checks(root: Path = ROOT) -> list[str]:
    return [*validate_manifest(root), *analyze_source_files(root=root)]


def main() -> int:
    findings = run_checks()

    if findings:
        print("Aelunor UI asset usage check failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("Aelunor UI asset usage check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
