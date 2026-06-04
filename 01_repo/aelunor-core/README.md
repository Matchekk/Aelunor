# Aelunor Core

Aktiver Code-Stack fuer Aelunor: FastAPI-Backend, React/Vite-v1-UI, Services, Tests und technische Checks.

## Kurzbeschreibung

Aelunor Core betreibt ein lokales Multiplayer-Story-RPG. Das Backend persistiert Kampagnen als JSON, stellt HTTP- und SSE-Endpunkte bereit und ruft optional Ollama fuer Narrator-/Extractor-Funktionen auf. Die React/Vite-v1-UI ist die aktive Produktoberflaeche unter `/v1`; `/` leitet dorthin weiter.

## Ordner

| Pfad | Zweck |
| --- | --- |
| `app/README.md` | Backend-Kontextkarte fuer Agents |
| `app/main.py` | App-Wiring, Runtime-Konfiguration, Router-Composition, kleine Public-Fassade |
| `app/routers/` | HTTP-Router fuer Campaigns, Claims, Setup, Turns, Boards, Context, Presence, Sheets |
| `app/services/` | Fachlogik fuer Kampagnen, Setup, Claims, Turns, State, Boards, Context, Presence |
| `app/helpers/` | Hilfslogik fuer Setup; Random Preview und Finalisierung sind aus der Setup-Fassade geteilt |
| `app/static/` | Statische Brand-/Icon-Assets ohne aktive Legacy-UI |
| `ui/` | React/Vite-v1-Frontend |
| `tests/unit/` | Service- und State-Unit-Tests |
| `tests/integration/` | Kernflow-/HTTP-Smoke-Tests |
| `scripts/` | Systemchecks, Longrun-Tools, Dev-Start/Stop-Skripte |
| `docs/` | Historische Audits und Ist-Analysen |

## Backend starten

Docker Compose:

```powershell
docker compose up -d --build
```

Lokaler Uvicorn-Run mit temporaerem Datenpfad:

```powershell
$env:DATA_DIR="$PWD\.runtime"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```

URLs:

- `http://localhost:8080/v1` fuer React/Vite-v1
- `http://localhost:8080` leitet auf `/v1` weiter
- `http://localhost:8080/api/llm/status` fuer Ollama-Status

## Frontend

```powershell
cd ui
npm install
npm run dev
npm run typecheck
npm run test
npm run build
```

`ui/package.json` definiert aktuell `dev`, `build`, `preview`, `typecheck` und `test`. Ein Lint-Script existiert nicht.

## Backend-Checks

```powershell
python -m pytest tests -q
python -m py_compile app/main.py
python scripts/check_progression_canon_gate.py
python scripts/check_codex_system.py
python scripts/check_element_system.py
```

Gezielt:

```powershell
python -m pytest tests/unit -q
python -m pytest tests/integration -q
```

## Environment

| Variable | Default | Zweck |
| --- | --- | --- |
| `DATA_DIR` | Docker: `/data` | Root fuer Campaign JSON und Legacy-State |
| `OLLAMA_URL` | Compose: `http://host.docker.internal:11434` | Ollama-Server |
| `OLLAMA_MODEL` | Compose: `gemma3:12b` | Modellname |
| `OLLAMA_TIMEOUT_SEC` | Compose: `300` | Request-Timeout |
| `OLLAMA_TEMPERATURE` | Compose: `0.6` | Sampling |
| `OLLAMA_NUM_CTX` | Compose: `8192` | Kontextfenster |
| `OLLAMA_SEED` | leer | Optionaler deterministischer Seed |

Automatisierte Tests duerfen keine echten Ollama-Aufrufe ausloesen. Nutze Fake Narrator, Stubs oder injizierte Dependencies.

## Architekturregeln

- Router bleiben duenne HTTP-Adapter.
- Fachlogik gehoert in `app/services/`.
- `app/main.py` bleibt Wiring/Composition.
- `state_engine.EXPORTED_SYMBOLS` bleibt auf echte Public-Fassade begrenzt: `public_turn`, `build_campaign_view`.
- `state_engine.runtime_symbols()` ist eine interne Uebergangsbruecke fuer bestehende Runtime-Factories und Turn-Wiring; keine neue Monolith-API.
- Neue Domain-Helfer direkt in Zielmodulen testen/importieren, z. B. `app/services/items/`, `characters/`, `setup/`, `llm/`, `world/`.
- JSON-State-Shape, Campaign-Dateien, Setup-Catalog-Struktur, Turn-Record-Format und UI-Erwartungen sind Public Contracts.
- `07_runtime/` nicht als Testfixture benutzen und nicht aus Tests beschreiben.
- UI-Arbeit gehoert in `ui/`; `app/static/` enthaelt keine aktive Legacy-UI mehr.

## Zentrale technische Schulden

1. `app/services/state_engine.py` ist mit ca. 10.5k Zeilen weiterhin der groesste Monolith. Der naechste sinnvolle Slice ist Campaign Lifecycle / Persistence / View-Building.
2. `app/services/turn_engine.py` mischt noch Narrator-Orchestrierung, LLM-Fehlerpfade, Patch-/Canon-Auswertung und Prompt-nahe Logik.
3. `ui/src/shared/styles/globals.css` enthaelt noch sehr viele globale Regeln. Neue Systeme sollten in eigene Token-/Layout-Dateien ausgelagert werden.
4. Lokale `__pycache__`-Artefakte und Runtime-Logs sind generiert; sie sollten nicht versioniert werden.

## Dokumentation

Aktuelle, uebergeordnete Produkt-/Architektur-Doku liegt unter `../../02_docs/`. Historische Audits in `docs/` bleiben als Zeitdokumente erhalten und sollten nicht als alleinige Wahrheit gelesen werden.

Fuer schnelle Agent-Orientierung:

- `app/README.md`
- `app/services/README.md`
- `app/routers/README.md`
- `tests/README.md`
- `scripts/README.md`
