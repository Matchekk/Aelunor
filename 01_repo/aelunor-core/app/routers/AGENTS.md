# AGENTS.md — Router (`app/routers/`)

Bereichsregeln fuer die HTTP-Adapter-Schicht. Ergaenzt Root-`AGENTS.md`, `app/AGENTS.md` und `app/services/AGENTS.md` (nicht ersetzen). Router-Landkarte und Dependency-Wiring stehen in `README.md`; hier nur handlungsleitende Regeln.

## Router bleiben duenne HTTP-Adapter

- Erlaubt im Router: Request-/Response-Mapping, HTTP-Status, Fehlerabbildung, Dependency-Aufloesung und Service-Aufruf.
- Keine Fachlogik im Router. Keine State-/Turn-/Canon-/RAG-/Retrieval-/Chunking-/Indexing-Logik.
- Keine direkten Dateisystem-/Runtime-Zugriffe im Router, ausser die bestehende Dependency-Struktur sieht es ausdruecklich vor.
- Keine direkten LLM-/Ollama-/Anthropic-/OpenAI-Aufrufe im Router.

## Fachlogik und Dependencies

- Neue Fachlogik gehoert in `app/services/` oder passende Unterordner, nicht in den Router.
- Neue Dependencies zuerst ueber bestehende Dependency-/Factory-Patterns (`app/dependencies/factories.py`, verdrahtet in `app/main.py`) pruefen, nicht neu im Router verdrahten.

## Public Contracts schuetzen

Router muessen stabil halten:

- HTTP-API,
- Request-/Response-Modelle,
- Campaign-Snapshot/UI-Erwartungen,
- Fehlerformat.

## Tests

- Bei neuen oder geaenderten Router-Flows passende Service-Tests bevorzugen.
- HTTP-Smoke-/Integrationstest nur, wenn API-Verhalten veraendert wird.
- Keine echten LLM-/Ollama-Aufrufe in Tests; Fake Narrator, Stubs oder injizierte Ports.

## Vorbereitung fuer spaetere RAG-Arbeit

- Router duerfen einen RAG-Service nur aufrufen.
- RAG-Fachlogik bleibt in `app/services/rag/` oder einem passenden Service-Modul.
- Context-Preview-/Reindex-/Memory-Endpunkte duerfen keine Retrieval-Implementierung enthalten.
