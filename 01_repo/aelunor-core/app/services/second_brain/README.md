# Campaign Second Brain (`app/services/second_brain/`) — Prototype

Exploratory evolution of the deterministic RAG foundation
(`app/services/rag/`) into a **persistent campaign knowledge system**. Where
the RAG slice rebuilds a read-only, in-memory, lexical context every turn,
the Second Brain *remembers*: it persists structured knowledge, recalls it
semantically, links it as a graph, and consolidates it over time.

> Status: **MVP wired into the live turn pipeline behind
> `AELUNOR_SECOND_BRAIN` (default off)**, branch `feat/campaign-second-brain`,
> not merged to main. Offline-first and deterministic by default so it stays
> fully unit-testable. See `docs/architecture/campaign-second-brain.md` for the
> integration seam and phase status, and
> `docs/performance/second-brain-benchmark.md` for the benchmark recipe.

## Live integration (flag-gated, default off)

| Hook | Module | Where it fires |
|---|---|---|
| First-run **seed** | `seed.py` | on the first turn (via the write hook), deterministic from existing campaign state |
| Post-turn **write** | `write_hook.maybe_record_turn` | `turn_engine` finalize block (~1979); event card + entities + edges + facts; never fails the turn |
| Pre-narrator **retrieval** | `retrieval.maybe_brain_context_block` | `turn_engine` `consistency_context` merge (~1425); bounded `[RELEVANT_CAMPAIGN_BRAIN]` block next to the RAG block |
| **Debug API** | `debug.brain_overview` + `routers/brain.py` | `GET /api/campaigns/{id}/brain` (counts/meta only) |
| **Storage** | `locator.open_campaign_brain` | `campaigns/<id>/brain/brain.sqlite`, per-campaign, safe-open |

With the flag off, all hooks are no-ops and turn behavior is unchanged.

## The four pillars

| Pillar | Where | What it does |
|---|---|---|
| **Persistence** | `store.py` | SQLite (`SecondBrainStore`). Campaign-scoped nodes + edges. `:memory:` for tests, a file under `DATA_DIR/second_brain` for runtime. First `sqlite3` use in the repo — stdlib only. |
| **Semantic recall** | `embeddings.py`, `recall.py` | Swappable `EmbeddingPort`. `DeterministicHashEmbedding` (offline feature hashing, process-stable via `hashlib`) for tests; `OllamaEmbedding` (e.g. `nomic-embed-text`) for runtime. Cosine similarity, brute-force over campaign-scoped rows (no vector-DB dependency yet). |
| **Entity graph** | `ingest.py`, `store.py` | `KnowledgeNode` / `KnowledgeEdge`. Co-mention edges derived deterministically from the existing RAG mapper output. Recall does N-hop neighbor expansion so related NPCs/locations/quests surface even when their text didn't match. |
| **Auto consolidation** | `consolidation.py` | `decay_salience` ages non-canonical nodes by turn distance; `consolidate_turns` folds old per-turn memories into a rolling `chronicle` node (optional local-LLM `SummarizerPort`, deterministic digest fallback). |

## Public surface (`__init__.py`)

- `SecondBrain` — orchestrator: `ingest_state`, `remember_turn`, `recall`,
  `context_block`, `maintain`.
- `SecondBrainStore` — persistence.
- `KnowledgeNode`, `KnowledgeEdge`, `RecallQuery`, `RecallResult` — models.
- `EmbeddingPort`, `DeterministicHashEmbedding`, `OllamaEmbedding`,
  `cosine_similarity` — embeddings.
- `build_knowledge_from_state`, `recall`, `decay_salience`,
  `consolidate_turns` — building blocks.

## Hybrid recall

`recall()` blends three deterministic signals and is reproducible:

1. **Semantic** — cosine(query embedding, node embedding); skipped cleanly
   when no embedder/vector is present.
2. **Lexical** — shared-token overlap; keeps recall working before
   embeddings exist and as a stable tie-breaker. Explicit entity hits score
   strongly.
3. **Graph** — one-hop (or N-hop) neighbors of the strongest hits get a
   boost. Blend: `0.65*semantic + 0.35*lexical`, then graph boost `0.25`.

Ordering: score desc → salience desc → canonical first → id (stable).

## Conflict rule (inherited from RAG)

The Second Brain is *supporting* memory. On any conflict the current
structured campaign state wins. `context_block()` renders a bounded
`[CAMPAIGN MEMORY]` block that says so explicitly and is never cut mid-item.

## What is real vs. stubbed in this slice

- **Real & tested:** SQLite persistence (incl. file reopen), deterministic
  embeddings + cosine, co-mention graph + neighbor expansion, salience
  decay, turn consolidation, campaign scoping, bounded context block.
- **Stubbed / runtime-only:** `OllamaEmbedding` (injected HTTP client, never
  called in tests), the LLM `SummarizerPort` (falls back to a deterministic
  digest).
- **Not wired yet:** Turn Engine integration (the RAG block still feeds the
  narrator), router/API endpoints, real embedding backfill, vector-DB
  backend.

## Next-loop candidates

1. Wire a real `OllamaEmbedding` (local model) + a one-off backfill that
   embeds existing nodes; benchmark recall quality vs. the lexical baseline.
2. Turn Engine integration behind a flag, A/B against the current RAG block
   (respect the turn-latency budget — see `docs/performance/`).
3. Richer graph: typed relations from the canon extractor, edge-weighted
   ranking, path explanations in `reasons`.
4. LLM-backed consolidation with the narrator-output-budget contract so the
   chronicle stays dense and bounded.
5. Persistence location/lifecycle: per-campaign DB under `DATA_DIR`, eviction
   policy, migration story.

## Run the tests

```powershell
cd D:\Aelunor\01_repo\aelunor-core
python -m pytest tests/unit/test_second_brain_service.py -q
```
