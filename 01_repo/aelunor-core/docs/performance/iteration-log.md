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







