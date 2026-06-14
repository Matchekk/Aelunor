# Campaign Second Brain — Architecture & Integration Seam

Status: **MVP wired end-to-end behind feature flag `AELUNOR_SECOND_BRAIN`
(default off).** Seed → deterministic write hook → bounded retrieval are live
in the turn pipeline; a read-only debug API exposes counts. Offline latency +
token-budget guards are green in CI. The narrator-quality A/B benchmark (local
Ollama) and Ollama embeddings (Phase 7) are still pending. Branch
`feat/campaign-second-brain`, **not merged to main**.

## What it is (and is not)

The Second Brain is a **campaign-scoped world memory**: a persistent,
structured store of events, hard facts, entities (NPCs / places / items /
factions / concepts), relationships, and open threads. Its job is to feed the
narrator a *small, relevant* set of memory cards each turn so the narrator
needs **less** giant prompt context over a long campaign — not more.

It is **not** a second GM, not a free-form LLM memory, not a replacement for
`campaign.json`, and not a cross-campaign / global user memory.

Hard non-goals (enforced):
- No new **blocking** LLM call in the standard turn path.
- No Deferred / llama.cpp default; no external vector DB (Chroma/Qdrant).
- No cross-campaign mixing — every campaign has its own DB file *and* a
  `campaign_id` column as a second guard.
- The full campaign state is never sent to a Second-Brain LLM.

## Prototype inventory (`app/services/second_brain/`)

| Piece | File | Role |
|---|---|---|
| `SecondBrainStore` | `store.py` | SQLite persistence: `knowledge_node`, `knowledge_edge` (campaign-scoped). Path-injectable (`:memory:` or file). |
| `KnowledgeNode` / `KnowledgeEdge` | `models.py` | Unit of memory (id, campaign_id, kind, name, text, metadata, salience, canonical, embedding, updated_turn) + co-mention edges. |
| `EmbeddingPort` | `embeddings.py` | Swappable: `DeterministicHashEmbedding` (offline) + `OllamaEmbedding` (runtime stub). |
| `recall` | `recall.py` | Hybrid semantic + lexical + N-hop graph, reproducible ordering. |
| `consolidation` | `consolidation.py` | Salience decay by turn age + rolling `chronicle` node. |
| `SecondBrain` | `service.py` | Orchestrator: `ingest_state`, `remember_turn`, `recall`, `context_block`, `maintain`. |

`KnowledgeNode.kind` is the card vocabulary and already covers the required
types: `npc`, `location`, `quest`, `world_summary`, `lore`, `turn_summary`,
`chronicle`, plus new `event` / `fact` / `open_thread` / `item` / `faction`.
The MVP reuses this single-node model rather than inventing parallel tables.

## Integration seam (exact points in the live pipeline)

All wiring is gated by `AELUNOR_SECOND_BRAIN` and degrades to a no-op when off.

1. **Storage path** — `CAMPAIGNS_DIR/<campaign_id>/brain/brain.sqlite`, a
   sibling dir next to the existing single-file `CAMPAIGNS_DIR/<id>.json`
   (`app/core/paths.py:15`, `app/repositories/campaign_repository.py:34`).
2. **Feature flag** — `app/config/feature_flags.py` via
   `env_flag_enabled("AELUNOR_SECOND_BRAIN")` (idiomatic, default off).
3. **Write hook (deterministic)** — post-turn success window in
   `_create_turn_record_impl`, `turn_engine.py` ~1979–1984: after
   `campaign["state"] = state_after` and `normalize_npc_codex_state`, before
   `return turn_record`. Inputs available: `turn_record` (turn_id, patch,
   narrator_patch, extractor_patch, state_before, state_after, npc_updates),
   `actor`, `gm_text_display`.
4. **Retrieval / context section** — the `consistency_context` merge in
   `turn_engine.py` ~1417–1428, right next to the existing RAG
   `rag_prompt_block`. A new `[RELEVANT_CAMPAIGN_BRAIN] … [/…]` block is
   appended only when the flag is on.
5. **Dependency injection** — follow the `TurnRagDependencies` frozen-dataclass
   + `configure_*/getter` pattern (`app/services/turn/dependencies.py`) so the
   brain is an optional port; unconfigured ⇒ no behavior change.

## Patch / delta as the deterministic write source

`patch_payloads.blank_patch()` → `{meta, characters, items_new,
plotpoints_add, plotpoints_update, map_add_nodes, map_add_edges, events_add}`.
The merged `turn_record["patch"]` plus `state_after` give us deterministic
facts/entities **without any LLM call**:
- `items_new` → `item` entities.
- `plotpoints_add/update` → `open_thread` updates.
- `characters[slot]` deltas (bio/scene/conditions/…) → `fact`s + `npc`/actor
  entity updates; `scene_id` → place link.
- `events_add` + (player_action, gm_text) → one `event` node / memory card.
- `npc_updates` → `npc` entity upserts.

## The six questions

1. **Where does `brain.sqlite` live per campaign?**
   `CAMPAIGNS_DIR/<campaign_id>/brain/brain.sqlite` — one DB file per campaign,
   never a shared/global file. Dir created lazily on first write.
