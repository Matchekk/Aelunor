# Technical Debt Register

Stand: 2026-04-29

## Reduzierte Schulden

- Root- und Core-README beschreiben jetzt den aktuellen v1/FastAPI/Docker/Test-Stand.
- `02_docs/` hat einen Index und erste code-backed Architektur-/UX-Dokumente statt reiner Ueberschriften.
- v1-Designsystem wurde zuletzt in eigene Token-/Layout-Dateien ausgelagert.

## Hohe Prioritaet

| Bereich | Problem | Empfohlene Richtung |
| --- | --- | --- |
| `app/services/state_engine.py` | Sehr grosser Monolith mit mehreren Domains | In kleine, reine Module splitten: elements, codex, character_state, patching, normalization |
| `app/services/turn_engine.py` | Orchestrierung, LLM, Canon, Fehlerklassifikation vermischt | Narrator adapter, canon gate, extraction und retry policy trennen |
| `app/static/app.js` | Legacy-UI gross und schwer testbar | Nur Bugfixes; keine neuen Features |
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
- Legacy-UI: keine Produktarbeit ausser gezielten Bugfixes.
