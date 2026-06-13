# Narrator Output Budget

Branch: `perf/narrator-output-budget` (off main) · Datum: 2026-06-13
Ziel: Der Narrator soll **kontrolliert, vollständig und dichter** erzählen (nicht bloß kürzer) →
sinkende narrator_s / visible_turn_s / total_turn_s, seltener Story-Length-Guard, kein Runaway/Truncation.

Vergleichsbasis: it6 total ~61.2s · Deferred visible ~49.7s · llama.cpp OK-Turns ~36s (aber Runaway-Fails).
Erkenntnis aus Vor-Loops: Prefill und Schema-Zwang sind NICHT der Bremser; der Narrator ist decode-bound
und kann **runaway** generieren (im llama.cpp-Test bis 6144–8192 Tokens ohne JSON-Abschluss → Fail).

## Aktueller Contract-Stand (Gap-Analyse, vor Änderung)

System-Prompt (`prompt_payloads.build_turn_system_prompt`) + Pacing-Block
(`world_settings.build_pacing_instruction_block`) steuern die Länge so:
- **Nur eine harte Längenregel: ein MINIMUM** — „Die story muss mindestens {min_story_chars} Zeichen
  enthalten." (Default min 800). Das *drückt Richtung Padding/Länge*.
- `max_story_chars=2200` wird nur als **nackte Zahl** im Pacing-Block ausgegeben — **ohne Direktive**
  („überschreite nicht", „fasse dich"). Das Maximum wird real erst **nachgelagert** vom LLM-basierten
  `story_length_guard` (compress, ~13s) erzwungen → Guard wird zum Standardmechanismus statt Ausnahme.
- **Keine Absatz-/Struktur-Regel** (Funktion pro Absatz), keine „vollständig vor JSON-Ende"-Regel,
  keine Dichte-Regel. → Modell kann lang, redundant oder unvollständig generieren.

## Phase 1 — Baseline-Messung (output_budget_baseline, it6-Basis, Ollama default)

| Metrik | Wert |
|---|---|
| total avg / median | 100.8s / 88.1s (Session läuft heiß; ein Runaway-Turn **172.6s**), 2 Errors |
| narrator avg | 64.5s |
| narrator resp_tokens | [1773, 1305, 1014, 1404, **9589**] — meist ~1000–1800, aber 1× **9589 (Runaway!)** |
| gm story_chars | [1567, 1919, 2117, 2191] — Ø ~1948, dicht am 2200-Cap |
| patch/JSON-Anteil (chars) | [4634, 2851, 1754, 2715] — oft **größer als die story selbst** |
| story_length_guard | **3/4 = 75 %** (Ziel <20 %) |

**Befund (Kernfrage geklärt):** Die **Story-Länge ist NICHT das Hauptproblem** (~1900 Zeichen, ok). Die
Kostenstelle ist **(a) der Patch-/JSON-Anteil** (oft größer als die Story) **plus seltene, katastrophale
Runaway-Generierung** (9589 Tokens → 172s-Turn; dominiert den Schnitt und ist exakt die Ursache der
llama.cpp-Truncation-Fails) und **(b) der Guard läuft 75 %**, weil die Story dicht am Cap liegt.

⇒ Contract muss: **Runaway/Patch-Bloat verhindern** (Patch knapp, JSON sauber abschließen, kein
Endlos-Output) + **Story proaktiv unter den 2200-Cap** drücken (Ziel ~unterer/mittlerer Bereich), damit
der Guard zur Ausnahme wird. **Kein hartes num_predict-Limit** zuerst (Truncation-Risiko) — erst Contract,
dann messen.

## Phase 2/3 — Contract implementiert (Code, getestet)

`build_turn_system_prompt` (prompt_payloads.py): die alte nackte Minimum-Regel ersetzt durch einen
**AUSGABE-BUDGET-Block** (bindend):
- 2–4 Absätze mit klarer Funktion (Konsequenz / Atmosphäre / neue Info / optional Cliffhanger ohne Frage).
- Ziel-Länge `min..max_story_chars` (900–2200), kleine Aktion unterer Bereich, **„Überschreite max nicht"**.
- „DICHT statt lang" (keine Wiederholung, keine NPC-Aufzählung bei Umgebungs-Aktion, kein Padding).
- **„Schließe die story vollständig ab, BEVOR das JSON endet; niemals abgeschnitten."**
- **„Halte den patch knapp … keinen Endlos-Output."** (gegen den 9589-Token-Runaway)

