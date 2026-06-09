# AGENTS.md — Backend (`app/`)

Bereichsregeln fuer das FastAPI-Backend. Ergaenzt die Root-`AGENTS.md` (nicht ersetzen). Architektur-Details und Runtime-Wiring stehen in `README.md`; hier nur handlungsleitende Regeln.

## Schichten (kurz)

- `main.py`: App-Wiring/Composition und kleine Public-Fassade. Keine Fachlogik.
- `routers/`: duenne HTTP-Adapter. Keine Fachlogik.
- `services/`: Domain- und Workflow-Logik (siehe `services/AGENTS.md`).
- `repositories/`: Persistenzadapter. `adapters/`: externe Systeme (z. B. Ollama).
- `schemas/`, `serializers/`, `dependencies/`: Schnittstellen und Wiring.
- `static/`: statische Brand-/Icon-Assets; keine aktive Legacy-UI.

## Guards

- Neue Fachlogik gehoert in `services/`, nicht in `main.py` oder `routers/`.
- Public Contracts schuetzen: HTTP-API, JSON-State-Shape, Campaign-Dateien, Setup-Catalog, Turn-Records, UI-Snapshot. Shape-Aenderungen nur versioniert.
- Tests und Check-Scripts duerfen keine echten Ollama-/LLM-Aufrufe ausloesen.
- Runtime-Daten (`.runtime/`, `.runtime-verify/`, `07_runtime/`) nie fuer Tests oder Experimente beschreiben.
- Vor groesseren Backend-Aenderungen `README.md` und ggf. `services/README.md` lesen.
