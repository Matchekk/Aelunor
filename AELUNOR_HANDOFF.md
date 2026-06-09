# AELUNOR_HANDOFF.md

Compact continuation context for agents. Read first, then `AGENTS.md` (rules). Update dated sections after substantial changes. Paths relative to repo root unless noted.

> Repo root = `D:\Projekte\Aelunor-main\Aelunor-main` (has `.git`, `AGENTS.md`). A session may open the parent `D:\Projekte\Aelunor-main`, which also holds the sibling worktree `Aelunor-push-worktree/` — ignore it. Active code = `01_repo/aelunor-core/`.

## Current Goal
- Durable: local UI-driven multiplayer story/RPG; stable architecture, clean campaign/claim/turn/canon/presence flows, story-first UX.
- In flight (2026-06-09): agent/token infra set up (this file, `.agent_scripts/`, `.agent_tmp/`, AGENTS.md token section). No specific feature task on record — *assumption:* set per session.

## Current Architecture
- Backend: FastAPI + Uvicorn (Py 3.13), JSON campaign persistence, HTTP + SSE, optional Ollama / Anthropic-Claude narrator. Entry `app/main.py` (~482, wiring only).
- Frontend: React 18 + Vite 5 + TS strict, base `/v1`. State: Zustand (settings/theme/presence) + TanStack Query. Entry `ui/src/main.tsx`.
- Layering: thin routers (9) -> services (15 + subdirs) -> state engine. `state_engine.py` (~67) facade; `EXPORTED_SYMBOLS = [public_turn, build_campaign_view]` only.
- `deepaelunor/` — 15-task offline agent benchmark (dae-001..015), scored via `benchmark.toml`.

## Important Files / Directories
- `01_repo/aelunor-core/`:
  - `app/main.py` (482) — app factory; `configure_dependencies(StateEngineDependencies(...))`.
  - `app/routers/*.py` (9): campaigns, setup, claim, turns, boards, context, presence, sheets.
  - `app/services/` (15): turn_service, `turn_engine.py` (~1645), `state_engine.py` (67), live_state_service, `llm/client.py`; subdirs `state/runtime_core.py` (~1629), `campaigns/`, `turn/dependencies.py` (ports).
  - `app/static/` — LEGACY UI, do not revive. `tests/` unit(89)+integration(3). `scripts/` 22+ checks.
  - `ui/src/` — features (play/boards/claim/setup/scenes/drawers/context/session), entities (campaign/settings/presence/theme), shared (ui/design/styles).
- `02_docs/` docs · `03_brand/` assets (no code) · `05_prompts/` · `10_tools/` (car-hub, unrelated).

## Core Data / State / Game Flow
- Campaign JSON keys: campaign_meta, players, claims, state, turns[], boards, setup, board_revisions, legacy_migration.
- Phases (`state.meta.phase`): lobby -> world_setup -> character_setup_open -> ready_to_start -> active.
- Loop: Setup(World Q/A) -> Claim(player_id->slot) -> Character Setup -> Play(Turns) -> Persist/Reload.
- Turn: HTTP create_turn -> turn_service -> `turn_engine.create_turn_record` -> LLM narrator -> patch (JSON delta) sanitize->validate->apply (fixed order) -> mutate -> save JSON -> SSE broadcast. Turn record carries patch + state_before/after + edit_history + retry_of_turn_id.
- Subsystem ports (`turn/dependencies.py`): LLM, Extraction(canon/NPC), Progression(+canon gate), Codex(lore), Pacing, Attribute.
- LLM: `ChatAdapter`; `LLM_PROVIDER`=auto|ollama|anthropic (default Ollama `gemma3:12b`; Claude fallback needs `ANTHROPIC_API_KEY`).
- Persistence: `DATA_DIR` (default `.runtime/`, tests=tempdir) -> `campaigns/<ID>.json`. Presence/SSE = live sync, not truth.

