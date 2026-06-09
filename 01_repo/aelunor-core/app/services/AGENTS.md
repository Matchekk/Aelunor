# AGENTS.md — Services (`app/services/`)

Bereichsregeln fuer die Backend-Domain-Schicht. Ergaenzt Root-`AGENTS.md` und `app/AGENTS.md` (nicht ersetzen). Service-Landkarte und Refactoring-Reihenfolge stehen in `README.md`; hier nur handlungsleitende Regeln.

## Domain-Schicht

- `services/` ist die Domain-Schicht. Neue Fachlogik in passende Unterordner, nicht in `app/main.py` oder Router.
- `state_engine.py` ist aktive Kernlogik, aber nicht weiter als Monolith aufblasen; neue Logik in echte Zielmodule (`campaigns/`, `turn/`, `world/`, `state/`, ...).
- `state_engine.EXPORTED_SYMBOLS` bleibt klein (`public_turn`, `build_campaign_view`); private/Domain-Helper nicht wieder als breite Fassade exportieren. `runtime_symbols()` ist nur interne Uebergangsbruecke, keine Public API.
- `turn_engine.py` ist Orchestrierung; neue Turn-Abhaengigkeiten zuerst in `turn/dependencies.py` ueber die expliziten Ports modellieren, nicht `runtime_symbols()` oder `main.py` erweitern.

## Story-, Canon- und Game-Logic

- Kernloop schuetzen: Setup -> Claim -> Character Setup -> Play -> Turn -> Persist/Reload.
- Canon-State nicht willkuerlich ueberschreiben. Game-, Session-, Presence- und persistierte Daten klar trennen; Presence/SSE ist Live-Sync, nicht persistente Wahrheit.
- Narrator-/LLM-Ausgaben duerfen strukturellen Spielstatus nicht ungeprueft zerstoeren. Edge Cases bedenken: leere Party, fehlender Save, kaputte/alte Daten, abgebrochene LLM-Antwort.
- Campaign/World/Turn/Canon-State als Public Contracts behandeln.

## RAG-Vorbereitung

- RAG spaeter als eigenes kleines Modul unter `app/services/rag/` (oder aehnlich), nicht in `main.py`, `routers/` oder UI.
- Kein RAG in diesem Slice; Public-Contract-Stabilitaet hat Vorrang.

## Tests

- Kein echter Ollama-/LLM-Call in Tests oder Check-Scripts; Fake Narrator, Stubs oder injizierte Ports (`turn/dependencies.py`).
- Neue Service-Logik mit Unit-Tests unter `tests/unit/` absichern.
- Bei State-/Turn-Aenderungen pruefen: Reload, Phase, Turn-Zaehler, Timeline, aktiver Turn-Status, Claims.
