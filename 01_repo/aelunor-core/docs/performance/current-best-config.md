# Current Best Config

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
