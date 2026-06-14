# Current Best Config

> **Aktueller Stand (2026-06-14). `main` enthält:**
> - **It6-Perf-Basis + Output-Budget v1**.
> - **llama.cpp opt-in Provider + `repeat_penalty`-Fix** (PR #59 gemerged): Adapter sendet
>   `repeat_penalty=1.18` / `repeat_last_n=192` → dominanter 1/4-**Stage-D-Runaway eliminiert (0/80 Turns)**,
>   ~60 % niedrigere Avg-Latenz. Details: `docs/performance/llamacpp-opt-in-stability.md`.
> - **Second Brain Foundation — gemerged, aber `AELUNOR_SECOND_BRAIN` default OFF** (PR
>   `feature/second-brain-foundation-pr`): campaign-scoped Weltgedächtnis (`campaigns/<id>/brain/brain.sqlite`),
>   Seed → Write-Hook → bounded Retrieval (`[RELEVANT_CAMPAIGN_BRAIN]`-Block, ~1200 Tok / 8 Cards). Flag-off =
>   No-op, Verhalten unverändert. Latenz/Tokens vernachlässigbar (write <20 ms, retrieval ~0 ms, Prompt-Tokens
>   flach). Details: `docs/performance/second-brain-benchmark.md`.
>
> **Empfohlener Default bleibt Ollama.** `LLM_PROVIDER` / `AELUNOR_LLM_PROVIDER` default `ollama`,
> `AELUNOR_SECOND_BRAIN` default leer (off). Opt-in: `AELUNOR_LLM_PROVIDER=llama_cpp_openai` (schneller, stabil)
> und/oder `AELUNOR_SECOND_BRAIN=1` (Weltgedächtnis).
>
> **Second Brain Foundation = KEEP. `default-on` bleibt PARK**, bis ein **plot-referenzierender
> Continuity-Benchmark** (referenziert alte Entitäten/Threads) den Kontinuitätsnutzen ohne Qualitäts-/
> Token-Regression nachweist. Kein Deferred, keine Embedding-Downloads, keine externe Vector-DB (SQLite),
> keine `semantic_mentions` gemerged.

> **Stabiler main-Stand (Merge 2026-06-14):** `main` enthält jetzt die **It6-Perf-Basis + Output-Budget v1**
> (Fast-Forward von `perf/integrate-it6-output-budget`). Keine Deferred-Defaults, kein llama.cpp-Default,
> keine experimentellen Runtime-Settings. Diese Experimente bleiben als Branches erhalten und sind
> **NICHT in main**:
> - **Deferred Extraction** (`perf/deferred-extraction-fast-visible-turn`): sicher, Default off, Barriere
>   getestet — Kandidat für spätere Wiederaufnahme.
> - **Deferred + llama.cpp Kombi** (`perf/it10-deferred-llamacpp-stability`): PARK — nicht mit der Foundation
>   gemischt. (Der saubere llama.cpp opt-in Provider + `repeat_penalty`-Fix ist hingegen via PR #59 in main,
>   s.o.)

Stand: nach Iteration 6. Ø Turn-Zeit **61.2 s** (Baseline ~110 s, −44 %),
0 harte Fails, 4/4 echte Stories auf der 28-Turn-Benchmark-Kampagne.

> **Update (Branch perf/narrator-output-budget, KEEP):** Der **Narrator-Output-Budget-Contract**
> (AUSGABE-BUDGET-Block im System-Prompt: 2–4 Absätze mit Funktion, Cap-Direktive, „Story vor JSON-Ende
> abschließen", „Patch knapp") senkt **narrator −25.7 %**, **total −17.5 %**, eliminiert die
> Runaway-Generierung (max-Tokens 9589→1870) und die daraus folgenden Schema-Fails (2→0), bei erhaltener
> Story-Länge/-Dichte und Struktur (keine A/B-Fragen, vollständige Enden). Kein Env nötig (Prompt-Default).
> Offen: story_length_guard noch ~67 % (Hebel: Guard-Schwelle max_story_chars anheben). Siehe
> `narrator-output-budget.md`.

## Empfohlene Start-Konfiguration

```powershell
$env:OLLAMA_URL = "http://localhost:11434"   # bzw. host.docker.internal aus Docker heraus
# Aktives Modell via DATA_DIR/llm_settings.json: gemma4:e4b
# num_ctx bleibt 32768 (nicht global senken; 16k/8k getestet & verworfen)

# Memory-Summary nur jeden 2. Turn (Default 1 = jeden Turn):
$env:AELUNOR_MEMORY_SUMMARY_INTERVAL = "2"

# Defaults seit diesem Branch (kein Env nötig):
# - Canon-Extractor: heuristic_only (LLM-Pfad war truncation-vergiftet)
#   Altes Verhalten: $env:AELUNOR_CANON_EXTRACTOR_MODE = "full" | "compact"
# - NPC-Extractor: deterministischer Vorab-Trigger
#   Immer aufrufen: $env:AELUNOR_NPC_EXTRACTOR_TRIGGER = "always"
```

## Effekt gegenüber Baseline

| Metrik | Baseline (It. 0) | Aktuell (It. 6) |
|---|---:|---:|
| Total Ø | ~110 s (50 % Fails) | **61.2 s, 0 Fails** |
| Echte Stories | 2 von 8 Turns | 4 von 4 |
| Narrator-Prompt | 32.1k Tokens (> num_ctx, truncated) | 23.1–23.7k |
| Canon-Extractor | 28.8–35.5 s truncated/halluzinierend | 0 s (Heuristik) |
| Story-Compress | deterministischer Turn-Killer ab ~25 Turns | 12.7–14 s, funktioniert |
| Progression-Gate | 32k truncated, Confidence leer | compact 1.2k Tokens |
| Memory | 11.7–13.5 s jeden Turn | ~11.4 s jeden 2. Turn |
| VRAM Peak | 7.8 GB | 7.8 GB (unverändert) |

## Benchmark ausführen

```powershell
cd D:\Aelunor\01_repo\aelunor-core
python benchmark/run_turn_benchmark.py --label <name> --turns 4
# Ergebnisse: benchmark/perf_results/<name>.jsonl + _summary.json + _stories.json
```
