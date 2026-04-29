# Performance and Storage Notes

Last updated: 2026-04-29

## Scope

This audit covered the active Aelunor stack under `01_repo/aelunor-core`, the active React/Vite UI under `01_repo/aelunor-core/ui`, shared brand assets under `03_brand`, and local runtime data under `07_runtime`.

The goal was to reduce committed/generated noise and shrink frontend assets without changing backend/API contracts or removing working features.

## Largest Local Storage Areas

Measured locally on 2026-04-29:

| Path | Size |
| --- | ---: |
| `07_runtime` | ~244.60 MB |
| `01_repo/aelunor-core/ui/node_modules` | ~88.72 MB |
| `01_repo/aelunor-core/.venv` | ~30.74 MB |
| `01_repo/aelunor-core/ui/dist` | ~28.14 MB |
| `03_brand` | ~16.42 MB |
| `01_repo/aelunor-core/app/static/brand` | ~11.84 MB |
| `01_repo/aelunor-core/ui/public/brand` | ~11.46 MB |
| `01_repo/aelunor-core/app/static/icons` | ~0.49 MB after optimization |
| `01_repo/aelunor-core/ui/public/icons` | ~0.49 MB after optimization |

The largest individual files were local runtime campaign JSON files under `07_runtime/campaigns` and `07_runtime/temp/automation_runs`, followed by dependency binaries from `ui/node_modules` and Python wheels in `.venv`.

## Git Hygiene Changes

The root `.gitignore` now ignores:

- Python coverage output: `.coverage`, `htmlcov/`
- Node/Vite build and cache output: `dist/`, `build/`, `.vite/`, `coverage/`
- package manager debug logs
- local runtime folders: `**/.runtime/`
- OS metadata files: `Thumbs.db`, `desktop.ini`
- the accidental root-level `/package-lock.json`

`01_repo/aelunor-core/.runtime/dev_v1_pids.json` was removed from the Git index because it is a generated local runtime PID file. The local file may still exist, but it should not be versioned.

## Asset Optimization

The production sidebar icons in these folders were resized from `1024x1024` PNGs to `256x256` optimized PNGs:

- `01_repo/aelunor-core/ui/public/icons`
- `01_repo/aelunor-core/app/static/icons`

Results per icon source copy:

| Asset | Before | After | Saved |
| --- | ---: | ---: | ---: |
| `campaign_icon_sidebar.png` | 1,802,624 B | 54,216 B | 97.0% |
| `characters_icon_png.png` | 1,455,456 B | 64,682 B | 95.6% |
| `codex_icon_sidebar.png` | 2,039,629 B | 65,943 B | 96.8% |
| `hub_icon_sidebar.png` | 1,837,956 B | 68,132 B | 96.3% |
| `inventory_icon_sidebar.png` | 1,967,495 B | 62,764 B | 96.8% |
| `quests_icon_sidebar.png` | 1,982,940 B | 66,766 B | 96.6% |
| `settings_icon_sidebar.png` | 1,949,732 B | 67,588 B | 96.5% |
| `world_icon_sidebar.png` | 1,599,993 B | 64,779 B | 96.0% |

This keeps enough resolution for the current sidebar display while removing roughly 14.1 MB per icon folder copy.

## Intentionally Kept

- `03_brand` originals remain untouched as brand source files.
- `Hub_Referenz.png` and copied wallpaper assets remain available because the current hub redesign uses the wallpaper direction as product UI reference.
- `ui/node_modules`, `.venv`, `ui/dist`, `.pytest_cache`, `__pycache__`, and runtime campaign data were not physically deleted in this pass. They are generated/local artifacts and should be cleaned only with explicit action-time confirmation.

## Cleanup Candidates

Safe candidates after confirmation:

- `01_repo/aelunor-core/ui/dist`
- `01_repo/aelunor-core/.pytest_cache`
- `01_repo/aelunor-core/**/__pycache__`
- `01_repo/aelunor-core/ui/node_modules/.vite`
- stale files under `07_runtime/temp`

Review before deleting:

- `07_runtime/campaigns` because these are local campaign saves.
- duplicated wallpaper copies in `app/static/brand/wallpapers` and `ui/public/brand/wallpapers`; the app currently references both `/static/brand/...` and `/brand/...` depending on serving mode.

## Frontend Bundle Notes

`ui/package.json` dependencies are small and expected for the current React/Vite app:

- `react`, `react-dom`
- `react-router-dom`
- `@tanstack/react-query`
- `zustand`

No dependency was removed. The larger bundle/storage contributors are public image assets and generated build output, not application dependencies.

## Low-Memory Development Notes

- Run UI commands from `01_repo/aelunor-core/ui` so root-level package artifacts are not created accidentally.
- Keep `07_runtime`, `.runtime`, `node_modules`, and `dist` ignored and out of commits.
- Rebuild `ui/dist` only when needed; do not commit it unless the deployment workflow explicitly requires checked-in build output.
- Keep future UI icons at 256px or 512px maximum unless they are displayed as large artwork.
- Keep design/reference images in `03_brand` or docs, not duplicated into productive public asset folders unless the app directly uses them.

