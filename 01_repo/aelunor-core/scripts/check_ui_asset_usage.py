from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = [ROOT / "ui" / "src", ROOT / "app" / "static"]
SKIP_DIRS = {".git", "dist", "node_modules", "__pycache__", "07_runtime"}
TEXT_SUFFIXES = {".css", ".html", ".js", ".jsx", ".md", ".ts", ".tsx"}
APPROVED_DIRECT_REFERENCES = {
    ROOT / "ui" / "src" / "shared" / "styles" / "aelunor-ui-assets.css",
    ROOT / "ui" / "src" / "shared" / "ui" / "aelunorAssets.tsx",
    ROOT / "ui" / "src" / "shared" / "design" / "aelunor.asset-manifest.json",
    ROOT / "ui" / "src" / "shared" / "design" / "AELUNOR_ASSET_USAGE.md",
}


def iter_source_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
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


def report(findings: list[str], path: Path, text: str, pattern: re.Pattern[str], message: str) -> None:
    for match in pattern.finditer(text):
        rel = path.relative_to(ROOT)
        findings.append(f"{rel}:{line_number(text, match.start())}: {message}")


def main() -> int:
    findings: list[str] = []
    corner_background = re.compile(
        r"background(?:-image)?\s*:[^;{}]*panel-corner-[^;{}]*|"
        r"backgroundImage\s*[:=][^;\n{}]*panel-corner-",
        re.IGNORECASE,
    )
    corner_stretch = re.compile(r"panel-corner-[\s\S]{0,180}background-size\s*:\s*100%\s+100%", re.IGNORECASE)
    frame_stretch = re.compile(r"frame-(?:card|hero)\.png[\s\S]{0,180}background-size\s*:\s*100%\s+100%", re.IGNORECASE)
    direct_ui_kit = re.compile(r"['\"](?:/static)?/brand/ui-kit/[^'\"]+['\"]|url\(['\"]?(?:/static)?/brand/ui-kit/[^)'\"\s]+", re.IGNORECASE)
    wallpaper_in_card = re.compile(
        r"\.(?:card|button|modal|sidebar)[^{]{0,80}\{[^}]*brand/wallpapers/|"
        r"brand/wallpapers/[^;{}]*(?:card|button|modal|sidebar)",
        re.IGNORECASE,
    )
    decorative_img_missing_alt = re.compile(r"<img(?=[^>]*(?:brand/ui-kit|divider-arcane|frame-card|frame-hero|panel-corner))(?!(?:[^>]*\salt=['\"]{2}|[^>]*\saria-hidden=['\"]true['\"]))[^>]*>", re.IGNORECASE)

    for path in iter_source_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        if path.resolve() in APPROVED_DIRECT_REFERENCES:
            continue

        report(findings, path, text, corner_background, "corner assets must not be parent backgrounds; use AelunorPanelFrame")
        report(findings, path, text, corner_stretch, "corner assets must not be stretched with background-size 100% 100%")
        report(findings, path, text, frame_stretch, "frame-card/frame-hero must not be blindly stretched; use AelunorPanelFrame contain overlay")
        report(findings, path, text, wallpaper_in_card, "wallpapers are page-level backgrounds, not card/button/modal/sidebar assets")
        report(findings, path, text, decorative_img_missing_alt, "decorative UI-kit img needs alt=\"\" or aria-hidden")
        report(findings, path, text, direct_ui_kit, "direct UI-kit path outside approved wrappers/docs")

    if findings:
        print("Aelunor UI asset usage check failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("Aelunor UI asset usage check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
