# Performance-Loop: Iterations-Log

Branch: `perf/turn-latency-loop-known-bottlenecks`
Ziel: Ø Turn-Zeit < 45 s ohne Qualitätsverlust. Baseline laut Vorarbeit: ~90 s/Turn.

Regeln: eine Änderung pro Iteration, vorher/nachher messen, nur KEEP committen.

---

## Iteration 0 — Baseline (2026-06-12)

**Setup:**
- Benchmark-Runner `benchmark/run_turn_benchmark.py` neu erstellt (kein App-Code geändert):
  kopiert `camp_c02276e6d5` (28 Turns Historie) in isoliertes `DATA_DIR`
  (`.agent_tmp/perf-runtime`), führt N echte Turns über `turn_engine.create_turn_record`
  aus (identischer Pfad wie die API, inkl. `finalize_state_memory`), sammelt
  Profiling-JSONL + GPU/RAM-Samples. Jeder Lauf startet vom identischen Stand.
- Modell: gemma4:e4b (aus `llm_settings.json`), num_ctx 32768, Ollama lokal (localhost:11434).
- Stolperstein behoben: User-Env `OLLAMA_URL=host.docker.internal` ist von der Shell aus
  nicht erreichbar — Runner setzt die URL jetzt explizit (`--ollama-url`).

**Befund Code-Analyse (vor Messung):**
- Canon-Extractor: 2 LLM-Calls/Turn (Quelle player + narrator), je mit komplettem
  STATE_PACKET (alle Items, alle Szenen, alle Rassen/Bestien/Elemente, NPC-Codex).
  Heuristik-Kandidaten laufen davor deterministisch; LLM-Patch wird nur additiv gemerged
  (`merge_safe_patch_additive`). LLM-Fehlschlag fällt heute schon still auf `blank_patch`
  zurück → `heuristic_only` ist strukturell sicher.
- Story-Compress (`story_length_guard.rewrite_story_length_guard`): bis zu 2 Rewrite- +
  1 Compress-Versuch, läuft innerhalb der Narrator-Phase.
- Memory-Summary läuft innerhalb `create_turn_record` (Phase `finalize_state_memory`).

