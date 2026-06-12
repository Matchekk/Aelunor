# Research-Notizen: Optimierung lokaler Ollama-LLM-Pipeline (gemma-Klasse 4B–12B, RTX-Consumer-GPU, Windows)

Stand: 2026-06-12. Fokus: umsetzbare Befunde für Turn-Latenz, Schema-Stabilität und Kontextbudget.

---

## 1. Ollama Structured Output (format=json/Schema): Performance & Fallstricke

- Seit Ollama v0.5 wird aus dem übergebenen JSON-Schema eine Grammatik generiert; der Sampler erlaubt pro Schritt nur Tokens, die ein gültiges JSON-Dokument fortsetzen ([Daniel Clayton](https://blog.danielclayton.co.uk/posts/ollama-structured-outputs/), [Ollama Blog](https://ollama.com/blog/structured-outputs)).
- Wirkung ist modellabhängig: Für schwache/kleine Modelle wirkt Constrained Decoding als Sicherheitsnetz; bei stärkeren (Reasoning-)Modellen kann harte Grammatik die Qualität massiv drücken (Benchmark-Beispiel: 92,5 % → 35 % Accuracy) ([TOON-vs-JSON-Benchmark, arXiv](https://arxiv.org/pdf/2603.03306)).
- Bekanntes Degenerationsmuster: gemma-Modelle geraten bei **langen Freitext-String-Feldern unter Schema-Zwang** in Wortwiederholungs-Schleifen (60–100 % Reproduktionsrate, `repeat_penalty` wirkungslos); betrifft v. a. dichte große gemma-Varianten ([ollama/ollama#15502](https://github.com/ollama/ollama/issues/15502)). Deckt sich mit dem beobachteten gemma4:12b-SAGEN/STORY-Degenerieren.
- Komplexe Schemas (tiefe Verschachtelung, `anyOf`/`oneOf`, Arrays mit eigenen Item-Schemas) sind unzuverlässig bzw. teuer in der Grammatik-Erzeugung ([Serverman-Guide](https://www.serverman.co.uk/ai/ollama/ollama-structured-json-output/)).
- Offizielle Best Practices: Temperature 0, Schema **zusätzlich als Text in den Prompt** legen ("grounding"), Schemas via Pydantic/Zod definieren und zur Validierung wiederverwenden ([Ollama Docs](https://docs.ollama.com/capabilities/structured-outputs)).

**Konsequenz für Aelunor:** Narrator-Schema flach halten, lange Freitextfelder (Story/SAGEN-Prosa) aus dem Schema-Zwang herausnehmen (zweistufig: Prosa frei generieren, Metadaten separat constrained), Schema immer auch im Prompt zitieren, Temperature 0 für Extraktor-Rollen.

## 2. Kontextlänge vs. Prompt-Eval-Kosten & Prompt-Caching

- Prompt-Processing (Prefill) skaliert spürbar mit der Promptlänge; gemessene Beispiele: ~1883 tok/s bei 8k Kontext vs. ~425 tok/s bei 128k ([LocalLLM.in](https://localllm.in/blog/llamacpp-vram-requirements-for-local-llms), [Medium: 5 llama.cpp-Parameter](https://xhinker.medium.com/the-5-llama-cpp-parameters-that-actually-matter-9f2c38b53755)).
- KV-Cache-VRAM wächst linear mit `num_ctx` (~1 KB/Token Größenordnung bei kleinen Quants); zu großes `num_ctx` kostet VRAM auch ohne Nutzung und kann Layer auf die CPU verdrängen ([LocalLLM.in](https://localllm.in/blog/llamacpp-vram-requirements-for-local-llms)).
- Ollama nutzt hash-basiertes Prefix-Matching: Teilt ein Request einen **byte-identischen Prefix** mit dem vorigen, wird nur der neue Teil prefilled (TTFT-Reduktion erheblich) ([DeepWiki KV Cache](https://deepwiki.com/ollama/ollama/5.3-kv-cache-system), [J. Ding: KV Cache & Scheduling](https://jonathanding.github.io/llm-learning/en/articles/ollama-kv-cache-scheduling/)).
- Cache-Invalidierung: jede Änderung früh im Prompt (Timestamp, rotierende Abschnitte), Context-Shift bei vollem Fenster (Positionsindizes verschieben sich), `num_ctx`-Wechsel (Reallokation), und `OLLAMA_NUM_PARALLEL` (teilt den Kontext auf Slots auf) ([Leanpub: Prompt Caching](https://leanpub.com/read/ollama/prompt-caching), [J. Ding](https://jonathanding.github.io/llm-learning/en/articles/ollama-kv-cache-scheduling/)).
- Modellwechsel/-entladung verwirft den Cache komplett; Caching wirkt nur, solange das Modell geladen bleibt (`keep_alive`).

**Konsequenz für Aelunor:** Prompts cache-freundlich layouten — stabiler Teil (Systemprompt, Welt-Kanon, Regeln) zuerst und unverändert lassen, volatile Teile (Turn-Delta, Zeit, Zufalls-IDs) ans Ende; pro Rolle festes `num_ctx` (32k) nie zwischen Calls wechseln; Rollenwechsel zwischen Modellen minimieren, da jeder Wechsel den Prefix-Cache killt.

## 3. KV-Cache-Quantisierung & Flash Attention

- `OLLAMA_FLASH_ATTENTION=1` ist Voraussetzung für KV-Quantisierung; FA selbst bringt ~1,3–2× schnelleres Prompt-Processing und weniger KV-VRAM, praktisch ohne Nachteil ([smcleod.net](https://smcleod.net/2024/12/bringing-k/v-context-quantisation-to-ollama/), [Markaicode](https://markaicode.com/howto/how-to-configure-llamacpp-production-settings/)).
- `OLLAMA_KV_CACHE_TYPE=q8_0` halbiert den KV-VRAM (Beispiel 8B@32k: ~6 GB F16 → ~3 GB), Perplexity-Anstieg nur 0,002–0,05 — in der Praxis nicht messbar ([smcleod.net](https://smcleod.net/2024/12/bringing-k/v-context-quantisation-to-ollama/), [ModelPiper](https://modelpiper.com/blog/ollama-kv-cache-quantization)).
- `q4_0` spart ~66–75 %, aber mit spürbarer Qualitätsminderung (Perplexity +0,2–0,25) — riskant für lange, kohärente Erzähltexte ([smcleod.net](https://smcleod.net/2024/12/bringing-k/v-context-quantisation-to-ollama/)).
- Kompatibilitäts-Caveats: nicht für Embedding-Modelle, Vorsicht bei Vision/Multimodal und Modellen mit vielen Attention-Heads; nicht jede Architektur unterstützt FA+KV-Quant gleichermaßen ([ollama/ollama#13337](https://github.com/ollama/ollama/issues/13337)).
- Speed-Effekt der Quantisierung selbst ist neutral (K-Quant minimal schneller, V-Quant minimal langsamer) — Gewinn ist primär VRAM → mehr Kontext oder größeres Modell auf derselben GPU.

**Konsequenz für Aelunor:** `OLLAMA_FLASH_ATTENTION=1` + `OLLAMA_KV_CACHE_TYPE=q8_0` als Kandidat für Iteration 7 (Windows: User-Env-Variablen, Ollama-Dienst neu starten); damit wird 32k-`num_ctx` für die gemma-Klasse auf RTX-VRAM deutlich billiger. `q4_0` nicht für den Narrator verwenden; vorher kurz per Smoke-Run verifizieren, dass gemma4 mit FA+q8_0 sauber läuft.

## 4. RAG-Kontextkompression & Prompt-Budgeting für lange Sessions

- Bewährtes Muster für lange Agent-/Game-Sessions: **strukturierte Zusammenfassung alter Turns + verbatim die letzten N Turns** — aktuelle Präzision plus alte Historie zu planbaren Kosten ([SurePrompts](https://sureprompts.com/blog/context-compression-techniques), [BuildMVPFast](https://www.buildmvpfast.com/blog/context-compression-techniques-fewer-tokens-llm-optimization-2026)).
- Token-Budget **deterministisch vor jedem Call erzwingen** (harte Sektion-Budgets: System / Kanon / Historie / Output-Reserve), nicht auf das Modell oder den Provider verlassen; 10–20 % Puffer unterm Limit lassen ([SitePoint](https://www.sitepoint.com/optimizing-token-usage-context-compression-techniques/)).
- Memory-Buffering: roh sammeln, alle ~10 Nachrichten zusammenfassen; hierarchische/gestufte Summaries für sehr lange Horizonte (Summary of Summaries) — Achtung kumulative Fehler ([Agenta](https://agenta.ai/blog/top-6-techniques-to-manage-context-length-in-llms)).
- Kompression dort zuerst, wo Information am wenigsten wert ist (Dokumente/alte Turns vor Kern-Instruktionen); Deduplikation/Redundanzentfernung bringt typ. 40–60 % Tokenersparnis ([Towards Data Science](https://towardsdatascience.com/rag-isnt-enough-i-built-the-missing-context-layer-that-makes-llm-systems-work/), [Agenta](https://agenta.ai/blog/top-6-techniques-to-manage-context-length-in-llms)).
- Warnung: Über-Kompression ist „silent" — das Modell antwortet selbstbewusst auf weggekürztem Material; Kompressionsstufen gegen Regression-Smokes testen ([SurePrompts](https://sureprompts.com/blog/context-compression-techniques)).

**Konsequenz für Aelunor:** Narrator-Prompt-Klippe (~25 Turns) mit festen Sektion-Budgets + rolling Summary lösen: letzte 3–5 Turns verbatim, ältere Turns als komprimierte Chronik; Budget-Check deterministisch im Code vor jedem LLM-Call, Compress-Schritt ohne Voll-Kontext (nur Delta + bisherige Summary) füttern.

## 5. Kleine Modelle für JSON-Faktenextraktion

- Für strukturierte Extraktion gilt: Temperature 0,0–0,2; niedrige Temperatur macht Output **konsistent, nicht korrekter** — Korrektheit kommt aus Prompt + Input-Eingrenzung ([Tetrate Temperature Guide](https://tetrate.io/learn/ai/llm-temperature-guide), [arXiv 2402.05201](https://arxiv.org/pdf/2402.05201)).
- Kurzer Kontext ist messbar besser: Halluzinations-/Fabrikationsraten steigen mit Kontextlänge deutlich; bei sehr langen Kontexten bleibt kein Modell unter 10 % Halluzination ([arXiv 2603.08274](https://arxiv.org/pdf/2603.08274)).
- Generische „extrahiere Fakten"-Anweisungen reichen nicht; zuverlässig wird es erst mit konkreten Beispielen, klarer Output-Definition und expliziten Markern, wo relevante Aussagen beginnen/enden ([arXiv 2511.05320](https://arxiv.org/pdf/2511.05320)).
- Schema-erzwungene Generierung (Jsonformer-artig / Ollama format) plus nachgelagerte Pydantic-Validierung ist das Standard-Pattern; Schema klein und flach halten ([Simon Willison: LLM Schemas](https://simonwillison.net/2025/Feb/28/llm-schemas/)).
- Deterministisches Preprocessing vor dem LLM (Regex/Heuristik filtert Kandidaten-Sätze, Deduplikation, nur **Delta-Text** statt Voll-State) reduziert Input, Kosten und Fehlerfläche — das LLM klassifiziert/normalisiert nur noch.

**Konsequenz für Aelunor:** Den toten Canon-Extraktor (Packet zu groß) nicht reparieren, sondern umbauen: Extraktion ausschließlich aus dem Turn-Delta (neuer Narrator-Output + Spieleraktion), nicht aus dem Voll-State; kleines Modell (4B-Klasse), Temperature 0, flaches Schema, Few-Shot-Beispiele — damit bleibt der Extraktor-Prompt dauerhaft unter ~2–4k Tokens.

## 6. JSON-Repair: deterministisch vs. LLM

- Erste Verteidigungslinie immer deterministisch: `json.loads()` versuchen, bei `JSONDecodeError` Fallback auf `json_repair` (fixt fehlende Quotes/Kommata/Klammern, Prosa-Reste, abgeschnittene Werte) ([json_repair GitHub](https://github.com/mangiucugna/json_repair), [PyPI](https://pypi.org/project/json-repair/)).
- LLM-basierte Repair-/Retry-Calls sind die teuerste Option: zusätzliche volle Inferenz (lokal: nochmal komplette Turn-Latenz), unzuverlässig, und bei systematischen Schema-Fails endlos wiederholbar ([Medium: Malformed JSON Handling](https://medium.com/@sd24chakraborty/handling-and-fixing-malformed-json-in-llm-generated-responses-f6907d1d1aa7), [Medium: json_repair Tutorial](https://medium.com/@yanxingyang/tutorial-on-using-json-repair-in-python-easily-fix-invalid-json-returned-by-llm-8e43e6c01fa0)).
- Sinnvolle Eskalationskette: (1) Parse → (2) `json_repair` → (3) Schema-Validierung (Pydantic) mit Default-Auffüllung → (4) erst dann **ein** gezielter LLM-Retry mit Fehlermeldung im Prompt; mehr Retries lohnen lokal fast nie.
- `json_repair` ist heuristisch — kann semantisch „falsch reparieren"; daher Repair-Ergebnis immer gegen das Schema validieren und Repair-Fälle loggen (Symptom-Monitoring für Prompt-/Schema-Probleme) ([json_repair GitHub](https://github.com/mangiucugna/json_repair)).
- Häufigste Repair-Ursache lokal ist **Truncation** (Token-Budget erschöpft, oft durch Repetition-Loops, s. Thema 1) — dort ist die Wurzelbehebung (Schema/`num_predict`) wirksamer als jede Reparatur.

**Konsequenz für Aelunor:** Schema-Fails primär per deterministischer Kette abfangen (parse → json_repair → Pydantic-Defaults) statt per Narrator-Retry; LLM-Retry nur als letzte Stufe mit max. 1 Versuch und Fehlerkontext; Repair-Rate als Metrik im Turn-Profiling beobachten, denn steigende Repair-Quote zeigt Schema-/Prompt-Drift früher als Latenz.
