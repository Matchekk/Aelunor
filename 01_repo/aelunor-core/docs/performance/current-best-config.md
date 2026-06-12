# Current Best Config

Stand: nach Iteration 1 (Canon-Extractor heuristic_only, KEEP).

## Modelle / Kontext

```powershell
$env:OLLAMA_URL = "http://localhost:11434"   # bzw. host.docker.internal aus Docker heraus
# Aktives Modell via DATA_DIR/llm_settings.json: gemma4:e4b
$env:OLLAMA_NUM_CTX = "32768"   # nicht global senken (16k/8k bereits getestet & verworfen)

# Canon-Extractor: LLM-Pfad aus (Default seit Iteration 1, kein Env nötig).
# Altes Verhalten erzwingen: $env:AELUNOR_CANON_EXTRACTOR_MODE = "full"
```

## Effekt gegenüber Baseline

| Metrik | Baseline (It. 0) | Aktuell |
|---|---:|---:|
| LLM-Calls/Turn | 5+ | 3+ |
| Canon-Extractor | 28.8–35.5 s/Turn, truncated, halluziniert | 0 s, deterministische Heuristik |
| Sauberer Turn (1 Narrator-Call) | ~91 s | ~60 s erwartet |

## Bekannte offene Baustelle

Narrator-Prompt ~32k Tokens > num_ctx auf Kampagnen ab ~25 Turns → ~50 % Turn-Fails
und Fallback-Stories. Wird in Iteration 4 (Prompt-Budget) behandelt.

## Benchmark ausführen

```powershell
cd D:\Aelunor\01_repo\aelunor-core
python benchmark/run_turn_benchmark.py --label <name> --turns 4
# Ergebnisse: benchmark/perf_results/<name>.jsonl + <name>_summary.json + <name>_stories.json
```
