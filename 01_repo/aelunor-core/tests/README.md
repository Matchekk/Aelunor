# Tests Context

Backend-Tests liegen unter `tests/` und muessen offline laufen.

## Struktur

| Pfad | Inhalt |
| --- | --- |
| `unit/` | Service-, State-, Serializer- und Modulgrenzen-Tests |
| `integration/` | HTTP-/Core-Flow-Smoke-Tests mit Fake Narrator/LLM |

## Regeln

- Keine echten Ollama-/LLM-Aufrufe.
- Nur temporaere Datenpfade oder In-Memory-Daten nutzen.
- `07_runtime/` nie beschreiben oder als Fixture verwenden.
- Alte Monolith-Vertraege nicht wiederbeleben: private/domain Helper nicht in
  `state_engine.EXPORTED_SYMBOLS` erwarten.
- Patch-Pfade auf echte Zielmodule oder explizite Dependency-Ports setzen.

## Wichtige Tests

```powershell
python -m pytest tests -q --basetemp .pytest_tmp --cache-clear -o cache_dir=.pytest_cache_local
python -m pytest tests/unit -q
python -m pytest tests/integration -q
python -m pytest tests/unit/test_state_dependencies.py tests/unit/test_main_state_engine_config.py tests/unit/test_state_engine_reexports_after_service_extraction.py -q
python -m pytest tests/unit/test_turn_dependencies.py tests/unit/test_turn_engine_llm_ports.py tests/unit/test_turn_extraction_ports.py tests/unit/test_turn_progression_codex_ports.py tests/unit/test_turn_pacing_attribute_ports.py tests/unit/test_turn_engine_runtime_dependency_inventory.py -q
```

Bei State-/Turn-Aenderungen besonders pruefen:

- Phase,
- Turn-Zaehler,
- Timeline / aktive Turns,
- Claims,
- State vor/nach Reload,
- Canon-/Progression-Gate.

Turn-Port-Tests pruefen bewusst offline, dass LLM-, Extraction-/Canon-/NPC-,
Progression-/Skill-/Codex- und Pacing-/Attribute-Abhaengigkeiten ueber explizite
Ports laufen. Sie duerfen keine echten Ollama-/HTTP-Aufrufe ausloesen.
