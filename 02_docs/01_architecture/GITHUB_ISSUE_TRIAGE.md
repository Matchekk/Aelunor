# GitHub Issue Triage

## Zweck

* Snapshot der offenen Issue-Landschaft von `Matchekk/Aelunor`.
* Hilft, RAG- und Architekturarbeit zu priorisieren, damit naechste Slices
  nicht gegen offene Strukturthemen laufen.
* Kein Ersatz fuer die GitHub Issues selbst; bei Konflikt gewinnt GitHub.

## Snapshot-Datum

* 2026-06-09.
* Quelle: `gh issue list --repo Matchekk/Aelunor --state open` (read-only).
* 18 offene Issues. Keines traegt aktuell Labels (siehe #41).

## Read-only-Regel

* In diesem Slice wurden Issues nur gelesen.
* Es wurden keine Labels gesetzt, keine Kommentare geschrieben, keine Issues
  geschlossen oder bearbeitet.
* Issue-Bodies sind hier nur zusammengefasst, nicht vollstaendig kopiert.

## Offene Issue-Gruppen

### A. Architektur-Blocker / Grundlagen

Fundament fuer alle Grosssysteme (Map, RAG, Gilden, Rivalen, Karma,
Split-Party). Status aller: offen.

* **#35 — Domaenengrenzen / Context Map / modularer Monolith.** Status: offen.
  Bedeutung: definiert Bounded Contexts (State, Turn, Narrator, Canon, Memory,
  Map, NPCs, Persistenz). RAG/DeepAelunor braucht klare Memory-Grenzen, damit
  Retrieval nicht quer durch Domaenen greift. Empfehlung: parallel zu RAG;
  Memory-Domaene fruehzeitig sauber schneiden.
* **#36 — Versionierte State-Modelle / Migrationen.** Status: offen.
  Bedeutung: ersetzt implizite `Dict[str, Any]`-Shapes durch versionierte,
  typisierte State-Vertraege. RAG mappt strukturierten State -> Dokumente;
  stabile State-Keys verhindern brechende Memory-Schemata. Empfehlung:
  parallel; jede neue Memory-Quelle an versionierten State binden.
* **#38 — Runtime-Wiring / DI ohne Globals/Bridges.** Status: offen.
  Bedeutung: explizite Composition Root statt `runtime_symbols()`-Bruecke.
  Ein RAG-Service sollte sauber injiziert, nicht global verdrahtet werden.
  Empfehlung: parallel; neuen RAG-Index-Service ueber Dependency-Objekte wiren.
* **#37 — Patch-Pipeline zu Commands/Domain-Events/Invariants.** Status: offen.
  Bedeutung: LLM-Patches werden zu validierten Commands/Events. Relevant fuer
  RAG indirekt: saubere Events sind spaeter gute Memory-Quellen. Empfehlung:
  spaeter; nicht blockierend fuer RAG-Foundation-Folgeslices.
* **#39 — LLM-Vertraege/Schemas/Prompt-Context als versionierte Contracts.**
  Status: offen. Bedeutung: Response-/Extractor-/Prompt-Context-Schemas als
  echte Contract-Schicht. Direkt RAG-nah: der retrievte Kontextblock muss in
  einen versionierten Prompt-Context passen. Empfehlung: parallel zu RAG;
  Context-Packet-Contract gemeinsam definieren.
* **#40 — Replaybare Turn-Pipeline / Golden Tests / Architektur-Smokes.**
  Status: offen. Bedeutung: reproduzierbare Turn-Szenarien ohne echte LLMs.
  Wichtig, um RAG-Kontext deterministisch zu testen. Empfehlung: parallel;
  RAG-Context-Builder ueber Golden Fixtures absichern.
* **#42 — Architecture Decision Review (Stack).** Status: offen.
  Bedeutung: prueft FastAPI-Stack; vorlaeufiges Ergebnis = FastAPI bleibt,
  Modernisierung liegt bei State-Versionierung, typed Models und
  Command-/Event-Pipeline. Empfehlung: vor grossen RAG-/Stack-Entscheidungen
  als Leitplanke lesen; kein Framework-Wechsel geplant.

### B. Roadmap-/Issue-Hygiene

* **#41 — Roadmap-/Issue-Hygiene mit Labels, Prioritaeten, Duplikatkontrolle.**
  Status: offen.
  * Warum wichtig: 18 Issues, keine Labels, gemischte Scopes (Architektur, UI,
    Backend, Produktidee). Ohne Hygiene greifen Agents das falsche Issue auf
    und Reihenfolge/Prioritaet bleiben unklar.
  * Vermutlich zu pruefende Ueberschneidungen: RAG (#2 vs. die bereits gebaute
    Foundation in `app/services/rag/`); State-/Domain-Themen (#35/#36/#38);
    Memory-nahe Future Features (#15/#33/#10) mit RAG-/State-Bedarf; mehrere
    System-Rehauls (#34 Map, #14 Inventar, #23 Waffen) mit grossem Scope.
  * Empfehlung: separater, ausdruecklich beauftragter Issue-Hygiene-Slice
    (`chore(docs)` / GitHub-Labeling), getrennt von Produktarbeit.

### C. Future Features mit RAG-/State-Relevanz

Nicht blockierend fuer die RAG-Foundation-Folgeslices, aber relevant fuer
spaetere Memory-Schemata und State-Vertraege. Status aller: offen.

* **#34 — Map-System-Rehaul (KI-Karte, Fog of War, Discovery).** Bedeutung:
  echtes spielbares Kartensystem ueber `state.map`. Abhaengigkeit: stark
  State-getrieben; Orte/Discovery sind spaeter gute RAG-Quellen (Location
  facts). Empfehlung: nach State-Versionierung; Memory-relevant, nicht
  blockierend.
* **#33 — Karma-/Ruf-/Standing-System.** Bedeutung: moralische Konsequenzen,
  Fraktions-/Gildenstanding, NPC-Beziehungen langfristig. Abhaengigkeit:
  State-Versionierung; Standing-Historie ist RAG-Memory-Kandidat. Empfehlung:
  nach #36; relevant fuer Memory-Schema.
* **#32 — Split-Party / getrennte KI-Kontexte.** Bedeutung: getrennter
  GM-Kontext pro Gruppe/Ort. Abhaengigkeit: stark Context-/Retrieval-nah —
  pro-Gruppe-Kontext beruehrt direkt RAG-Filterung (campaign_id + Szene/Ort).
  Empfehlung: erst nach stabiler RAG- und Context-Schicht.
* **#23 — Waffen-/Techniken-System.** Bedeutung: Moves, Stile, Synergien,
  Progression ueber `weapon_profile`/Skills. Abhaengigkeit: primaer State, RAG
  nur leicht (Rules/Lore-Snippets). Empfehlung: nicht RAG-blockierend.
* **#18 — Zeit-System-Ausbau (Kalender, Tagesphasen, Reisen, Fristen).**
  Bedeutung: vollwertiges Kampagnen-Zeit-System ueber `meta.world_time`.
  Abhaengigkeit: State; Zeit-Stempel verbessern spaeter Memory-Salience/
  Sortierung. Empfehlung: nicht RAG-blockierend; potenzieller Duplikat-Check
  (#41).
* **#15 — Persoenlichkeitssystem (PCs/NPCs).** Bedeutung: Verhalten,
  Dialogstil, Beziehungen, Entwicklung ueber `bio.personality`. Abhaengigkeit:
  State + RAG (NPC facts sind Kern-Memory-Quelle). Empfehlung: nach
  RAG-Memory-Mapper; relevant fuer NPC-Memory-Schema.

### Weitere offene Issues (nicht im Triage-Fokus)

* #14 Inventar-/Ausruestungs-Rehaul, #10 Rivalen-/Nemesis-System,
  #3 Gilden-System, #2 lokale RAG-Schicht (Ziel-Issue der RAG-Arbeit).
* #2 ist das Dach-Issue fuer die echte RAG-Schicht; die gemergte Foundation
  (`app/services/rag/`, PR #46) ist dessen erste deterministische Vorstufe.

## Priorisierte naechste Arbeit

1. RAG Structured Memory Mapper (strukturierter State -> `RAGDocument`).
2. RAG Index Builder / In-Memory-Index (Service, kein Vector-DB).
3. Context-Preview-Service/API (Router ruft nur Service).
4. LLM-Context-Contract-Alignment mit #39.
5. Replay-/Golden-Tests fuer RAG-Kontext mit #40.
6. State-Versionierung / Context Map weiterfuehren mit #35/#36.

## Issue-Aktionsvorschlaege

Nur Vorschlaege; in diesem Slice nicht ausgefuehrt.

* Label-Vorschlag (Beispiele): `architecture`, `rag`, `testing`, `roadmap`,
  `future-feature`, `state`, `llm-contract`, `ui`, `map`, `needs-triage`.
* Moegliche Duplikat-/Ueberschneidungsgruppen:
  * RAG: #2 vs. bereits gebaute Foundation in `app/services/rag/`.
  * State/Architektur: #35, #36, #38 (eng verzahnt, klare Reihenfolge noetig).
  * Memory-nahe Features: #15, #33, #10 (gemeinsames NPC-/Standing-Memory).
  * Grosse Rehauls: #34, #14, #23 (Scope ggf. in Teil-Issues schneiden).
* Spaeter zu aktualisieren/kommentieren (nach Auftrag): #2 (auf Foundation
  verweisen), #41 (Labels umsetzen), #39/#40 (RAG-Bezug ergaenzen).
* Keine GitHub-Aktionen ausfuehren ohne ausdruecklichen separaten Auftrag.
