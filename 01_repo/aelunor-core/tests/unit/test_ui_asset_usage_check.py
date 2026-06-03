from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_ui_asset_usage.py"
SPEC = importlib.util.spec_from_file_location("check_ui_asset_usage", SCRIPT_PATH)
assert SPEC is not None
check_ui_asset_usage = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(check_ui_asset_usage)


def write_fixture(root: Path, relative_path: str, content: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def analyze(root: Path) -> list[str]:
    return check_ui_asset_usage.analyze_source_files(
        root=root,
        scan_roots=[root / "ui" / "src"],
        approved_direct_references=[],
    )


def test_detects_corner_parent_background(tmp_path: Path) -> None:
    write_fixture(
        tmp_path,
        "ui/src/components/BadPanel.css",
        '.panel { background-image: url("/brand/ui-kit/panel-corner-tl.png"); }',
    )

    findings = analyze(tmp_path)

    assert any("corner assets must not be parent backgrounds" in finding for finding in findings)


def test_accepts_wrapper_usage_without_direct_asset_paths(tmp_path: Path) -> None:
    write_fixture(
        tmp_path,
        "ui/src/components/GoodPanel.tsx",
        """
        import { AelunorPanelFrame, AelunorDivider } from "../shared/ui/aelunorAssets";

        export function GoodPanel() {
          return (
            <AelunorPanelFrame className="v1-panel" variant="card">
              <h2>Story</h2>
              <AelunorDivider variant="small" />
            </AelunorPanelFrame>
          );
        }
        """,
    )

    assert analyze(tmp_path) == []


def test_allows_documented_hub_mini_map_preview(tmp_path: Path) -> None:
    write_fixture(
        tmp_path,
        "ui/src/features/session/sessionHub.css",
        """
        .hub-mini-map {
          background:
            linear-gradient(180deg, transparent, rgba(3, 7, 13, 0.42)),
            url("/static/brand/wallpapers/hub-reference.png") center / cover no-repeat;
        }
        """,
    )

    assert analyze(tmp_path) == []


def test_detects_high_numeric_z_index(tmp_path: Path) -> None:
    write_fixture(
        tmp_path,
        "ui/src/components/Floating.css",
        ".floating { position: absolute; z-index: 999; }",
    )

    findings = analyze(tmp_path)

    assert any("high numeric z-index" in finding for finding in findings)


def test_detects_panel_edge_parent_background(tmp_path: Path) -> None:
    write_fixture(
        tmp_path,
        "ui/src/components/BadEdge.css",
        '.panel { background-image: url("/brand/ui-kit/panel-edge-top.png"); }',
    )

    findings = analyze(tmp_path)

    assert any("panel-edge assets must not be parent backgrounds" in finding for finding in findings)


def test_detects_panel_edge_content_image(tmp_path: Path) -> None:
    write_fixture(
        tmp_path,
        "ui/src/components/BadEdge.tsx",
        '<img src="/brand/ui-kit/panel-edge-top.png" alt="" />',
    )

    findings = analyze(tmp_path)

    assert any("panel-edge assets must not be content images" in finding for finding in findings)


def test_missing_panel_edge_files_are_not_required(tmp_path: Path) -> None:
    write_fixture(
        tmp_path,
        "ui/src/components/NoEdgesYet.tsx",
        "export function NoEdgesYet() { return <div>No edge assets exist yet.</div>; }",
    )

    assert analyze(tmp_path) == []


def test_allows_panel_edge_documentation_context(tmp_path: Path) -> None:
    doc_path = write_fixture(
        tmp_path,
        "ui/src/shared/design/AELUNOR_ASSET_PRODUCTION_PROTOCOL.md",
        'Bad example: background-image: url("/brand/ui-kit/panel-edge-top.png");',
    )

    findings = check_ui_asset_usage.analyze_source_files(
        root=tmp_path,
        scan_roots=[tmp_path / "ui" / "src"],
        approved_direct_references=[doc_path],
    )

    assert findings == []