`build_pacing_instruction_block` (world_settings.py): Min-Zeile → Range/Cap-Direktive
(„… überschreite max_story_chars nicht und schließe vollständig ab").
Schema unverändert (kein neues Feld — Risiko vermeiden). Kein num_predict-Hardcap (Truncation-Risiko).

Tests (Phase 5, grün, 761 passed): `test_prompt_decision_contract.py` prüft Budget-Block-Präsenz,
vollständiges-JSON-/lean-patch-Regel, Range-statt-Minimum im Pacing-Block; A/B-Frage-Verbot bleibt.

## Phase 6 — Re-Benchmark (output_budget_v1, 6 Turns) — **KEEP**

| Metrik | Baseline | output_budget_v1 | Δ |
|---|---:|---:|---|
| total avg | 100.8s (2 Errors) | **83.2s (0 Errors)** | **−17.5 %** |
| narrator avg | 64.5s | **47.9s** | **−25.7 %** ✓ |
| narrator resp_tokens max | **9589 (Runaway)** | **1870** | Runaway **eliminiert** ✓ |
| narrator resp_tokens avg | 3017 | 1364 | eng gebündelt 791–1870 |
| Schema-Fails | 2 | **0** | ✓ |
| gm story_chars avg | 1948 | 1917 | erhalten (nicht abgeflacht) |
| story_length_guard | 75 % | 67 % | ❌ Ziel <20 % verfehlt |
| Story-Struktur | — | **2–4 Absätze/Turn** (3,3,3,4,3,2) | ✓ |
| A/B-Fragen | — | **0** | ✓ |
| abgeschnittene Enden | — | **0** (alle Sätze vollständig) | ✓ |

**Entscheidung: KEEP.** Der Narrator erzählt jetzt **kontrolliert, vollständig und dicht** (gleiche
Länge, klare 2–4-Absatz-Struktur, keine A/B-Fragen) — nicht bloß kürzer. **Runaway eliminiert**
(max-Tokens 9589→1870), **0 statt 2 Schema-Fails**, narrator **−25.7 %**, total **−17.5 %**. Erfüllt alle
KEEP-Kriterien außer der Guard-Häufigkeit.

**Offen (1 unerfülltes Sub-Ziel): story_length_guard 67 %.** Ursache: der Roh-Narrator-Text überschreitet
gelegentlich noch den 2200-Cap → der Guard komprimiert nach (finale story_chars 1599–2170 sind
post-guard). Hebel für v2: weicheren Ziel-Korridor (~1800) mit Headroom unter dem 2200-Guard-Schwellwert.

## Plan

- **Phase 2/3 Contract:** Output-Budget-Block im System-Prompt — 2–4 Absätze mit klarer Funktion
  (Konsequenz / Atmosphäre / neue Info / optional Cliffhanger ohne Frage), explizite Ziel-/Cap-Spanne,
  „schließe story vollständig ab, bevor das JSON endet", „dicht statt lang". Min-Regel entschärfen
  (kein Padding-Zwang). Schema-Feld nur wenn risikoarm.
- **Phase 4:** story_guard-Häufigkeit < 20 % der Turns.
- **Phase 5:** Prompt-Regression-Tests (Budget-Regel vorhanden, keine A/B-Fragen, vollständiges JSON).
- **Phase 6:** 6-Turn-Benchmark vs Baseline. KEEP wenn 0 Schema-Fails, keine A/B-Fragen, Qualität ≤0.3
  schlechter, narrator_s ≥15 % oder total ≥10 % schneller, weniger Guard, Output stabil im Zielbereich.
- **Phase 7 (optional):** llama.cpp Re-Test — ob Output-Budget die Runaway-Truncation behebt.
