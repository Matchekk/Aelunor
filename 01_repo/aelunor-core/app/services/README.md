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
| `turn_engine.py` | Turn-Pipeline-Orchestrierung, noch grosser Uebergangsbereich |
| `state_engine.py` | State-, Campaign-, Canon-, World- und Compatibility-Monolith |
| `boards_service.py`, `context_service.py`, `sheets_service.py` | Views und spielnahe Hilfsflows |
| `presence_service.py`, `live_state_service.py` | SSE-Tickets, Presence, Blocking Actions |
| `turn/` | Patch sanitize/validate/apply Module und Turn-Helfer |
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
  - die noch nicht voll entkoppelte Turn-Record-Pipeline.
- Diese Bridge nicht als neue Monolith-API verwenden.

## Refactoring-Reihenfolge

1. Campaign Lifecycle / Persistence / View-Building aus `state_engine.py` ziehen.
2. Turn-Pipeline weiter in LLM, Canon-Gate, Patch-Flow und Retry-Policy trennen.
3. Weitere World-/Skill-/Progression-Helfer in echte Zielmodule bewegen.
4. `runtime_symbols()` nach jedem Slice weiter verkleinern.

## Test-Hinweise

- Neue Service-Logik mit Unit-Tests unter `tests/unit/` absichern.
- Kein echter Ollama-Call in Tests oder Check-Scripts.
- Bei State-/Turn-Aenderungen Phase, Turn-Zaehler, Timeline, Claims und Reload pruefen.
