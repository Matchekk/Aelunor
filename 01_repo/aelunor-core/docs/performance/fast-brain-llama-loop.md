# Fast-Brain-llama Loop — Ergebnis & Empfehlung

Branch: `perf/aelunor-factor-fast-brain-llama` (Basis `feat/campaign-second-brain`, `main` ist Ancestor).
Modell: `gemma-3n-E4B-it-Q4_K_M`. llama-server: `-c 32768 -ngl 99 -fa on` (n_parallel auto = 4).
Kampagne + Aktionen identisch über alle Varianten (`benchmark/run_turn_benchmark.py`, je 10 Turns).
**Rohdaten/Responses bleiben lokal** in gitignored `benchmark/perf_results/` — hier nur aggregierte Zahlen.

## PHASE 0 — Gate (bestanden)
- `main` ist Ancestor von HEAD (0 behind / 14 ahead) → kein Rebase nötig.
- main = `it6 + Output-Budget v1`; Second Brain vorhanden; alle Flags **default OFF**
  (Provider=ollama, `AELUNOR_SECOND_BRAIN` leer, Deferred nicht im Branch, llama.cpp opt-in).
- Volle Suite: 811 grün (jetzt 826 mit neuen Tests).

## PHASE 2 — llama.cpp 1/4-Fail root-caused (Diagnose-Harness)
Tooling (Commit `c93719e`): `benchmark/llama_failure_classifier.py` (pure Stage-A–H-Klassifizierer,
14 Offline-Tests) + `benchmark/diagnose_llama_cpp_failures.py` (treibt echte Turns, fängt
`AELUNOR_LLM_DIAG` + `TurnFlowError`, klassifiziert je Turn).

**Baseline reproduziert: 3/10 Fails, alle Stage D (json_repair).** Mechanismus:
- `call0` (erster Narrator-Schema-Call) war **immer valide**. Ein Downstream-Reject löste einen vollen
  Narrator-**Retry** aus.
- Der llama.cpp-Adapter ließ `repeat_penalty` fallen → Server-Default **1.0 (keine Strafe)**. gemma-3n
  lief auf den Retry-/Repair-Calls in **Wiederholungs-Runaways**, füllte `max_tokens=6144`
  (`finish_reason=length`) → abgeschnittenes invalides JSON → Repair erschöpft → **Stage D**.
- Ollama traf denselben Retry-Trigger, erholte sich aber, weil es `repeat_penalty=1.18` anwendet.
  → **Der fallengelassene Param war der ganze llama.cpp-spezifische Delta.**

## PHASE 3 — Iteration 1 (eine Variable, Commit `a6a714d`)
Adapter sendet jetzt llama.cpp-native `repeat_penalty` (1.18) + `repeat_last_n` (192) auf jedem
`/v1/chat/completions`-Call (spiegelt Ollama; expliziter Caller-Wert wie Repair-Pass 1.05 hat Vorrang;
überschreibbar via `LLAMA_CPP_REPEAT_PENALTY` / `LLAMA_CPP_REPEAT_LAST_N`).

| Lauf | Fails | Ø/Turn | Worst |
| --- | --- | --- | --- |
| Baseline | 3/10 (Stage D) | ~69 s | 142 s |
| it1 10-Turn | 0/10 | ~28 s | 37 s |
| it1 20-Turn | 0/20 | ~31 s | 51 s |
| it1 30-Turn | 0/30 | ~31 s | 55 s |

→ **Stage-D-Runaway eliminiert: 0/80 Turns.** Zusätzlich ~60 % niedrigere Avg-Latenz (Runaway-Tail weg).

## PHASE 1 — Fastest-Stable-Matrix (je 10 Turns)

