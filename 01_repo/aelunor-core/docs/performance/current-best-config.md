# Current Best Config

> **Empfohlener Default ist jetzt llama.cpp (Stand 2026-06-14).**
> - **llama.cpp ist der Standard-Provider** (`llama_cpp_openai`), gemacht nach PR #59 (stabiler
>   `repeat_penalty`-Fix: dominanter 1/4-Stage-D-Runaway eliminiert, 0/80 Turns, ~60 % schneller). Ohne Env
>   wählt `llm_config.py` automatisch llama.cpp; `auto` ist ein Alias für llama.cpp.
> - **Ollama ist Legacy/Fallback** und muss **explizit** gesetzt werden: `AELUNOR_LLM_PROVIDER=ollama`
>   oder `LLM_PROVIDER=ollama`. `AELUNOR_LLM_PROVIDER` hat Vorrang vor `LLM_PROVIDER`.
> - **Kein stiller Fallback:** Ist llama.cpp gewählt, aber der Server nicht erreichbar, bricht der Turn mit
>   einer klaren Fehlermeldung (LLAMA_CPP_BASE_URL/MODEL + Start-Hinweis) ab — Aelunor wird **nicht heimlich
>   langsam** durch automatisches Zurückfallen auf Ollama. Unbekannter Provider → klarer Fehler (kein
>   stilles Ollama). `anthropic` (Cloud) ist nie Default, nur explizit.
> - **Second Brain Foundation ist gemerged, aber `AELUNOR_SECOND_BRAIN` default OFF** (PR #60). Opt-in via
>   `AELUNOR_SECOND_BRAIN=1`. Flag-off = No-op. **llama.cpp + Second Brain ist die schnellste getestete
>   Variante** (~32.6 s/Turn, 0 Fails), aber **Second Brain default-on bleibt PARK** bis ein
>   plot-referenzierender Continuity-Benchmark den Kontinuitätsnutzen ohne Qualitäts-/Token-Regression
>   nachweist. Kein Deferred, keine Embedding-Downloads, keine externe Vector-DB (SQLite), keine
>   `semantic_mentions`. Details: `docs/performance/llamacpp-opt-in-stability.md`,
>   `docs/performance/second-brain-benchmark.md`.
>
> **Start (Windows PowerShell) — llama.cpp als Default:**
> ```powershell
> # 1) Ollama-Modell stoppen, damit VRAM frei ist
> ollama stop gemma4:e4b
>
> # 2) llama.cpp Server starten
> D:\Aelunor\08_experiments\llama_cpp\bin\llama-server.exe `
>   -m D:\Aelunor\08_experiments\llama_cpp\models\gemma-3n-E4B-it-Q4_K_M.gguf `
>   --host 127.0.0.1 --port 8088 -c 32768 -ngl 99 -fa on
>
> # 3) Aelunor nutzt jetzt standardmäßig llama.cpp (keine Env nötig).
> #    Optional nur zur Klarheit:
> $env:LLAMA_CPP_BASE_URL="http://127.0.0.1:8088/v1"
> $env:LLAMA_CPP_MODEL="gemma-3n-e4b"
>
> # 4) Ollama explizit wählen, falls nötig (Legacy/Fallback):
> $env:AELUNOR_LLM_PROVIDER="ollama"
> ```
> Hinweis: Docker-Compose-Deployment setzt `LLM_PROVIDER` weiterhin explizit (dort läuft kein llama-server).

> **Historie — stabiler main-Stand (Merge 2026-06-14):** `main` startete mit **It6-Perf-Basis + Output-Budget v1**
> (Fast-Forward von `perf/integrate-it6-output-budget`), Default damals Ollama. Inzwischen ist llama.cpp der
> Default (s.o.). Keine Deferred-Defaults. Diese Experimente bleiben als Branches erhalten und sind
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
