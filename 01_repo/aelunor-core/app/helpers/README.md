# Helpers Context

`app/helpers/` enthaelt schmale, service-nahe Hilfslogik. Helper duerfen
Workflows stuetzen, sollen aber keine Router- oder Persistenzlogik aufnehmen.

## Setup Helper Split

| Datei | Aufgabe |
| --- | --- |
| `setup_helpers.py` | Gemeinsame Setup-Dependency-Dataclass, Answer-Validation, Answer-Storage und Compatibility-Re-Exports |
| `setup_random.py` | Random-/AI-Preview-Antworten und Apply-Logik fuer World-/Character-Setup |
| `setup_finalize.py` | World-/Character-Summary-Building und Finalisierung des Setup-Flows |

`setup_helpers.py` bleibt bewusst als stabile Importoberflaeche bestehen, weil
`state_engine.py`, Tests und Services diese Namen weiterhin ueber die bestehende
Setup-Helper-Fassade verwenden.

## Regeln

- Keine echten Ollama-Calls in Tests; Random-Preview muss ueber injizierte
  `SetupHelperDependencies` fakebar bleiben.
- Keine Campaign-Persistenz in Helper schreiben.
- Setup-Shape und Response-Verhalten nur mit fokussierten Tests aendern.
