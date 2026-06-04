# Progression Architecture

Progression beschreibt Level, Skills, Klassen, Manifestationen und andere dauerhafte Charakterentwicklung.

## Aktuelle Bausteine

- Backend-State in Campaign JSON
- Progression-/Canon-Gate-Logik in `app/services/state_engine.py`
- Turn-Orchestration in `app/services/turn_engine.py`
- Explizite Turn-Ports in `app/services/turn/dependencies.py`:
  `TurnProgressionDependencies`, `TurnCodexDependencies`,
  `TurnPacingDependencies` und `TurnAttributeDependencies`
- Checks: `scripts/check_progression_canon_gate.py`, `scripts/check_progression_system.py`
- UI-Darstellung ueber Character Drawers und Timeline-Patches

## Regeln

- Narrator-Text allein darf keine versteckte Progression sein.
- Strukturierte Progression braucht Canon/Patch-State.
- Low-confidence Extractor-Ergebnisse duerfen nicht committed werden.
- Tests muessen Fake Extractor/Narrator verwenden.

## Refactoring-Ziel

Progression sollte weiter aus `state_engine.py` in eigene, testbare Service-Module
extrahiert werden, ohne Turn-Record- oder Campaign-JSON-Shape zu brechen. Die
Turn-Seite ist dafuer vorbereitet: Progression-/Skill-Events, Codex-Trigger,
Pacing/Timing und Attribute-Meta werden bereits ueber explizite Ports verdrahtet.
