# Technical Debt Register

Stand: 2026-06-04

## Reduzierte Schulden

- Root- und Core-README beschreiben jetzt den aktuellen v1/FastAPI/Docker/Test-Stand.
- `02_docs/` hat einen Index und erste code-backed Architektur-/UX-Dokumente statt reiner Ueberschriften.
- v1-Designsystem wurde zuletzt in eigene Token-/Layout-Dateien ausgelagert.
- Backend-Kontext-READMEs existieren fuer `app/`, `services/`, `routers/`, `tests/` und `scripts/`.
- `state_engine.EXPORTED_SYMBOLS` ist auf die echte Public-Fassade begrenzt; `runtime_symbols()` ist von der alten breiten Fassade auf eine begrenzte interne Uebergangsbruecke reduziert.
- `check_progression_canon_gate.py`, `check_element_system.py` und `check_codex_system.py` laufen offline und gruen.

## Hohe Prioritaet

| Bereich | Problem | Empfohlene Richtung |
| --- | --- | --- |
| `app/services/state_engine.py` | Sehr grosser Monolith mit ca. 10.5k Zeilen und mehreren Domains | Naechster Slice: Campaign Lifecycle / Persistence / View-Building extrahieren |
| `app/services/turn_engine.py` | Orchestrierung, LLM, Canon, Fehlerklassifikation vermischt | Narrator adapter, canon gate, extraction und retry policy trennen |
| `state_engine.runtime_symbols()` | Interne Uebergangsbruecke fuer Runtime-Factories und Turn-Wiring | Nach jedem Refactor-Slice verkleinern und nicht als Public API verwenden |
| `ui/src/shared/styles/globals.css` | Globale Regeln sehr breit | Neue Systeme in Tokens/Layout-Dateien halten und schrittweise alte Regeln reduzieren |
| Placeholder-Ordner | Viele leere Workspace-Bereiche ohne Inhalt | Nach Bestaetigung loeschen oder mit echten READMEs/Assets befuellen |

## Mittlere Prioritaet

- `CampaignWorkspace.tsx`, `CharacterDrawer.tsx`, `SetupWizardOverlay.tsx` weiter in kleinere Hooks/Presenter splitten.
- API-Contracts zwischen Backend und Frontend dokumentiert generieren oder zumindest synchron testen.
- Lint-Script fuer UI einfuehren, wenn Regeln abgestimmt sind.
- Pycache/Runtime-Logs aus dem Arbeitsbaum bereinigen, wenn keine laufenden Prozesse sie brauchen.

## Nicht anfassen ohne konkreten Scope

- `07_runtime/`: lokale Runtime-Daten.
- Historische Audits in `01_repo/aelunor-core/docs/`: nur mit Korrekturhinweis, nicht still ueberschreiben.
- `app/static/`: keine aktive UI-Arbeit; nur statische Assets und explizit angeforderte Kompatibilitaet.