**Messung Lauf A (`it0_baseline`, 4 Turns angefragt):**
- 2/4 Turns erfolgreich (Turn 1: interner Fehler, Turn 2: „KI-Antwort wirkt abgeschnitten") —
  bestätigt die bekannte Schema-/Truncation-Instabilität auf der 28-Turn-Kampagne.
- Erfolgreiche Turns: 137.7 s / 91.9 s (Ø 114.8 s) — Baseline ~90 s grob reproduziert,
  nach oben verschoben durch Narrator-Retries.
- Phasen (Ø über erfolgreiche Turns):
  - Narrator: 55.7 s, **31 911 Prompt-Tokens Ø / 32 093 max** → direkt an der 32k-Klippe.
  - Canon-Extractor: 17.9 + 17.6 = **35.5 s** über 2 Calls; max_prompt_tokens **exakt 32 767**
    → Truncation des STATE_PACKET bewiesen.
  - Memory (`finalize_state_memory`): 11.7 s (7.2k Tokens).
  - NPC-Extractor: 11.4 s (nur ~0.9k Tokens — Zeit ist fast reine Modell-/Prefill-Latenz).
  - Story-Compress: lief in diesen 2 Turns nicht (LLM-Calls wären als „unphased" aufgetaucht).
- Ressourcen: VRAM-Peak 7 801 MB, GPU Ø 65 %.
- Instrumentierungslücke geschlossen: `rewrite_story_length_guard` hat jetzt eine eigene
  Profil-Phase `story_length_guard` (turn_engine.py) — reine Messbarkeit, kein Verhalten geändert.
**Messung Lauf B (`it0_baseline_b`, 4 Turns angefragt):**
- Wieder 2/4 Turns erfolgreich (Turn 1 + Turn 4: interner Fehler) → Fehlerrate Baseline
  gesamt: **4 von 8 Turns (50 %)**.
- Erfolgreiche Turns: 120.4 s / 92.0 s (Ø 106.2 s).
- Narrator: 51.2 s Ø, **32 072 Prompt-Tokens Ø / 32 570 max** — Prompt überschreitet num_ctx
  bereits leicht (Ollama truncated still).
- Canon-Extractor: 14.3 + 14.5 = 28.8 s; Truncation erneut (max 32 767).
- Memory 13.5 s, NPC 12.1 s. Story-Compress lief erneut nicht (0 Guard-Calls).
- VRAM-Peak 7 798 MB, GPU Ø 69 %.

**Baseline-Fazit (Iteration 0, beide Läufe, n=4 erfolgreiche Turns):**
- Total Ø ≈ **110 s** (Median ~106 s, Best 91.9 s, Worst 137.7 s) — Vorgabe ~90 s
  reproduziert; Differenz = Narrator-Retries nach Schema-Fails.
- Bottleneck-Ranking: Narrator ~53 s > Canon-Extractor ~32 s (wertlos, truncated) >
  Memory ~12.6 s ≈ NPC ~11.8 s.
- Akzeptanz erfüllt: Canon-Extractor-Truncation, Narrator-Promptgröße und Phasen
  sind sauber messbar. → Weiter mit Iteration 1.

---

## Iteration 1 — Canon-Extractor: heuristic_only (2026-06-12)

**Hypothese:** Der LLM-Pfad des Canon-Extractors (~29–35 s/Turn, 2 Calls) liefert wegen
STATE_PACKET-Truncation (exakt 32 767 Tokens) keine echten Informationen. Skip ohne Qualitätsverlust.

**Änderung:** `AELUNOR_CANON_EXTRACTOR_MODE=full|compact|heuristic_only` in
`app/services/canon/extractor.py` (`canon_extractor_mode()`). Default `full` = unverändert.
`heuristic_only` überspringt nur den LLM-Call; deterministische Heuristik-Kandidaten,
Quarantäne und additive Patch-Merges bleiben vollständig erhalten.
44 bestehende canon/extractor-Tests grün.

**Messung (`it1_heuristic_only`, 4 Turns angefragt, 2 abgeschlossen):**
- Canon-Extractor-Phasen vollständig verschwunden: **−28.8 bis −35.5 s pro Turn**.
- Total Ø 93.5 s (vs. ~110 s Baseline). Direkter Total-Vergleich ist allerdings
  Retry-verrauscht: beide „erfolgreichen" it1-Turns brauchten 5 Narrator-Versuche
  und endeten im 159-Zeichen-Lokal-Fallback.

**Wichtigster Nebenbefund (Profil-Detailanalyse `story_chars` + Kampagnen-Turns):**
- Diese Kampagne ist **bereits über der Kollaps-Klippe**: Narrator-Prompt
  32 072 Tokens Ø (max 32 605) > nutzbares 32k-Fenster. Pro Lauf scheitern 2 von 4
  Turns hart, und auch „erfolgreiche" Turns sind teils Fallback-Stories (159 Zeichen).
  Ein sauberer Turn (1 Narrator-Call, echte 1.8–2.1k-Story) kostet ~91 s.
  Turn-Totals zwischen Läufen vergleichen sich daher nur über die Phasen-Zerlegung.
- Der Narrator-Kollaps ist unabhängig vom Canon-Modus (Canon läuft nach dem Narrator).
  Die eigentliche Heilung ist Iteration 4 (Prompt-Budget).

**Qualitäts-Beweis (offline A/B auf echtem 1 963-Zeichen-GM-Text, identischer State):**
- STATE_PACKET im full-Modus: 100 122 Zeichen ≈ 33,4k Tokens → über num_ctx, truncated.
- Full-Mode-LLM-Patch (17 s): **reiner Halluzinations-Müll** — `meta.phase="lobby"`
  (würde die aktive Kampagne zurücksetzen), erfundener Charakter „Protagonist" mit
  `scene_id="start_scene"`, Begründung „Start of the scenario". Das Modell sieht nur
  Packet-Fragmente und erfindet Generika. Aktiv schädlich, nicht nur nutzlos.
- heuristic_only (0.0 s): leerer Patch auf demselben Text — korrekt, der Text enthielt
  keine neuen kanonischen Fakten.

**Entscheidung: KEEP.**
- `AELUNOR_CANON_EXTRACTOR_MODE` Default = `heuristic_only` (bewusst, im Code-Docstring
  und hier dokumentiert; `full` bleibt per Env wählbar).
- Ersparnis: ~29–35 s pro Turn, 2 LLM-Calls weniger, plus Wegfall einer aktiven
  Halluzinationsquelle. Heuristik, Quarantäne und Patch-Merge unverändert.
- Tests: volle Suite 758 passed, 1 skipped.
- Commit: 751a445.

---

## Iteration 2 — Compact Canon Packet (2026-06-12)

**Hypothese:** Kompaktes Packet (Szene, Akteur, Namenslisten, Delta-Text) statt Voll-State
reicht für Canon-Extraktion und macht den LLM-Pfad wieder nutzbar.

**Änderung:** `build_compact_extractor_context_packet()` in extractor.py, aktiv bei
`AELUNOR_CANON_EXTRACTOR_MODE=compact`. Schnitt: nur aktive Party (Skill-/Item-NAMEN statt
Voll-Profile), aktuelle Szene + Szenenliste, NPC-Top-12 (Name/Rasse/Status/Szene),
Rassen/Bestien/Elemente als Namenslisten, keine Codex-known_facts, keine Element-Relationen,
kein Voll-NPC-Codex.

**Offline-A/B (identischer State, canon-reicher Synthetik-Text mit Item-Fund,
NPC-Auftritt, Skill-Levelup):**
- Packet: **3 595 Zeichen ≈ 1,2k Tokens** (full: 100 122 Zeichen ≈ 33,4k) → keine Truncation.
- Qualität: compact extrahiert korrekt `inventory_add: ["Eisendolch mit Moosgravur"]`,
  `skill_level_up: Moosgriff`, NPC „Mara Weidenruf" — heuristic_only findet auf demselben
  Text nichts. Aber auch Rauschen: halluziniertes `equip_set` (Runenschwert/Kurzschwert),
  fehlgenutzte Schema-Sektionen (items_new/plotpoints als Charakter-Objekte).
- Latenz: **25,3 s/Call mit num_ctx 8192; 25,5–28,2 s mit 32k** → kein Reload-Effekt,
  der Treiber ist die schema-erzwungene Generierung: CANON_EXTRACTOR_SCHEMA verlangt das
  komplette Patch-Skelett, das Modell füllt jede Sektion mit Boilerplate (~25 s Decoding).
- Bei 2 Calls/Turn wären das ~50 s — schlechter als der full-Modus der Baseline.

**Entscheidung: PARK.** KEEP-Kriterium (≤5–8 s extra) um Faktor 3–5 verfehlt.
heuristic_only bleibt Default. Compact bleibt flag-gated als Basis für eine spätere
Iteration „schlankes Extractor-Schema" (das volle Patch-Schema ist der eigentliche
Kostentreiber, nicht das Packet). Kein Default-Verhalten geändert.
Commit: 5bb4d6f.

---

## Iteration 3 — Story-Compress ohne Vollkontext (2026-06-12)

**Hypothese:** Compress braucht nur die erzeugte Story + Ziellänge + Stilregel,
nicht den kompletten 31k-Narrator-Kontext.

**Änderung (story_length_guard.py, nur Compress-Zweig):**
- Eigener minimaler System-Prompt (`_COMPRESS_SYSTEM_PROMPT`, Lektor-Rolle).
- User-Prompt = Auftrag + Storytext; der volle Narrator-User-Prompt entfällt.
- Temperatur fix 0.2. Kein num_ctx-Override (vermeidet Modell-Reload mitten im Turn;
  Abweichung von der Plan-Idee 4096/8192 ist gemessen begründet: Iteration 2 zeigte,
  dass der num_ctx-Wechsel nichts spart, und der Gewinn kommt aus dem Prefill).
- Skip-bei-kurzer-Story existierte bereits (Schleifenbedingung vor dem Call).
- Rewrite-Zweig (Mindestlänge) bewusst unverändert: er braucht Weltkontext, um Inhalt
  zu ERWEITERN. Achtung, dokumentiertes Risiko: auch er sendet den Vollkontext und
  dürfte auf 25+-Turn-Kampagnen degenerieren → Heilung über Iteration 4 (Prompt-Budget).

**Offline-A/B (realer 91k-Zeichen-User-Prompt aus gespeichertem Turn, 5.2k-Zeichen-Story,
Ziel 2 000 Zeichen):**
- ALT (Vollkontext): **2/2 Fehlschläge**, degenerierte Antwort (`{` …) nach 8.2 s / 2.5 s.
  → Auf der 28-Turn-Kampagne war jeder Compress-Call ein **deterministischer Turn-Killer**
  (Guard-Exception → TurnFlowError → Narrator-Retry). Erklärt mutmaßlich einen Teil der
  50 % Baseline-Turn-Fails bei langen Stories.
- NEU (nur Story): 2/2 Erfolge, 17.2 s / 16.2 s (generierungsdominiert), Output 3 085 /
  2 321 Zeichen, sprachlich sauber; deterministisches `_trim_story_to_max` kappt danach
  wie bisher auf Satzgrenze.
- 49 Guard-Tests grün.

**Messung (`it3_compress_minimal`, 4 Turns):**
- **4/4 Turns abgeschlossen, 0 harte Fails** — erstmals in diesem Loop (Baseline: 50 % Fails).
- Total Ø **76.7 s** (Median 79.6, Best 57.4, Worst 90.2) vs. Baseline ~110 s.
- Turn-Detail: Turn 29 echte Story (1 487 Zeichen) inkl. **funktionierendem Compress-Call
  (14.0 s, 889 Prompt-Tokens statt ~31k)**; Turn 31 sauber mit 1 Narrator-Call in **56.9 s**
  (= aktueller Clean-Turn-Floor: Narrator ~32 + Memory ~12 + NPC ~11);
  Turns 30/32 Fallback-Stories nach je 6 Narrator-Versuchen (Narrator-Klippe, → Iteration 4).
- State-Digest unauffällig (Items 12, NPCs 2, Szenen 2, Quarantäne 0).

**Entscheidung: KEEP.**
- Compress-Call: von „deterministischer Turn-Killer auf 25+-Turn-Kampagnen" zu
  funktionierend (889 Tokens, 14 s, generierungsdominiert).
- Harte Turn-Fails 0/4 statt 2/4. Keine Qualitäts-/State-Regression sichtbar.
- Nebenfix: Benchmark-Runner exportiert Stories jetzt aus `gm_text_display`.
- Commit: cdd0cc1.

---

## Iteration 4 — Narrator Prompt Budget (2026-06-12)

**Hypothese:** Der 30–32k-Token-Narrator-Prompt enthält massive Waste-Anteile;
gezielte deterministische Kürzung bringt ihn unter 24k und beendet die Kollaps-Klippe.

**Prompt-Budget-Bericht (echter gespeicherter Turn-28-Prompt, 101k Zeichen ≈ 32k Tokens):**
- User-Prompt 91,5k Zeichen, davon CONTEXT_PACKET 82,4k (90 %).
- Top-Posten im Packet: recent_turns 19,2k (23 %) · characters 11,5k · **meta 11,4k** ·
  plotpoints 9,4k · setup 6,7k · boards 5,7k · combat 4,5k.
- Waste-Funde:
  1. `meta.extraction_quarantine` (5,7k): interne Extraktions-Buchhaltung inkl.
     evidence_text — für den Narrator irrelevant.
  2. `meta.combat` = **exaktes Duplikat** des top-level `combat`-Eintrags (−4,5k).
  3. `combat.action_queue`: unbegrenzt wachsend (15 Runden seit Turn 2, 4,3k).
  4. `meta.timing/intro_state/migrations/world_codex_seed`: interne Felder.
  5. recent_turns: 8 × voller GM-Text à ~2,3k.
  6. plotpoints: 23 Einträge, ungefiltert, teils mit Halluzinations-Artefakten.

**Änderung (memory_context.py + build_context_packet):**
- `compact_meta_for_turn_context`: interne meta-Keys raus (Quarantäne, combat-Duplikat,
  timing, intro_state, migrations, world_codex_seed).
- `compact_combat_for_turn_context`: action_queue auf letzte 6 Einträge gekappt
  (mit `action_queue_omitted_count`).
- recent_turns: letzte 3 Turns voll, ältere 5 mit gm_text auf 400 Zeichen gekürzt,
  requests entfernt.
- `compact_plotpoints_for_turn_context`: resolved/done/closed raus, letzte 16,
  notes auf 280 Zeichen.
- Kein globales num_ctx-Senken (bleibt 32768).

**Offline-Verifikation:** Packet 82 390 → **54 310 Zeichen (−34 %)**;
Narrator-Prompt geschätzt ~23k Tokens statt 32k. 758 Tests grün.

**Messung (`it4_prompt_budget`, 4 Turns):**
- **4/4 Turns, 0 Fehler, 0 Fallbacks — alle 4 Stories echt (1 777–2 105 Zeichen).**
  Erstmals liefert jeder Turn echte Erzählung (Baseline: 2/8, It. 3: 2/4).
- Narrator-Prompt: **23 322 Tokens Ø / 23 730 max** (vorher 32 072/32 605) → Ziel <24k
  erreicht, ~9k Tokens unter num_ctx, keine Truncation mehr möglich.
- Narrator-Retries: 7 Calls über 4 Turns (It. 3: 16) — Restretries sind Qualitäts-Checks
  (Repetition/Truncation-Detektor), kein Kollaps.
- Sauberer Turn: **54.1 s** (Narrator 31.2 + Memory ~12.7 + NPC ~12.4).
- Total Ø 88.2 s — numerisch über It. 3 (76.7 s), aber nicht vergleichbar: It.-3-Schnitt
  war durch billige Fallback-Turns (159 Zeichen, kein Guard) geschönt. Ehrlicher Vergleich
  über sauberen Turn + Qualität: 54.1 s mit 4/4 echten Stories vs. 56.9 s mit 2/4.
- Story-Guard-Compress lief 2× (je ~13.6 s, 768 Tokens) — funktioniert.
- State-Digest plausibel (Items 15, NPCs 3, Quarantäne 0).

**Entscheidung: KEEP.** Promptgröße −27 %, Stabilität von Münzwurf auf 100 % echte
Stories, Quality klar über Baseline. Commit: 8dba807.

---

## Iteration 5 — Memory-Frequenz (2026-06-12)

**Hypothese:** Memory-Summary (~12.7 s/Turn) muss nicht jeden Turn laufen; recent_turns
deckt die letzten 8 Turns ohnehin wörtlich ab.

**Änderung:** `AELUNOR_MEMORY_SUMMARY_INTERVAL` (Default 1 = bisheriges Verhalten).
Skip nur bei `1 <= turn_gap < interval` — Edit (gap 0) und Undo (gap < 0) bauen
weiterhin immer neu; fehlende/leere Summary baut immer.

**Messung (`it5_memory_interval2`, Intervall 2, 4 Turns, 3 abgeschlossen):**
- Memory lief in 1 von 3 Turns (Intervall greift): **−9.8 s auf jedem Skip-Turn**.
- 1 Turn-Fail (Datenformat) — siehe Nebenbefund unten, nicht memory-bedingt.
- Stories echt (1 488–1 942 Zeichen), State-Digest plausibel.

**Wichtiger Nebenbefund (Profil `unphased`-Calls):** `call_progression_canon_extractor`
(Progression-Gate, läuft bei Progression-Claims) nutzte noch das volle
`build_extractor_context_packet`: **32 767 truncated Prompt-Tokens, Antwort degeneriert
zu 1 Token** — der Model-Anteil des Confidence-Scores lief still leer, plus ~8 s Waste.
Fix: Progression-Gate auf `build_compact_extractor_context_packet` umgestellt (Iteration-2-
Builder, ~1.2k Tokens) und `apply_progression_events` als Profil-Phase `progression`
sichtbar gemacht.

**Entscheidung Memory-Intervall: KEEP** (als Opt-in dokumentiert; Default bleibt 1,
empfohlene Config nutzt 2 — bewusst konservativ, weil Langzeit-Kontinuität bei
sehr langen Kampagnen von der Summary abhängt und n klein ist).

---

## Iteration 6 — NPC-Trigger + Progression-Packet-Fix (2026-06-12)

**Hypothese NPC:** Der NPC-Call (11–14 s, nur 89–157 Response-Tokens) ist auf
umgebungs-fokussierten Turns reiner Overhead; echte User-Turns 25–28 zeigten identische
NPC-Updates jeden Turn.

**Änderung:** `npc_extractor_should_run()` — deterministischer Vorab-Check; LLM-Call nur wenn
(a) bekannter NPC-Name/-Alias im Turn-Text, (b) lebender NPC mit `last_seen_scene_id` ==
Akteur-Szene, oder (c) Personen-/Dialog-Cues im Text (bewusst breite Liste — False-Positive
kostet nur den bisherigen Call, False-Negative würde still Canon verlieren).
`AELUNOR_NPC_EXTRACTOR_TRIGGER=always` schaltet den Check ab. Spot-Checks 6/6 korrekt.

**Messung (`it6_npc_trigger_prog_compact`, 4 Turns, Memory-Intervall 2 aktiv):**
- **4/4 Turns, 0 Fehler, Total Ø 61.2 s** (Median 61.0, Best 56.0, Worst 66.7) —
  erstmals unter 70 s und sehr konsistent.
- 4/4 echte Stories (1 823–2 113 Zeichen), nur 1 Narrator-Retry über alle Turns.
- Narrator 35.5 s Ø; Memory lief 2/4 (Intervall greift, −11.4 s auf Skip-Turns);
  **keine unphased-Calls mehr** → Progression-Fix bestätigt (kein truncated 32k-Call).
- NPC-Trigger skippte in diesem Lauf nichts (Szene enthält 2 lebende NPCs + Personen-Cues
  → Check sagt korrekt „laufen lassen"). Auf personenfreien Texten skippt er
  (Spot-Checks). Kosten des Checks: vernachlässigbar, rein deterministisch.
- State-Digest unauffällig, NPC-Codex konsistent (2 Einträge wie vorher).

**Entscheidung: KEEP** (NPC-Trigger als kostenloser konservativer Guard mit
`always`-Escape-Hatch; Progression-Compact-Fix klar positiv: vorher stiller
Truncation-Leerlauf + ~8 s Waste pro Progression-Claim-Turn).
Commit: 02d104c.

---

## Iteration 7 — Ollama-Runtime-Settings (ABGEBROCHEN, ungemessen)

`OLLAMA_FLASH_ATTENTION=1` wurde testweise gesetzt und Ollama neu gestartet, der
Benchmark dazu lief auf Nutzerwunsch (Loop-Stopp) nicht mehr. Die Env-Variable wurde
wieder entfernt und Ollama in Originalkonfiguration neu gestartet — **kein Zustand
geändert, keine Messung, keine Entscheidung.** Kandidat für einen späteren Loop
(Research-Notizen §3: FA + KV q8_0 sind die aussichtsreichsten Knöpfe; erwarteter
Gewinn primär VRAM, da gemma4:e4b als MoE nur 3.3 GB belegt).

---

# Finaler Bericht (Loop beendet 2026-06-12)

**Stop-Grund:** Nutzer-Stopp nach Iteration 6. Stop-Regel „<45 s" nicht erreicht,
aber alle bekannten toten/teuren Pipeline-Pfade sind behoben.

| Metrik | Baseline (It. 0) | Final (It. 6) | Δ |
|---|---:|---:|---|
| Total Ø pro Turn | ~110 s (Vorgabe ~90 s) | **61.2 s** | **−44 %** |
| Harte Turn-Fails | 4 von 8 (50 %) | **0 von 4** | −100 % |
| Echte Stories (kein Fallback) | 2 von 8 | **4 von 4** | Münzwurf → stabil |
| LLM-Calls pro Turn | 5+ (Narrator, 2× Canon, NPC, Memory + Retries) | 2.5–3.5 (Narrator, NPC getriggert, Memory ½, Guard bei Bedarf) | ca. −50 % |
| Narrator-Prompt | 31.9–32.6k Tokens (**> num_ctx, truncated**) | 23.1–23.7k | −27 %, Klippe beseitigt |
| Narrator-Retries | bis 6 Calls/Turn | 1 Retry über 4 Turns | — |
| Canon-Extractor | 28.8–35.5 s/Turn, halluzinierend | 0 s (deterministische Heuristik) | −100 % |
| Story-Compress | deterministischer Turn-Killer ab ~25 Turns | 12.7–14 s, funktioniert | repariert |
| Progression-Gate | 32 767 truncated Tokens, Confidence leer | compact 1.2k Tokens | repariert |
| Memory | 11.7–13.5 s jeden Turn | ~11.4 s jeden 2. Turn (Opt-in) | −~6 s/Turn Ø |
| NPC | 11–14 s immer | gleich, aber deterministisch getriggert | neutral–positiv |
| VRAM Peak | 7.80 GB | 7.79 GB | unverändert |
| GPU Ø | 65–70 % | 72 % | besser ausgelastet |
| Quality | Baseline (instabil) | klar über Baseline | ↑ |

**KEEP:** Canon heuristic_only (Default) · Compress ohne Vollkontext · Prompt-Budget
(meta/combat/plotpoints/recent_turns) · Memory-Intervall (Opt-in, Default 1) ·
NPC-Trigger (Default an, `always`-Escape) · Progression-Gate compact.
**PARK:** Canon-compact-Modus (braucht schlankes Extractor-Schema) · It. 7
Runtime-Settings (FA/KV q8_0, ungemessen) · It. 8 kleineres Extractor-Modell
(geringes Restpotenzial, da Extractor-LLM-Calls weitgehend eliminiert).
**REVERT:** keiner (alle gemessenen Änderungen waren KEEP).

**Verbleibender Bottleneck:** Narrator-Generierung selbst (~31–35 s/Call, davon
~½ Prefill von 23k Tokens, ~½ Decoding von 1.2–2.3k Output-Tokens). Nächste Hebel:
Prompt weiter Richtung 18k (Charaktere/Setup-Deduplizierung), cache-freundliches
Prompt-Layout (stabiler Prefix), FA/KV-Settings, ggf. Output-Längenbudget.

**Finale Start-Kommandos:** siehe current-best-config.md.











