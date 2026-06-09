# RAG Foundation (`app/services/rag/`)

Deterministic, offline-testable core for later campaign-memory RAG. This
slice ships only local building blocks; nothing is wired into the turn
pipeline yet.

## Zweck

Eine deterministische Grundlage, die spaeter Langzeit-Erinnerungen (Kampagnen,
Chroniken, NPCs, Orte, Quests, fruehere Turns) gezielt in den Narrator-Kontext
bringen kann. In diesem Slice nur reine Datenmodelle, Chunking, lexical
Retrieval und ein bounded Context Builder.

## Nicht-Ziele (dieser Slice)

- Keine Vector-DB.
- Keine Embeddings / Embedding-API.
- Keine LLM-/Ollama-/HTTP-Aufrufe.
- Keine Router / API-Endpunkte.
- Keine Turn-Pipeline-Integration.
- Keine neue externe Dependency (nur stdlib).

## Daten, die spaeter hinein duerfen

Campaign summaries, Chronicle summaries, World facts, NPC facts, Location
facts, Quest facts, prior turn summaries, rules/lore snippets.

## Daten, die NICHT hinein duerfen

Secrets, `.env`-Inhalte, Runtime-Caches, raw logs, generierte Assets,
`node_modules`, build outputs, private lokale Ordner.

## Public Contract

Stabile, kleine Oberflaeche (siehe `__init__.py`):

- `RAGDocument` — Quelle: `id`, `campaign_id`, `source_type`, `text`,
  `metadata`, `salience`, `canonical`.
- `RAGChunk` — retrievable Slice mit `contextual_header` und `token_estimate`.
- `RetrievalQuery` — `text`, `campaign_id`, `entities`, `source_types`,
  `max_results`.
- `RetrievalResult` — `chunk`, `score`, `reasons`.
- `chunk_document(document, *, max_chars=900, overlap_chars=120)`
- `retrieve_chunks(query, chunks)`
- `build_rag_context(results, *, max_items=5, max_chars=2500)`
- `build_rag_documents_from_campaign_state(campaign_id, state, *, max_text_chars=4000)`
- `build_rag_document_id(campaign_id, source_type, stable_key)`

## Structured Memory Mapper

`document_mapping.py` (mit privaten Helfern in `_mapping_utils.py`) macht aus
strukturiertem Campaign-State `RAGDocument`-Objekte. Eingabe: `campaign_id` +
ein `state`-Mapping; Ausgabe: deterministische `RAGDocument`-Liste.

- Unterstuetzte `source_type`-Werte: `campaign_summary`, `world_summary`,
  `lore`, `location`, `npc`, `quest`, `turn_summary`.
- Rein stdlib, offline: keine File-/Runtime-/LLM-/HTTP-Zugriffe, kein Mutieren
  des Input-State, keine Zufalls-IDs, keine Timestamps.
- Robust gegen fehlende Keys, `None` und falsche Typen; unbekannte Shapes
  werden ignoriert statt zu crashen. Leere Dokumente entstehen nie.
- Mappt nur strukturierte Fakten/Summaries — keine Rohlogs, keine
  Runtime-Dateien. Text ist knapp gerendert und durch `max_text_chars`
  begrenzt. Metadata bleibt klein und serialisierbar.
- `campaign_id` ist Pflicht und fliesst in jede `RAGDocument.id` ein.

Noch kein Index-Service, keine API, keine Turn-Integration. Naechster Slice:
In-Memory Campaign-Memory-Index-Service.

## Chunking

Kleine Dokumente ergeben genau einen Chunk; leerer/whitespace Text ergibt
keine Chunks (nie ein Crash). Jeder Chunk traegt einen `contextual_header` mit
mindestens `campaign_id` und `source_type` plus vorhandenen Metadaten
(`title`/`name`/`location`/`entities`). Chunk-IDs sind deterministisch:
`f"{document.id}#chunk-{i}"`.

## Retrieval

Rein lexical und deterministisch:

- `campaign_id` ist ein harter Filter (kein Cross-Campaign-Leak).
- `source_types` filtert hart, wenn gesetzt.
- Exact entity/name match stark, Keyword-Overlap mittel, Header/Metadata
  leicht; `salience` und `canonical` nur als leichte, stabile Tie-Breaker.
- Score `<= 0` wird verworfen; Sortierung: hoeherer Score zuerst, bei
  Gleichstand stabil nach `chunk.id`.
- `max_results` wird strikt eingehalten.

## Context Budget

`build_rag_context` haelt `max_items` und `max_chars` strikt ein. Ein Item
kommt nur in den Block, wenn der vollstaendig geschlossene Block noch in
`max_chars` passt — es wird nie mitten im Tag abgeschnitten. Reihenfolge der
Results bleibt erhalten.

## Conflict Rule

RAG ist unterstuetzende Erinnerung. Bei Konflikt gewinnt der aktuelle
strukturierte Campaign-State. Der Context-Block enthaelt dazu einen
expliziten Hinweis.

## Spaetere Integrationsstelle (nicht in diesem Slice)

Die natuerliche Andockstelle ist die Turn-/Narrator-Kontextbildung
(`app/services/context_service.py` bzw. die Turn-Pipeline-Kontextaufbereitung).
Dort koennten retrievte Chunks als zusaetzlicher, klar markierter Kontextblock
eingespeist werden. Bewusst kein Code-Wiring in diesem Slice — nur diese
Dokumentation.
