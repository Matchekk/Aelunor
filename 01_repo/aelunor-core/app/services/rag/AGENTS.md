# AGENTS.md — RAG (`app/services/rag/`)

Bereichsregeln fuer die RAG-Fachlogik. Ergaenzt Root-`AGENTS.md`,
`app/AGENTS.md` und `app/services/AGENTS.md` (nicht ersetzen).

## Guards

- RAG-Fachlogik bleibt hier; kein RAG-Code in `main.py`, Routern oder UI.
- Keine Routerlogik / keine HTTP-Adapter in diesem Modul.
- Keine LLM-/Ollama-/HTTP-Aufrufe.
- Keine Vector-DB- oder Embedding-Abhaengigkeit ohne eigenen spaeteren Slice.
- Keine neue externe Dependency; nur Python-stdlib.
- `campaign_id` immer hart filtern (kein Cross-Campaign-Leak).
- Context Builder darf keine unbounded Bloecke erzeugen: `max_items` und
  `max_chars` strikt einhalten, nie mitten im Tag abschneiden.
- Public Surface (`__init__.py`) klein und stabil halten; kein Wildcard-Export.
- Keine Datei ueber 300 Zeilen.
- Structured Memory Mapper (`document_mapping.py`) darf den Input-State nie
  mutieren; `campaign_id` bleibt Pflicht. Keine raw logs, keine Runtime-Daten,
  keine File-/HTTP-Zugriffe; nur strukturierte Fakten -> `RAGDocument`.
- Memory Index Service (`memory_index.py`) bleibt in-memory und
  side-effect-free: keine globale mutable Registry, keine Persistenz/Cache
  ohne eigenen spaeteren Slice, kein Mutieren des Input-State. Retrieval immer
  ueber `index.campaign_id` scopen.

## Tests

- Tests muessen offline und deterministisch sein.
- Keine Runtime-Daten, keine Netzwerk-/LLM-Aufrufe, keine echten Kampagnen.
- Neue Logik unter `tests/unit/` absichern.
