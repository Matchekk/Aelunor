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

## Status

- Offline latency + token-budget guards: **green** (CI).
- Full A/B/C/D LLM run: **pending local Ollama** (run the commands above; paste
  the `*_summary.json` numbers back to fill the KEEP/PARK/REVERT decision in
  `docs/architecture/campaign-second-brain.md` and `current-best-config.md`).