| Variante | ok/err | Ø s | Median s | Worst s | Narrator s | Prompt-Tok | brain_write | brain_retr |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A Ollama, SB off | 10/0 | 86.6 | 80.9 | 124.0 | 52.8 | 24541 | – | – |
| B Ollama, SB on | 10/0 | 91.3 | 95.3 | 128.1 | 51.8 | 24703 | 19 ms | ~0 ms |
| C llama, SB off | 9/**1** | 41.4 | 41.0 | 60.5 | 27.5 | 24527 | – | – |
| D llama, SB on | 10/0 | **32.6** | 27.5 | 53.7 | 22.2 | 24508 | 15 ms | ~0 ms |
| E Ollama+SB+Deferred | — | — | — | — | — | — | — | — |
| F llama+SB+Deferred | — | — | — | — | — | — | — | — |

- **llama.cpp ≈ −52 % (C) bis −62 % (D) gegen Ollama-Baseline** — bestätigt die frühere −61..−65 %-Größenordnung.
- **Second Brain kostet praktisch nichts:** write ~15–19 ms, retrieval ~0 ms, **Prompt-Tokens flach**
  (SB off 24527 vs SB on 24508/24703). → Gates *kontrollierte Tokens* ✓ und *kein Kontextmüll* ✓ erfüllt.
- E/F **nicht gefahren**: Deferred-Code ist nicht in diesem Branch ("no deferred"). Erfordert gezielten
  Cherry-pick aus `perf/deferred-extraction-fast-visible-turn` — bewusst NICHT unaufgefordert gezogen.

## Residual-Fail (ehrlich)
Über die ganze Matrix + 60 Diagnose-Turns gab es **genau 1 Fail**: matrixC **Turn 1**,
`"Die KI-Antwort wirkt abgeschnitten"` (Truncation-Guard, `NARRATOR_RESPONSE`) — **andere Klasse** als der
behobene Stage-D-Runaway, sah cold-start-artig aus und **reproduzierte in 60 Folge-Turns nicht** (it1-Läufe
0/80). Geschätzte Rate ~1/80 (~1.25 %). Kein verlässlicher Repro → **nicht „gefühlt" weiter optimiert**.
Iteration-2-Kandidat (sobald reproduzierbar): Truncation-Guard-Schwelle vs. `LLAMA_CPP_MAX_TOKENS`/
Output-Budget-Durchsetzung auf llama.cpp-Output prüfen (eine Variable).

## „Schnellste Variante" (Definition angewandt)
Schnellste Variante mit 0 Turn-Fails / 0 Format-/Schema-Fails / 0 Save-Korruption / 0 State-Races /
stabiler Qualität / keiner Kontinuitätsregression / keinen Engine-Artefakten:
**→ D (llama.cpp + Second Brain) mit Ø 32.6 s** ist die schnellste Variante mit 0 Fails in der Matrix
(SB kostet nichts, llama.cpp halbiert die Zeit). Caveat: llama.cpp insgesamt hat noch den ~1.25 %-Residual
(Turn-1-Truncation), daher noch **nicht 100 % „0-Fail stabil nachgewiesen"** im strengen Sinn — der
**dominante 1/4-Fail ist aber weg**.

## Empfehlung

### Darf nach main
- **Diagnose-Tooling** (`c93719e`): pure Tooling, default-off, 0 Laufzeitrisiko.
- **repeat_penalty-Fix** (`a6a714d`): nur llama.cpp-Adapter-Pfad (default-off-Provider). Macht den
  experimentellen Provider stabil, berührt Ollama/Default nicht. Sicher als KEEP.

### Bleibt default OFF (opt-in)
- **llama.cpp-Provider** (`AELUNOR_LLM_PROVIDER=llama_cpp_openai`): jetzt die schnelle Variante, aber wegen
  ~1.25 %-Residual-Truncation noch opt-in, nicht default-on.
- **Second Brain** (`AELUNOR_SECOND_BRAIN=1`): Tokens/Latenz/Kontextmüll-Gates erfüllt; **default-on fehlt
  weiter: plot-referenzierender Continuity-Benchmark + Qualitätsregression-Check** (die 2 offenen der 4 Gates).

### PARK / REVERT
- **Nichts zu reverten.** E/F (Deferred-Kombis) ungetestet, da Deferred nicht im Branch — PARK
  (Cherry-pick nur auf Anfrage).

### Startkommandos — schnellste stabile Variante (D: llama.cpp + Second Brain)
```powershell
# 1) llama.cpp-Server (lokal vorhanden, kein Download)
D:\Aelunor\08_experiments\llama_cpp\bin\llama-server.exe `
  -m D:\Aelunor\08_experiments\llama_cpp\models\gemma-3n-E4B-it-Q4_K_M.gguf `
  --host 127.0.0.1 --port 8088 -c 32768 -ngl 99 -fa on
# (VRAM: vorher 'ollama stop <model>' — 12GB teilen sich llama.cpp & Ollama nicht gut)

# 2) App mit Provider + Second Brain
$env:AELUNOR_LLM_PROVIDER="llama_cpp_openai"
$env:LLAMA_CPP_BASE_URL="http://127.0.0.1:8088/v1"
$env:LLAMA_CPP_MODEL="gemma-3n-e4b"
$env:AELUNOR_SECOND_BRAIN="1"
# .\"Aelunor starten.bat"  bzw. uvicorn-Start
```
Konservativ-stabil ohne llama.cpp: Variante **A** (Ollama, alles default) bleibt der sichere Fallback.
