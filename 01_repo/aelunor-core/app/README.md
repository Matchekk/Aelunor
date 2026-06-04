# Backend Context

Diese Datei ist der schnelle Einstieg fuer Agents im Backend. Sie beschreibt,
wo Code liegt und welche Grenzen aktuell gelten.

## Schichten

| Pfad | Aufgabe |
| --- | --- |
| `main.py` | FastAPI-App, Runtime-Konfiguration, Router-Wiring, kleine Public-Fassade |
| `routers/` | HTTP-Adapter; duerfen keine Fachlogik aufnehmen |
| `services/` | Domain- und Workflow-Logik |
| `dependencies/` | Factory-Funktionen fuer Router-/Service-Dependencies |
| `schemas/` | Pydantic-Request-/Response-Modelle |
| `serializers/` | Public-View-Builder, besonders Campaign-Snapshot |
| `repositories/` | Persistenzadapter |
| `adapters/` | externe Systeme, z. B. Ollama |
| `catalogs/`, `config/`, `prompts/` | statische Regeln, Schemas, Prompt-Konfiguration |
| `static/` | statische Brand-/Icon-Assets; keine aktive Legacy-UI |

## Runtime-Wiring

- Normaler State-Engine-Pfad: `state_engine.configure_dependencies(StateEngineDependencies(...))`.
- Nicht wieder einfuehren: `state_engine.configure(globals())` als normaler App-Pfad.
- `main.py` re-exportiert nur `state_engine.EXPORTED_SYMBOLS`.
- `state_engine.EXPORTED_SYMBOLS` bleibt klein: `public_turn`, `build_campaign_view`.
- `state_engine.runtime_symbols()` ist eine interne Uebergangsbruecke fuer
  bestehende Dependency-Factories und Turn-Wiring. Sie ist keine Public API.

## Wichtige Guards

- Keine neue Fachlogik in `main.py`.
- Router bleiben duenne Adapter.
- Tests und Check-Scripts duerfen keine echten Ollama-Aufrufe ausloesen.
- Campaign JSON, Turn-Records, Setup-Catalog und UI-Snapshot sind Public Contracts.
- `07_runtime/` nie fuer Tests oder Experimente beschreiben.

## Naechstliegende READMEs

- `services/README.md` fuer Domain-Landkarte.
- `routers/README.md` fuer HTTP-Wiring.
- `../tests/README.md` fuer Teststruktur.
- `../scripts/README.md` fuer technische Checks.
