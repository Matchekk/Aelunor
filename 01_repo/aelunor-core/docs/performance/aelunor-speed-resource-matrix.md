# Aelunor Speed/Resource-Matrix

Benchmark-Setup: Kopie der echten Kampagne `camp_c02276e6d5` (28 Turns Historie, Turn-Nr. ~17+),
4 echte `do`-Turns pro Lauf über `benchmark/run_turn_benchmark.py`, gemma4:e4b, num_ctx 32768,
Ollama lokal. Jeder Lauf startet vom identischen Kampagnenstand.

| Iteration | Commit | Hypothese | Änderung | Calls pro Turn | Narrator s | Story-Compress s | Canon-Extractor s | NPC s | Memory s | Total Ø | Median | Best | Worst | Prompt Tokens Narrator | Max Prompt Tokens | Output Tokens | Tokens/s | VRAM Peak | RAM Peak | CPU Ø | GPU Ø | Schema-Fails | Quality Score | Entscheidung |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 0 (Lauf A) | — | Baseline reproduzieren | keine (nur Benchmark-Runner) | ≥5 | 55.7 | 0 (lief nicht) | 35.5 (2 Calls) | 11.4 | 11.7 | 114.8 | 114.8 | 91.9 | 137.7 | 31911 | 32767 (Extractor truncated) | — | — | 7801 MB | — | — | 65 % | 2/4 Turns fehlgeschlagen | Basis | Baseline |
| 0 (Lauf B) | — | Baseline reproduzieren | + Profil-Phase story_length_guard (nur Messung) | ≥5 | 51.2 | 0 (lief nicht) | 28.8 (2 Calls) | 12.1 | 13.5 | 106.2 | 106.2 | 92.0 | 120.4 | 32072 | 32767 (Extractor truncated) | — | — | 7798 MB | — | — | 69 % | 2/4 Turns fehlgeschlagen | Basis | Baseline bestätigt |
| 1 | 751a445 | Canon-LLM-Pfad ist truncated → wertlos/schädlich, Skip kostet nichts | AELUNOR_CANON_EXTRACTOR_MODE, Default heuristic_only | 3 statt 5 | 71.5 (Retry-verzerrt) | 0 (lief nicht) | **0** | 9.8 | 11.7 | 93.5 | 93.5 | 91.4 | 95.7 | 32068 | 32605 | — | — | 7795 MB | — | — | 70 % | 2/4 + 2 Fallback-Stories (Narrator-Klippe, unabhängig von Canon) | keine Canon-Regression (A/B-Beweis: full-Patch = Halluzination) | **KEEP** |
| 2 | — | Kompaktes Packet macht Canon-LLM nutzbar | compact-Modus (flag-gated, offline A/B) | — | — | — | 25–28 s/Call (Schema-Decoding) | — | — | — | — | — | — | — | Packet 1.2k statt 33.4k | ~1k Boilerplate | — | — | — | — | — | 0 (extrahiert korrekt, aber equip-Halluzination) | Facts > heuristic, Kosten 3–5× über Budget | **PARK** (heuristic_only bleibt) |