## UI / Theme / Asset Flow
- main.tsx -> AppRoot (ErrorBoundary > QueryProvider > ThemeProvider > AppWorkspace + BrowserRouter) -> RouteGate `/v1/*` (pages hub/campaigns/characters/world/quests/inventory/codex; workspaces claim/setup/play).
- Themes: 4 (arcane/tavern/glade/hybrid) via `data-theme` + `--aelunor-*`; settings persist localStorage `aelunorUserSettingsV1` (legacy isekai-* migrated).
- Assets: NEVER use `public/brand/ui-kit` paths directly — wrap via `AelunorPanelFrame`/`AelunorDivider`/`AelunorIconFrame`/`AelunorSceneBackground` (`ui/src/shared/ui/aelunorAssets.tsx`). Registry `aelunor.asset-manifest.json` (637) enforces allowed/forbidden usage; new patterns need `AELUNOR_ASSET_PRODUCTION_PROTOCOL.md` + manifest/test update. Decorative: aria-hidden + pointer-events:none. See `ui/AGENTS.md`.

## Known Constraints
- Routers thin; logic in services; `main.py` wiring only. `EXPORTED_SYMBOLS` stays {public_turn, build_campaign_view}; `runtime_symbols()` internal only; no `state_engine.configure(globals())`.
- Public contracts (Campaign JSON, Turn-Record, Setup-Catalog, UI snapshots) need versioning on shape change.
- Tests offline only, NO real Ollama (fakes/injection), temp data only, no Docker. Code file <= ~300 lines unless justified. `.ps1`/`.bat` = PowerShell 5.1. No secrets committed.

## Known Issues
- Runtime dirs: local default `DATA_DIR` = `01_repo/aelunor-core/.runtime/` (+ `.runtime-verify/`), both present. `07_runtime/` (repo root) is the Docker bind-mount data dir from `docker-compose.yml` (created on `docker compose up`; currently absent). `14_private/`, `99_archive/` = reserved gitignore guards (absent). None are stale.
- `runtime_core.py`/`turn_engine.py` (~1.6k each) large — don't force-split.
- Pre-existing uncommitted working-tree changes exist (asset manifest/docs; untracked app/static, ui/public, deepaelunor/) — not agent infra; leave them.

## Do-Not-Reread / Do-Not-Touch
- Skip: `node_modules/`, `.venv/`, `dist/`, `build/`, `.runtime*/`, `.pytest_cache/`, `.mypy_cache/`, binary assets, `Aelunor-push-worktree/`, `.agent_tmp/`.
- Don't touch: runtime data, `app/static/` legacy UI, `deepaelunor/tasks/*/tests/hidden_verifier.py` (hidden scoring), `_analysis_for_chatgpt/`, `_tmp/`, `reports/`.

## Useful Commands (from `01_repo/aelunor-core/`)
- Map (repo root): `python .agent_scripts/repo_map.py`
- Tests: `python -m pytest tests/unit -q` ; `tests/integration -q`. Compact: `... > .agent_tmp/p.txt 2>&1; python ../../.agent_scripts/compact_test_output.py .agent_tmp/p.txt`
- Errors in a log: `python ../../.agent_scripts/scan_errors.py .agent_tmp/out.txt`
- Checks: `python -m py_compile app/main.py`; `python scripts/check_progression_canon_gate.py` (+ check_codex_system / check_element_system); `python scripts/deepaelunor_validate.py`
- Backend: `$env:DATA_DIR="$PWD\.runtime"; python -m uvicorn app.main:app --host 127.0.0.1 --port 8080`
- UI: `cd ui; npm run dev|typecheck|test|build`. Win app: `scripts/build-windows.ps1`.

## Recent Test Status (2026-06-09)
- `python -m pytest tests -q` (from aelunor-core): **PASS** — 640 passed in ~253s. Py 3.13.13 / pytest 9.0.3.
- `npm run typecheck` (ui, `tsc --noEmit`): **PASS** — 0 errors.
- `npm run test` (ui, `vitest run`): **PASS** — 18 files / 53 tests.
- No `lint` script in `ui/package.json`. Raw logs: `.agent_tmp/{pytest,tsc,vitest}.{out,err}`.

## Next Recommended Steps
- Re-run the baseline (above) after dependency or core-state changes (pytest ~4 min; cap output to `.agent_tmp/`).
- Add `app/services/`/router/test context READMEs that root AGENTS.md references, if absent.
