# World Generation

World Generation entsteht derzeit aus Setup-Antworten, Fallback-Logik und optionalen LLM-Aufrufen.

## Aktive Quellen

- `app/setup_catalog.json`
- `app/services/setup_service.py`
- `app/services/state_engine.py`
- Welt-Setup im v1-Setup-Overlay

## Generierte Bereiche

- Weltzusammenfassung
- Elemente und Element-Relationen
- Races und Beast Types
- Codex-/World-Info-Grundlagen

## Testregeln

- Keine echten LLM-Aufrufe in automatisierten Tests.
- Fallbacks muessen deterministisch sein.
- Ergebnis muss reload-sicher normalisiert werden.
