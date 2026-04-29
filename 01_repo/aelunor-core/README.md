# Aelunor Core

Aktiver Code-Stack fuer Aelunor: FastAPI-Backend, React/Vite-v1-UI, Legacy-UI, Services, Tests und technische Checks.

## Kurzbeschreibung

Aelunor Core betreibt ein lokales Multiplayer-Story-RPG. Das Backend persistiert Kampagnen als JSON, stellt HTTP- und SSE-Endpunkte bereit und ruft optional Ollama fuer Narrator-/Extractor-Funktionen auf. Die v1-UI ist die aktive Produktoberflaeche unter `/v1`; die Legacy-UI unter `/` bleibt nur fuer Kompatibilitaet bestehen.

## Ordner

| Pfad | Zweck |
| --- | --- |
| `app/main.py` | App-Wiring, Runtime-Konfiguration, Router-Composition, Kompatibilitaets-Exports |
| `app/routers/` | HTTP-Router fuer Campaigns, Claims, Setup, Turns, Boards, Context, Presence, Sheets |
| `app/services/` | Fachlogik fuer Kampagnen, Setup, Claims, Turns, State, Boards, Context, Presence |
| `app/helpers/` | Hilfslogik fuer Setup und Serialisierung |
| `app/static/` | Legacy-UI und statische Brand-Assets |
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
- `http://localhost:8080` fuer Legacy
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
node --check app/static/app.js
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
- JSON-State-Shape, Campaign-Dateien, Setup-Catalog-Struktur, Turn-Record-Format und UI-Erwartungen sind Public Contracts.
- `07_runtime/` nicht als Testfixture benutzen und nicht aus Tests beschreiben.
- Neue UI-Arbeit gehoert in `ui/`, nicht in `app/static/`.

## Zentrale technische Schulden

1. `app/services/state_engine.py` ist mit Abstand der groesste Monolith. Zerlegung sollte zuerst reine, testbare Teilbereiche extrahieren: Element-System, Codex, Character-State, Patch-Normalisierung, State-Migration.
2. `app/services/turn_engine.py` mischt noch Narrator-Orchestrierung, LLM-Fehlerpfade, Patch-/Canon-Auswertung und Prompt-nahe Logik.
3. `app/static/app.js` ist Legacy und sollte nur noch fuer Kompatibilitaets-Bugfixes angefasst werden.
4. `ui/src/shared/styles/globals.css` enthaelt noch sehr viele globale Regeln. Neue Systeme sollten in eigene Token-/Layout-Dateien ausgelagert werden.
5. Lokale `__pycache__`-Artefakte und Runtime-Logs sind generiert; sie sollten nicht versioniert werden.

## Dokumentation

Aktuelle, uebergeordnete Produkt-/Architektur-Doku liegt unter `../../02_docs/`. Historische Audits in `docs/` bleiben als Zeitdokumente erhalten und sollten nicht als alleinige Wahrheit gelesen werden.
