# Aelunor

Aelunor ist ein lokales, browserbasiertes Multiplayer-Story-RPG mit KI-GM. Der aktive Stack liegt in `01_repo/aelunor-core/` und verbindet ein FastAPI-Backend, JSON-basierte Kampagnenpersistenz, eine React/Vite-v1-UI und optionale Ollama-Narrator-Aufrufe.

## Ziel

Der spielbare Kernflow ist:

1. Kampagne erstellen oder per Join-Code beitreten.
2. Welt-Setup und Charakter-Setup abschliessen.
3. Slots claimen.
4. Gemeinsam spielen.
5. Story-Turns erzeugen.
6. Canon/Patch-State konsistent halten.
7. Live-Updates per Presence/SSE anzeigen.

MVP-Stabilitaet hat Vorrang vor Feature-Ausbau. Neue UI-Arbeit gehoert in die React/Vite-v1-UI, nicht in die Legacy-UI.

## Tech Stack

- Backend: Python, FastAPI, Uvicorn
- Frontend: React 18, Vite, TypeScript, React Query, Zustand
- Persistence: JSON-Dateien unter `07_runtime/campaigns/`
- KI: Ollama-kompatible HTTP-Schnittstelle, in Tests immer gefaked oder gestubbt
- Tests: `pytest`, `vitest`, TypeScript `tsc`
- Packaging/Run: Docker Compose oder lokaler Uvicorn/Vite-Dev-Run

## Workspace-Struktur

| Pfad | Zweck |
| --- | --- |
| `01_repo/aelunor-core/` | Aktiver Code-Stack |
| `01_repo/aelunor-core/app/` | FastAPI-App, Router, Services, Legacy-UI, statische Assets |
| `01_repo/aelunor-core/ui/` | React/Vite-v1-Frontend |
| `01_repo/aelunor-core/tests/` | Backend-Unit- und Integrationstests |
| `01_repo/aelunor-core/scripts/` | Smoke-/Audit-/Wartungsskripte |
| `02_docs/` | Aktuelle Produkt-, Architektur- und UX-Dokumentation |
| `03_brand/` | Brand-Assets und Referenzbilder |
| `05_prompts/` | Prompt-Registry und zukuenftige Prompt-Bibliothek |
| `07_runtime/` | Lokale Runtime-Daten; nicht als Testfixture nutzen |
| `99_archive/` | Historische/obsolete Materialien |

Viele Ordner ausserhalb `01_repo/aelunor-core/`, `02_docs/`, `03_brand/`, `05_prompts/` und `07_runtime/` sind derzeit strukturierte Platzhalter. Sie sollten nur befuellt werden, wenn echte Inhalte entstehen.

## Setup

Aus `01_repo/aelunor-core/`:

```powershell
docker compose up -d --build
```

URLs:

- v1-UI: `http://localhost:8080/v1`
- Legacy-UI: `http://localhost:8080`
- LLM-Status: `http://localhost:8080/api/llm/status`

Lokaler Backend-Run ohne Docker:

```powershell
cd 01_repo/aelunor-core
$env:DATA_DIR="$PWD\.runtime"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```

Lokaler Frontend-Dev-Run:

```powershell
cd 01_repo/aelunor-core/ui
npm install
npm run dev
```

## Environment Variables

| Variable | Default | Zweck |
| --- | --- | --- |
| `DATA_DIR` | Docker: `/data`, lokal sonst app-abhaengig | Kampagnen- und Runtime-Persistenz |
| `OLLAMA_URL` | `http://host.docker.internal:11434` in Compose | Ollama-Endpunkt |
| `OLLAMA_MODEL` | `gemma3:12b` in Compose | Narrator-/Extractor-Modell |
| `OLLAMA_TIMEOUT_SEC` | `300` in Compose | LLM-Timeout |
| `OLLAMA_TEMPERATURE` | `0.6` in Compose | LLM-Sampling |
| `OLLAMA_NUM_CTX` | `8192` in Compose | Kontextfenster |
| `OLLAMA_SEED` | leer | Optionaler Seed |

## Checks

Aus `01_repo/aelunor-core/`:

```powershell
python -m pytest tests -q
python -m py_compile app/main.py
node --check app/static/app.js
python scripts/check_progression_canon_gate.py
python scripts/check_codex_system.py
python scripts/check_element_system.py
```

Aus `01_repo/aelunor-core/ui/`:

```powershell
npm run typecheck
npm run test
npm run build
```

Es gibt aktuell kein `npm run lint`.

## Architekturueberblick

- Router in `app/routers/` sind HTTP-Adapter.
- Fachlogik liegt in `app/services/`.
- `app/main.py` verdrahtet Runtime-Konfiguration, Router und Kompatibilitaets-Exports.
- `app/services/state_engine.py` und `app/services/turn_engine.py` enthalten noch grosse Altlasten und sind die wichtigsten Refactoring-Ziele.
- v1-Frontend ist feature-orientiert unter `ui/src/features/`, Shared Code unter `ui/src/shared/`.
- Backend-State bleibt Quelle der Wahrheit; UI darf keine parallele Campaign-/Claim-/Turn-Wahrheit einfuehren.

## Aktueller Feature-Stand

- Kampagne erstellen/be treten und lokal speichern
- Setup-Flow fuer Welt und Charaktere
- Slot-Claims und Spieler-Kontext
- Story-Turns inklusive Retry/Undo/Edit-Contracts
- Canon/Patch-State, Codex, Elemente und Progression-Pruefungen
- Presence/SSE fuer Live-Sync
- v1-UI mit Hub, Claim/Setup/Play, Timeline, Composer, RightRail, Drawers und Boards
- Legacy-UI bleibt aus Kompatibilitaetsgruenden vorhanden

## Bekannte Einschraenkungen

- `state_engine.py` ist ein sehr grosser Monolith und sollte schrittweise nach Domain-Bereichen zerlegt werden.
- `app/static/app.js` ist Legacy und sollte nicht erweitert werden.
- Viele Workspace-Ordner sind Platzhalter ohne produktiven Inhalt.
- `02_docs/` war lange nur als Skelett vorhanden; aktuelle Inhalte muessen weiter code-backed gepflegt werden.
- Push/Pull sollte nur mit sauberem Worktree erfolgen, da lokale Runtime-/Arbeitsdaten nicht vermischt werden duerfen.

## Naechste Schritte

1. `state_engine.py` in kleine Module fuer Elemente, Codex, Charakter-State, Patch-Anwendung und Normalisierung zerlegen.
2. `turn_engine.py` weiter von Prompt-/LLM-/Canon-Entscheidungen trennen.
3. Legacy-UI nur noch fuer Regressionen stabilisieren.
4. Backend-API-Contracts und v1-Frontend-Contracts aus einer dokumentierten Quelle ableiten.
5. Platzhalter-Ordner entweder mit echten Inhalten befuellen oder nach Bestaetigung entfernen.
