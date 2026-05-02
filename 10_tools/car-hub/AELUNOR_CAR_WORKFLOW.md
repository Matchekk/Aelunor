# Aelunor CAR Workflow

Status: CAR hub prepared, WSL runtime partially blocked by Windows WSL service.

## Paths

- Aelunor root: `D:\Aelunor`
- Active repo: `D:\Aelunor\01_repo\aelunor-core`
- Active UI: `D:\Aelunor\01_repo\aelunor-core\ui`
- CAR hub: `D:\Aelunor\10_tools\car-hub`
- WSL hub path: `/mnt/d/Aelunor/10_tools/car-hub`

## Installed Pieces

- Windows Python: available.
- Windows CAR package: installed, but native Windows execution fails because CAR imports Unix `fcntl` in the web PTY layer.
- WSL distribution: `Ubuntu-24.04` installed.
- WSL CAR: `codex-autorunner 1.11.11` installed via `pipx`.
- WSL OpenCode: `opencode 1.14.31` installed via `npm install -g opencode-ai`.
- Docker Desktop: installed; WSL Docker integration still needs validation after WSL is healthy.

## Current Blocker

After package installation, Ubuntu-24.04 stopped starting with:

```text
Wsl/Service/CreateInstance/E_FAIL
```

The local process cannot restart `LxssManager` without elevated Windows rights. A Windows restart or an elevated service restart is likely required before `car doctor` and `car serve` can complete.

## Recovery Commands

Run these after Windows/WSL has recovered:

```powershell
wsl.exe --list --verbose
wsl.exe -d Ubuntu-24.04 -- bash -lc "id; python3 --version; car --version; opencode --version"
```

Then run the CAR checks:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "export PATH=`"`$PATH:/root/.local/bin`"; cd /mnt/d/Aelunor/10_tools/car-hub; car doctor"
```

Start the CAR Web UI:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "export PATH=`"`$PATH:/root/.local/bin`"; cd /mnt/d/Aelunor/10_tools/car-hub; car serve --host 0.0.0.0"
```

Open:

```text
http://localhost:8765
```

## Aelunor Operating Model

Use CAR for small missions, not broad autonomous rewrites.

Preferred loop:

1. Check `git status`.
2. Identify user-owned uncommitted changes.
3. Assign analysis/review roles before implementation.
4. Implement the smallest useful change.
5. Run checks.
6. Review diff.
7. Commit only when checks and review are green.

## Fixed Agent Roles

### Architect Agent

Use for architecture, API contracts, persistence, phase transitions, and refactor risk.

Primary areas:

- `app/services/state_engine.py`
- `app/services/turn_engine.py`
- `app/routers/`
- `app/schemas/`
- JSON campaign/state contracts

### UI/HUD Agent

Use for Hub, Play Screen, responsive behavior, story-first layout, and RPG-HUD polish.

Primary areas:

- `ui/src/`
- Hub components
- Play screen components
- shared styles and tokens

### QA/Test Agent

Use for smoke tests, fake LLMs, reload safety, claims, setup, turn regression, and no-network guards.

Primary areas:

- `tests/`
- `scripts/check_*.py`
- FastAPI TestClient tests

### Asset/Performance Agent

Use for image assets, mirrors, file sizes, bundle/storage risk, and `.gitignore` hygiene.

Primary areas:

- `03_brand/`
- `ui/public/brand/`
- `app/static/brand/`
- `02_docs/technical/PERFORMANCE_AND_STORAGE_NOTES.md`
- `02_docs/technical/UI_ASSET_KIT_NOTES.md`

### Reviewer Agent

Use before commit. It must return `GO` or `NO-GO`.

Review checklist:

- Mission fulfilled.
- No unrelated files changed.
- No runtime/cache/dist/node_modules committed.
- No `07_runtime` usage in tests.
- No real Ollama/LLM calls in tests.
- Checks match touched areas.

## Global Guardrails

- Do not use `D:\Aelunor\07_runtime` as a test fixture.
- Do not commit `.runtime`, `dist`, `node_modules`, `__pycache__`, `.pytest_cache`, or local saves.
- Do not change backend/API contracts unless explicitly requested.
- Do not expand legacy UI in `app/static/app.js` unless explicitly scoped.
- Put new React UI work under `D:\Aelunor\01_repo\aelunor-core\ui\src`.
- Keep Brand originals in `D:\Aelunor\03_brand` as source of truth.
- Do not mirror large source sheets into `app/static`.
- Do not add dependencies without a concrete reason.
- Prefer tests and audits before large refactors or feature expansion.

## Standard Checks

Backend:

```powershell
cd D:\Aelunor\01_repo\aelunor-core
python -m py_compile app/main.py
python -m pytest tests -q
python scripts/check_progression_canon_gate.py
python scripts/check_codex_system.py
python scripts/check_element_system.py
```

Frontend:

```powershell
cd D:\Aelunor\01_repo\aelunor-core\ui
npm run typecheck
npm run test
npm run build
```

