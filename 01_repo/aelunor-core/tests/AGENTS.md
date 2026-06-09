# AGENTS.md — Tests

Bereichsregeln fuer `01_repo/aelunor-core/tests/`. Ergaenzt die Root-`AGENTS.md` (nicht ersetzen).

- Pytest laeuft aus `01_repo/aelunor-core/`. Layout: `tests/unit/` (89 Dateien), `tests/integration/` (3 Smoke-Tests). `conftest.py` setzt `sys.path`.
- Offline-Pflicht: KEINE echten Ollama-/LLM-/Netzwerk-Calls. Fake Narrator, Stubs oder injizierte Ports (`app/services/turn/dependencies.py`) verwenden.
- Kein Docker fuer normale Tests.
- Nur temporaere Daten (tempdir / In-Memory). `.runtime/`, `.runtime-verify/`, `07_runtime/` NIE beschreiben oder als Fixture nutzen.
- Bei Turn-/Canon-/State-Aenderungen pruefen: Phase, Turn-Zaehler, Timeline, aktiver Turn-Status, Claims, State vor/nach Reload.
- Ausgaben cappen: `python -m pytest tests -q > .agent_tmp/pytest.txt 2>&1`, dann `python ../../.agent_scripts/compact_test_output.py .agent_tmp/pytest.txt`. Keine vollen Logs in Antworten.
- Neue Logik moeglichst mit Test absichern; Bugfix -> Regressionstest, wenn der Aufwand vertretbar ist.
- UI-Tests laufen separat unter Vitest (`cd ui; npm run test`), nicht via pytest.
- Public Contracts respektieren: Campaign-JSON-Shape, Turn-Record, Setup-Catalog. Shape-Aenderung nur mit Versionierung.
