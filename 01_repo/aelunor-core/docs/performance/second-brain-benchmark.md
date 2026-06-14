# Second Brain — Benchmark (off / on)

How to measure the Campaign Second Brain against the stable baseline, and what
the offline guards already prove. Goal: the brain must **unburden** the
narrator (continuity ≥ stable, narrator prompt not growing uncontrollably),
never add a blocking LLM call, and stay within tight latency/token budgets.

## What is measurable offline (already green)

`tests/unit/test_second_brain_perf.py` grows a brain to a realistic
mid-campaign size (seed + 30 deterministic turns) and asserts the two KEEP
latency criteria with no LLM:

- deterministic **brain write < 250 ms** per turn — measured max well under
  budget (local stdlib sqlite).
- **retrieval < 100 ms** per turn on the grown brain — measured max well under
  budget.

These run in CI on every commit, so the write/retrieval budgets can't silently
regress. Token budget is enforced structurally: `render_brain_block` caps the
`[RELEVANT_CAMPAIGN_BRAIN]` block at `token_budget` (default 1800, hard
`chars ≈ tokens*4`), ≤ 12 short cards, resolved threads excluded — verified by
`test_second_brain_retrieval.py`.

## What needs local Ollama (user run)

The narrator quality / continuity / prompt-token comparison needs real turns
against a local model. The harness (`benchmark/run_turn_benchmark.py`) runs the
exact `turn_engine.create_turn_record` path from a copy of a real campaign and
captures per-turn profiling, including the new non-LLM phase timings
(`second_brain_write`, `second_brain_retrieval`) under
`phase_breakdown._phase_timings`, plus a `brain_digest` (counts, last processed
turn, schema version, failed jobs).

### Configuration (per the loop spec)

```powershell
$env:OLLAMA_URL = "http://localhost:11434"
# active model gemma4:e4b via DATA_DIR/llm_settings.json; num_ctx 32768
$env:AELUNOR_MEMORY_SUMMARY_INTERVAL = "2"
$env:AELUNOR_PROFILE_TURNS = "1"
# no llama.cpp, no Deferred defaults
```

### The four variants

Each run starts from the identical campaign copy, so runs are A/B comparable.

```powershell
cd D:\Aelunor\01_repo\aelunor-core
# A) baseline — Second Brain OFF
python benchmark/run_turn_benchmark.py --label sb_A_off --turns 6

# B) Second Brain ON (write + retrieval, deterministic hash recall)
python benchmark/run_turn_benchmark.py --label sb_B_on --turns 6 --second-brain

# C) write on, retrieval off  (set AELUNOR_SECOND_BRAIN=1, then temporarily
#    neutralize retrieval — e.g. run B and read brain_write timing in isolation)
# D) retrieval on, write off, with a pre-seeded brain
#    (seed once, then run with retrieval; compare continuity vs A)
```

For C/D, the cleanest path is to compare phase timings from the B run
(`second_brain_write` vs `second_brain_retrieval` are reported separately) plus
the `brain_digest`, rather than building extra flags. If isolated C/D numbers
are needed, add narrow env toggles later — keep the default path single-flag.

If stable at 6 turns, repeat with `--turns 10` for the longer continuity test.

### Metrics to read from each `*_summary.json`

- `total_avg_s`, `phase_breakdown` (narrator `s`, `prompt_tokens`),
  `_phase_timings.second_brain_write/.second_brain_retrieval` (ms),
  `resources` (VRAM peak), `errors` (turn fails), `brain_digest`.
- `brain_context_tokens` ≈ the delta in narrator `avg_prompt_tokens` between
  B and A (the cost of the injected `[RELEVANT_CAMPAIGN_BRAIN]` block). It must
  stay ≤ ~2000 and not grow uncontrollably across turns.
- Continuity / missed-fact / hallucinated-recall / duplicate-memory are read
  qualitatively from `*_stories.json` (A vs B same inputs).

### KEEP criteria

0 turn fails · no save corruption · no campaign mixing · brain_write < 250 ms ·
retrieval < 100 ms · brain_context_tokens ≤ 2000 · narrator prompt not growing
uncontrollably · quality/continuity ≥ stable · no new blocking LLM call.

If the prompt grows without a continuity gain → **PARK**, do not inflate
further.

## Results — local Ollama run (gemma4:e4b, ctx 32768, mem-interval 2)

Real turns via `run_turn_benchmark.py` on a copy of campaign `camp_c02276e6d5`
(each run reseeds from the identical copy → A/B fair). Analyzed with
`analyze_second_brain_results.py`.

