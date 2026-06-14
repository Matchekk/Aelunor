# llama.cpp Provider — Stabilität (repeat_penalty-Fix)

> **Update (2026-06-14): llama.cpp ist jetzt der Standard-Provider** (`chore/default-llamacpp-runtime`).
> Der hier dokumentierte Stabilitäts-Fix (PR #59) hat den Provider produktionsreif gemacht; daraufhin wurde
> er zum Default. Ollama ist jetzt Legacy/Fallback (explizit via `AELUNOR_LLM_PROVIDER=ollama`).
> **Kein stiller Fallback:** ist llama.cpp gewählt, aber der Server nicht erreichbar, bricht der Turn mit
> einer klaren Fehlermeldung ab (LLAMA_CPP_BASE_URL/MODEL + Startkommando) statt heimlich auf Ollama
> zurückzufallen.

Scope (ursprünglicher PR #59): der llama.cpp-Provider + Diagnose-Tooling + `repeat_penalty`-Fix.
Rohdaten/Responses bleiben lokal in gitignored `benchmark/perf_results/` — hier nur Aggregate.

## Startkommandos (Windows PowerShell)
```powershell
# 1) Ollama-Modell stoppen, damit VRAM frei ist
ollama stop gemma4:e4b
# 2) llama.cpp Server starten
D:\Aelunor\08_experiments\llama_cpp\bin\llama-server.exe `
  -m D:\Aelunor\08_experiments\llama_cpp\models\gemma-3n-E4B-it-Q4_K_M.gguf `
  --host 127.0.0.1 --port 8088 -c 32768 -ngl 99 -fa on
# 3) Aelunor nutzt jetzt standardmäßig llama.cpp (keine Env nötig). Optional:
$env:LLAMA_CPP_BASE_URL="http://127.0.0.1:8088/v1"
$env:LLAMA_CPP_MODEL="gemma-3n-e4b"
# 4) Ollama explizit (Legacy/Fallback):
$env:AELUNOR_LLM_PROVIDER="ollama"
```

## Problem
Der experimentelle, OpenAI-kompatible llama.cpp-Provider war früher ~−60 % schneller als Ollama, hatte
aber einen **sporadischen ~1/4 Format-/Repair-Fail** (`gemma-3n-E4B`).

## Diagnose (reproduzierbar gemacht)
Neues Tooling:
- `benchmark/llama_failure_classifier.py` — pure, offline-testbare Klassifizierung eines Turns in genau eine
  Stage **A–H** (empty / transport / invalid-JSON / repair-failed / schema / patch-validator / story-quality /
  patch-apply), mit OK/DEGRADED/FAIL-Severity, Repro-Key-Gruppierung und Fix-Hint-Tabelle.
- `benchmark/diagnose_llama_cpp_failures.py` — treibt echte Turns über denselben Engine-Pfad wie die API,
  fängt `AELUNOR_LLM_DIAG`-Per-Call-Records + `TurnFlowError`, klassifiziert je Turn. Unterstützt
  `--repeat-action`-Isolation und Provider-Vergleich.

**Baseline reproduziert: 3/10 Fails, alle Stage D (json_repair).**

## Root Cause
- Der llama.cpp-Adapter ließ `repeat_penalty` fallen → es griff der llama-server-Default **1.0 (keine Strafe)**.
- Der erste Narrator-Schema-Call (`call0`) war **immer valide**. Ein Downstream-Reject löste einen vollen
  Narrator-**Retry** aus; ohne Strafe lief `gemma-3n` auf den Retry-/Repair-Calls in
  **Wiederholungs-Runaways**, füllte `max_tokens=6144` (`finish_reason=length`) → abgeschnittenes invalides
  JSON → Repair erschöpft → **Stage D**.
- Ollama traf denselben Retry-Trigger, erholte sich aber, weil es `repeat_penalty=1.18` anwendet.
  → **Der fallengelassene Param war der ganze llama.cpp-spezifische Delta.**

## Fix (eine Variable)
Der Adapter sendet jetzt die llama.cpp-nativen Sampler-Felder `repeat_penalty` (Default 1.18) +
`repeat_last_n` (Default 192) auf jedem `/v1/chat/completions`-Call (spiegelt Ollama; expliziter
Caller-Wert wie der Repair-Pass mit 1.05 hat Vorrang). Überschreibbar via `LLAMA_CPP_REPEAT_PENALTY` /
`LLAMA_CPP_REPEAT_LAST_N`.

| Lauf | Fails | Ø/Turn | Worst |
| --- | --- | --- | --- |
| Baseline | 3/10 (Stage D) | ~69 s | 142 s |
| Fix 10-Turn | 0/10 | ~28 s | 37 s |
| Fix 20-Turn | 0/20 | ~31 s | 51 s |
| Fix 30-Turn | 0/30 | ~31 s | 55 s |

→ **Stage-D-Runaway eliminiert: 0/80 Turns.** Zusätzlich ~60 % niedrigere Avg-Latenz (Runaway-Tail weg).

## Speed vs. Ollama (gleiche Kampagne + Aktionen, je 10 Turns)
| Provider | Fails | Ø/Turn | Narrator s | Prompt-Tok |
| --- | --- | --- | --- | --- |
| Ollama (Default) | 0/10 | 86.6 s | 52.8 | 24541 |
| llama.cpp (opt-in, Fix) | 9/10\* | 41.4 s | 27.5 | 24527 |

\* Der eine Fail war eine Turn-1-Truncation (`NARRATOR_RESPONSE`, **andere Klasse** als der behobene
Stage-D-Runaway) und reproduzierte in 60 Folge-Turns nicht (~1.25 % Restrate). Daher bleibt llama.cpp
**opt-in** (kein Default-Wechsel); ehrlich dokumentiert statt überschätzt.

## Status
- **Default bleibt Ollama.** `LLM_PROVIDER`/`AELUNOR_LLM_PROVIDER` default `ollama`.
- **llama.cpp ist opt-in** (`AELUNOR_LLM_PROVIDER=llama_cpp_openai`), durch den Fix deutlich stabiler.
- Volle Suite grün. Flag-off / Default-Pfad unverändert.

## Startkommandos (opt-in llama.cpp)
```powershell
# 1) Server (lokales Binary/Modell, kein Download)
D:\Aelunor\08_experiments\llama_cpp\bin\llama-server.exe `
  -m D:\Aelunor\08_experiments\llama_cpp\models\gemma-3n-E4B-it-Q4_K_M.gguf `
  --host 127.0.0.1 --port 8088 -c 32768 -ngl 99 -fa on
# (VRAM: vorher 'ollama stop <model>' — 12GB teilen sich llama.cpp & Ollama nicht gut)

# 2) App auf den opt-in Provider zeigen
$env:AELUNOR_LLM_PROVIDER="llama_cpp_openai"
$env:LLAMA_CPP_BASE_URL="http://127.0.0.1:8088/v1"
$env:LLAMA_CPP_MODEL="gemma-3n-e4b"
```
Sicherer Default ohne Server: einfach nichts setzen → Ollama.
