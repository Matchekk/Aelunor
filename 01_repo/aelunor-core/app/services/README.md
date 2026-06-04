# Services Context

`app/services/` ist die Backend-Domain-Schicht. Neue Fachlogik gehoert hierhin
oder in passende Unterordner, nicht in `app/main.py` und nicht in Router.

## Aktive Service-Gruppen

| Pfad | Aufgabe |
| --- | --- |
| `campaign_service.py` | Campaign-Aktionen, Host-Flows, Intro/Meta/Delete |
| `setup_service.py` | World-/Character-Setup, Antworten, Random Preview, Finalisierung |
| `claim_service.py` | Slot-Claim, Takeover, Unclaim |
| `turn_service.py` | Turn-Endpoint-Guards und Fehlerabbildung |
| `turn_engine.py` | Turn-Pipeline-Orchestrierung mit expliziten Ports fuer LLM, Extraction, Progression/Codex und Pacing |
| `state_engine.py` | grosser State-, Canon-, World- und Compatibility-Kern mit reduzierter Public-Fassade |
| `boards_service.py`, `context_service.py`, `sheets_service.py` | Views und spielnahe Hilfsflows |
| `presence_service.py`, `live_state_service.py` | SSE-Tickets, Presence, Blocking Actions |
| `campaigns/` | Campaign Persistence, Lifecycle, Views, Party, Normalization und State-Shape-Helfer |
| `turn/` | Patch sanitize/validate/apply Module, Turn-Helfer und explizite Dependency-Ports |
| `world/` | Codex, Progression, Elemente, Combat, NPCs, Defaults, Text/Naming |
| `items/` | Inventory-/Equipment-Normalisierung |
| `characters/` | abgeleitete Werte und Character-Stats |
| `setup/` | Setup-Antworten und Setup-Flow-Helfer |
| `llm/` | JSON-Reparatur und LLM-nahe reine Hilfen |
| `state/` | explizite State-Engine-Dependency-Ports |

## Aktueller State-Engine-Stand

- `EXPORTED_SYMBOLS` ist nur Public-Fassade: `public_turn`, `build_campaign_view`.
- Domain-Helfer werden direkt aus Zielmodulen getestet/importiert.
- `runtime_symbols()` enthaelt nur noch eine begrenzte interne Bruecke fuer:
  - Router-/Service-Dependency-Factories,
  - Turn-Patch-Sanitizer/-Validator-Konfiguration,
  - verbleibende Legacy-Abhaengigkeiten der Turn-Record-Pipeline.
- Turn-Engine-Subsysteme sind bereits explizit modelliert:
  - `TurnLlmDependencies`
  - `TurnExtractionDependencies`
  - `TurnProgressionDependencies`
  - `TurnCodexDependencies`
  - `TurnPacingDependencies`
  - `TurnAttributeDependencies`
- Diese Bridge nicht als neue Monolith-API verwenden.

## Refactoring-Reihenfolge

1. `runtime_symbols()` anhand der expliziten Turn-Ports weiter reduzieren.
2. Verbleibende Turn-Materialization-, Patch-Sanitizer/-Validator- und Domain-Helper-Abhaengigkeiten entkoppeln.
3. Weitere World-/Skill-/Progression-Helfer in echte Zielmodule bewegen.
4. `turn_engine.py` erst nach gesicherten Ports in kleinere Orchestrierungsbausteine teilen.

## Test-Hinweise

- Neue Service-Logik mit Unit-Tests unter `tests/unit/` absichern.
- Kein echter Ollama-Call in Tests oder Check-Scripts.
- Bei State-/Turn-Aenderungen Phase, Turn-Zaehler, Timeline, Claims und Reload pruefen.