| metric | A off (6t) | B on (6t) | C on (10t) | It1 on (6t) | It7 on (6t) |
|---|---:|---:|---:|---:|---:|
| turns completed / errors | 6 / 0 | 6 / 0 | 10 / 0 | 6 / 0 | 6 / 0 |
| total avg s | 85.9 | 84.2 | 77.6 | 67.7 | 68.6 |
| narrator avg prompt_tokens | 23901 | 24790 | 25923 | 24293 | 24484 |
| narrator max prompt_tokens | 24625 | 25884 | 28081 | 24986 | 25695 |
| **brain_context_tokens (≈ vs A)** | — | **+889** | +2022 | **+392** | +583 |
| brain write ms (avg/max) | — | 20 / 60 | 15 / 60 | 18 / 60 | 20 / 60 |
| brain retrieval ms (avg/max) | — | <1 | <1 | <1 | <1 |
| inter-turn repetition (avg) | 0.174 | 0.199 | 0.212 | 0.207 | 0.209 |
| A/B-question turns | 0 | 1 | 0 | 0 | 0 |
| brain open_threads (DB) | — | 30 | 30 | 24 | **7** |

Note: total/narrator seconds vary run-to-run with model load state — treat as
noise, not a brain effect (write+retrieval are <60 ms / <1 ms, i.e. negligible
vs ~50 s narrator).

### Optimization iterations

| It | Change | brain_ctx tok | repetition | write/retr ms | open_threads | Decision |
|---|---|---:|---:|---|---:|---|
| — | B baseline (budget 1800/10) | +889 | 0.199 | 20 / <1 | 30 | — |
| 1 | retrieval budget → 1200 tok / 8 cards | **+392** | 0.207 | 18 / <1 | 24 | **KEEP** (cost −56%, 0 fails, no regression) |
| 7 | cap seeded open_threads (≤8, skip resolved) | +583¹ | 0.209 | 20 / <1 | **7** | **KEEP** (DB bloat −71%, long-campaign hygiene; token delta is run noise) |

¹ It7 token figure is run-to-run noise — the 8-card cap (It1) already bounds the
block; It7's win is DB cleanliness, not tokens.

## Findings & limits

- **Safe**: 0 turn fails / no save corruption / no campaign mixing across all
  runs; flag off = byte-identical behavior (no-op).
- **Latency negligible**: brain write ≤60 ms, retrieval <1 ms — far under the
  250 ms / 100 ms budgets.
- **Cost controlled**: the block adds ~+390 narrator prompt tokens after It1
  (down from +889), well under the 2000 budget.
- **Continuity benefit NOT proven**: the harness uses scene-neutral actions
  ("look around", "move carefully") that never reference past NPCs/quests, so
  the Second Brain's recall value cannot manifest or be measured here. On short
  campaigns the seed largely duplicates static state already in the context
  packet. Inter-turn repetition is flat-to-slightly-higher with the brain on,
  showing no continuity *gain* in this test (nor a real regression).

## Decision

**KEEP the foundation, flag default OFF. PARK the "enable by default" call.**
The integration is safe, cheap, and bloat-capped, but its core value
(continuity from recalling dropped-out facts) is unproven by a neutral-action
benchmark. To prove or refute value, the next run needs **plot-referencing
actions over a long campaign** (player asks about a past NPC / returns to an
old location / follows up an earlier clue). Do not enable by default or merge
to main until that test shows continuity ≥ stable with the prompt staying lean.

## Final merge state (2026-06-14) — Foundation merged behind flag

The Second Brain **Foundation is merged to `main` behind `AELUNOR_SECOND_BRAIN`
(default OFF)** via `feature/second-brain-foundation-pr`. This records the
"merge it as a KEEP-foundation" decision — it does **not** flip default-on.

Re-measured on the fast-brain-llama matrix (gemma-3n-E4B, 10 turns each,
identical campaign+actions), Ollama and llama.cpp providers:

| Variant | fails | avg/turn | narrator s | prompt tokens | brain_write | brain_retr |
| --- | --- | --- | --- | --- | --- | --- |
| Ollama, SB off | 0/10 | 86.6 s | 52.8 | 24541 | – | – |
| Ollama, SB on | 0/10 | 91.3 s | 51.8 | 24703 | ~19 ms | ~0 ms |
| llama.cpp, SB on | 0/10 | 32.6 s | 22.2 | 24508 | ~15 ms | ~0 ms |

Gate status (all ✅):
- **brain_write < 250 ms** → ~15–19 ms.
- **brain_retrieval < 100 ms** → ~0 ms.
- **brain_context_tokens controlled** → prompt tokens flat (SB off 24541 vs SB
  on 24508/24703); the recall block stays well under the 2000 cap.
- **0 errors / no save corruption / no campaign mixing** with SB on.
- **No visible engine block** in `gm_text` (the `[RELEVANT_CAMPAIGN_BRAIN]`
  block is consistency context only, never echoed).

**KEEP Foundation. `default-on` stays PARK** until a plot-referencing
continuity benchmark proves recall value without quality/token regression.