2. **How is the brain initialized?**
   Lazily, only when the flag is on. On first open the schema (incl.
   `brain_meta` with `schema_version`) is created. First-run **seed** (Phase 3)
   deterministically mirrors existing setup/world/scene/character/NPC/item/
   plotpoint data — no LLM, schema stays in code.
3. **When is it written?**
   In the post-turn success window (deterministic), and once at seed time.
   No write on the read/retrieval path.
4. **When is it retrieved?**
   Once per turn, just before the narrator call, to build the bounded
   `RELEVANT_CAMPAIGN_BRAIN` section. Read-only.
5. **What happens on errors?**
   Brain failures are caught, logged, and swallowed — **the turn always stays
   valid**. A corrupt/unopenable brain disables the section for that turn; no
   rollback, no `campaign.json` corruption. Failures are counted in
   `brain_meta.failed_jobs` for the debug API.
6. **What is never dumped into the narrator prompt?**
   Raw JSONL/state dumps, full prior turns, long evidence blobs, whole prompts,
   embeddings, secrets/tokens, and any other campaign's data. Only ≤8–12 short
   cards within a hard 1200–2000 token budget, deduped against current state.

## Budgets & safety rails

- Deterministic write: target **< 250 ms**; retrieval: **< 100 ms**.
- `RELEVANT_CAMPAIGN_BRAIN`: ≤ 8–12 cards, **≤ 2000 tokens**, never cut
  mid-card.
- Stop/PARK if: save corruption, campaign mixing, > 2000 brain tokens without
  continuity gain, any new blocking LLM call, or 3 failed variants.

## Phase status

1. ✅ Architecture review + this doc (`78beab3`).
2. ✅ Per-campaign storage path + `brain_meta`/`SCHEMA_VERSION`, safe open (`78beab3`).
3. ✅ Deterministic first-run seed (`956e464`).
4. ✅ Deterministic post-turn write hook, wired in `turn_engine` finalize (`20f4117`).
5. ✅ Retrieval + `RELEVANT_CAMPAIGN_BRAIN` block, wired in `consistency_context` (`1094819`).
6. ◑ Benchmark: offline latency/token guards green in CI; **A/B/C/D LLM run pending local Ollama** (`fc3e36b`, see `docs/performance/second-brain-benchmark.md`).
7. ⏸ Ollama embedding backfill — deferred until Phase 6 LLM run confirms the integration is stable. Hash embedding stays the MVP.
8. ✅ Minimal read-only debug API `GET /api/campaigns/{id}/brain` (`67d8150`).
9. ✅ Docs + report (this update).

Modules: `models.py`, `store.py`, `locator.py`, `embeddings.py`, `ingest.py`,
`recall.py`, `consolidation.py`, `seed.py`, `write_hook.py`, `retrieval.py`,
`debug.py`, `service.py`. ~60 unit tests across
`tests/unit/test_second_brain_*.py`; full suite 807 passed.

## KEEP / PARK / REVERT (after local A/B benchmark)

**KEEP the foundation, flag default off. PARK the "enable by default" call.**
The local-Ollama A/B/C benchmark (gemma4:e4b, 6+6+10 turns) confirmed the
integration is safe (0 turn fails, no save corruption, no campaign mixing,
flag-off = no-op), latency-negligible (brain write ≤60 ms, retrieval <1 ms),
and — after optimization — cheap (block ≈ +390 narrator prompt tokens, down
from +889; DB open-thread bloat capped 30 → 7). But the **continuity benefit is
unproven**: the benchmark's scene-neutral actions never reference past entities,
so recall value cannot manifest, and on short campaigns the seed duplicates
static state already in the context packet. Do **not** enable by default or
merge to main until a **plot-referencing long-campaign benchmark** shows
continuity ≥ stable with a lean prompt. Full numbers + iteration table:
`docs/performance/second-brain-benchmark.md`.

## Hidden Semantic Mentions — feasibility (analysis only, not built)

Idea: the narrator emits a small structured sidecar (≤8 items, each
`{surface, type, action, canonical_name, importance}`) so entity extraction is
more reliable, with **no visible `(Item)` tags** in `gm_text` and **no extra
LLM call**. Findings:

- Narrator response schema lives in `app/prompts.json:3-209`; the **root is
  strict (`additionalProperties: false`)** and enforced as an Ollama grammar
  (`app/services/llm/client.py` `call_ollama_schema`). Adding a field is a
  schema change with a **real format-fail risk on gemma4:e4b** (which already
  has intermittent JSON fails).
- Recommended shape: an optional top-level `semantic_metadata` (sibling to
  `story`/`patch`/`requests`, *not* a state mutation), or reuse `events_add`.
  Thread-through: `turn/output_normalization` → `turn/records.build_turn_record_payload`
  → `second_brain/write_hook.record_turn` (new entity/edge creation, like
  `items_new`/`npc_updates`).
- No-visible-tag instruction belongs in `TURN_RESPONSE_JSON_CONTRACT`
  (`app/prompts/system_prompts.py`) + the system prompt `WICHTIG` block.
- **Verdict:** feasible but riskier than the deterministic write path; ship as a
  separate, default-off flag `AELUNOR_SEMANTIC_MENTIONS` *after* the continuity
  benchmark, with acceptance gates: 0 schema-fail regression, 0 visible tag
  leaks, measurably better entity detection.
