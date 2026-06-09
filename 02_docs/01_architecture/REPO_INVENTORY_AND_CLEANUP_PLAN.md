# Repo Inventory & Cleanup Plan

> Slice: `chore/repo-inventory-cleanup`
> Erstellt: 2026-06-09
> Zweck: Vollständiges, sicheres Repo-Inventar + Cleanup-Plan **vor** dem RAG-Slice.
> Dieser Plan ändert **keine Produktlogik** und implementiert **kein RAG**. Er ist
> primär dokumentierend. Lösch-/Archiv-Aktionen sind nur Kandidaten und werden in
> separaten, kleinen Folge-PRs ausgeführt.

**Ablageort-Begründung:** `02_docs/01_architecture/` existiert bereits und enthält
die übergeordnete Architektur-Doku (`system_overview.md`, `technical_debt.md`,
`turn_flow.md`, `persistence_strategy.md`). Ein Repo-Hygiene-/Inventar-Dokument
gehört thematisch dorthin und dupliziert keine bestehende Datei.

---

## 1. Executive Summary

**Aktiver Code-Stack** liegt vollständig unter `01_repo/aelunor-core/`:

- `app/` — FastAPI-Backend. `main.py` = Wiring/Composition. `routers/` = dünne
  HTTP-Adapter. `services/` = Domain-/Workflow-Logik mit 15 Subpaketen
  (`boards, campaigns, canon, characters, context, extraction, items, llm,
  migrations, progression, setup, sheets, state, turn, world`).
- `ui/` — aktive React/Vite-v1-UI (TSX/TS/CSS, `public/`-Assets).
- `tests/` — aktive Test-Suite (95 Dateien).
- `scripts/` — Hilfs-/Build-Skripte (27 Dateien).
- `app/static/` — statische Brand-/Icon-Assets (keine aktive Legacy-UI).

Begleitend: `02_docs/` (Produkt-/Architektur-Doku), `05_prompts/` (Prompt-Bibliothek),
`03_brand/` (Brand-Source-Assets), Root-Regeldateien (`AGENTS.md`, `AELUNOR_HANDOFF.md`,
`README.md`), `.agent_scripts/` (Token-effiziente Agent-Helfer).

**Vor RAG aufzuräumen (Kandidaten, nicht Pflicht in diesem Slice):**

1. `01_repo/aelunor-core/.runtime-verify/campaigns/camp_7734458b54.json` ist
   **falsch versioniert** — `.gitignore` ignoriert `**/.runtime-verify/`, die Datei
   wurde aber vorher (oder mit `-f`) getrackt. → einziger klarer Delete-Candidate
   (via `git rm --cached`, kein Löschen auf der Platte).
2. `_tmp/` (5× `.diff` + `tse_old.py`) — temporäre Patch-/Altdateien → Archiv/Delete.
3. `_analysis_for_chatgpt/` (5 MD) — historische Analyse-Doku → Archiv.
4. `01_repo/aelunor-core/reports/` (10 MD, `*_after_fix` / `*_clean` / `ai_smoke_*`)
   — historische Audit-Reports → Archiv.
5. `01_repo/aelunor-core/docs/` enthält gemischt aktive + historische Dokumente
   (z. B. `IST_ANALYSE_REHAUL_V1_2026-03-11.md`, `AELUNOR_STATUS_AUDIT.md`,
   `refactor_codex_log.md`) → teilweise Archiv.

**Was NICHT angerührt werden darf:**

- Gesamter aktiver Stack `01_repo/aelunor-core/{app,ui,tests,scripts}`.
- `app/services/turn_engine.py`, `app/services/state_engine.py` (aktive Kernlogik).
- `app/static/` Brand-/Icon-Assets, `ui/public/` Assets.
- `02_docs/`, `05_prompts/`, `03_brand/` (Quellen, kein Müll).
- Jegliche Runtime-Daten: `07_runtime/`, `**/.runtime/`, `**/.runtime-verify/` (Inhalt).
- Keine Secrets, keine `.env` (nur `.env.example` ist getrackt und ok).

**Status `.gitignore`:** Bereits umfassend (s. §6). In diesem Slice **keine Änderung
nötig** — alle geforderten Muster sind schon abgedeckt.

---

## 2. Repo Map

Zähler = Anzahl getrackter Dateien (`git ls-files`), 746 gesamt.

| Pfad | Zweck | Status | Begründung | Risiko |
|------|-------|--------|------------|--------|
| `01_repo/aelunor-core/app/` (255) | FastAPI-Backend, Domain-Kern | active | Aktiver Code-Stack, Kernlogik | hoch bei Änderung |
| `01_repo/aelunor-core/app/services/` | Domain-/Workflow-Logik, 15 Subpakete | active | Kernlogik inkl. turn/state engine | hoch |
| `01_repo/aelunor-core/app/routers/` | Dünne HTTP-Adapter | active | API-Oberfläche | hoch |
| `01_repo/aelunor-core/app/static/` (41 Assets) | Statische Brand-/Icons | active | Wird vom Backend ausgeliefert | mittel |
| `01_repo/aelunor-core/ui/` (235) | React/Vite-v1-UI | active | Aktive Frontend-Codebasis | hoch |
| `01_repo/aelunor-core/ui/public/` (38 Assets) | UI-Assets | active | Wird von Vite ausgeliefert | mittel |
| `01_repo/aelunor-core/tests/` (95) | Test-Suite | active | Schutz vor Regression | mittel |
| `01_repo/aelunor-core/scripts/` (27) | Hilfs-/Build-Skripte | active | Build/Tooling | mittel |
| `01_repo/aelunor-core/docs/` (6) | Core-nahe Doku, gemischt | docs / archive-candidate | Teils aktiv (WINDOWS_APP_BUILD), teils historisch | niedrig |
| `01_repo/aelunor-core/reports/` (10) | Historische Audit-Reports | archive-candidate | `*_after_fix`/`*_clean`/`ai_smoke_*` = Momentaufnahmen | niedrig |
| `01_repo/aelunor-core/.runtime-verify/` (1) | Runtime-Campaign-JSON | delete-candidate | `.gitignore` ignoriert Pfad → falsch versioniert | niedrig |
| `01_repo/aelunor-core/{requirements*.txt,docker-compose.yml,README.md,*.bat,.env.example}` | Build-/Run-Config | active | Produktiv benötigt | mittel |
| `02_docs/` (57) | Produkt-/Architektur-Doku | docs | Übergeordnete Doku, Quelle | niedrig |
| `02_docs/01_architecture/` (19) | Architektur-Diagramme/-Doku | docs | Aktive Referenz; Ablageort dieses Plans | niedrig |
| `02_docs/02_gameplay/` (1) vs `02_docs/02_features/` (17) | Doppelte `02_`-Nummerierung | needs-human-review | Nummern-Kollision, nur Struktur-Kosmetik | niedrig |
| `02_docs/technical/` (2) | Unnummerierte Technik-Notizen | needs-human-review | Bricht Nummern-Schema, inhaltlich ok | niedrig |
| `03_brand/` (31 Assets) | Brand-Source (Logos, Wallpapers) | active | Quell-Assets für UI/Static | niedrig |
| `05_prompts/` (2) | Prompt-Bibliothek + Registry | active | `prompt_registry.json` + Regeln | mittel |
| `10_tools/car-hub/` (3) | CAR-Workflow-Tooling | needs-human-review | Externes Tooling, nicht im Kern-Stack | niedrig |
| `.agent_scripts/` (3) | Token-effiziente Agent-Helfer | active | `repo_map/scan_errors/compact_test_output` | niedrig |
| `_analysis_for_chatgpt/` (5) | Historische Analyse-Doku | archive-candidate | Veraltete Code-Overviews/Roadmaps | niedrig |
| `_tmp/` (6) | Temp-Diffs + `tse_old.py` | delete-candidate / archive | Patch-Reste, klar temporär | niedrig |
| `AGENTS.md` (254 Z.) | Root-Agent-Regeln | active | Always-on-Regeln, evtl. zu lang (s. §7) | niedrig |
| `AELUNOR_HANDOFF.md` (70 Z.) | Handoff-Doku | active/docs | Kontext-Übergabe | niedrig |
| `README.md` (145 Z.) | Repo-Readme | active | Einstieg | niedrig |
| `.gitignore` | Ignore-Regeln | active | Bereits umfassend | niedrig |

Generierte/abgeleitete Ordner (`node_modules`, `.venv`, `__pycache__`, `dist`,
`build`, `coverage`, `.pytest_cache`, `07_runtime`, `**/.runtime*`) sind **nicht
getrackt** und korrekt ignoriert — daher nicht in der Tabelle.

---

## 3. Keep List (nicht löschen)

Aktive Bereiche, die unter keinen Umständen in diesem oder Folge-Slices entfernt
werden dürfen:

- `01_repo/aelunor-core/app/` (inkl. `main.py`, `routers/`, `services/`,
  `services/turn_engine.py`, `services/state_engine.py`, alle 15 Service-Subpakete)
- `01_repo/aelunor-core/app/static/` (Brand-/Icon-Assets)
- `01_repo/aelunor-core/ui/` (inkl. `ui/public/`, `ui/src/`)
- `01_repo/aelunor-core/tests/`
- `01_repo/aelunor-core/scripts/`
- `01_repo/aelunor-core/{requirements.txt, requirements-app.txt, docker-compose.yml, README.md, .env.example, Aelunor starten.bat}`
- `02_docs/` (gesamte Produkt-/Architektur-Doku)
- `05_prompts/` (`prompt_registry.json`, `living_world_character_rules.md`)
- `03_brand/` (Brand-Source-Assets)
- `.agent_scripts/` (Agent-Helfer)
- `AGENTS.md`, `AELUNOR_HANDOFF.md`, `README.md`, `.gitignore`

---

## 4. Archive Candidates

> **Nur Kandidaten — nicht ausführen.** Archiv statt Löschung, weil es sich um
> historische Erkenntnisse/Reports handelt, die nachvollziehbar bleiben sollten.
> Vorschlag Archiv-Wurzel: `99_archive/` (in `.gitignore` ist bereits
> `99_archive/legacy_data/` reserviert — Doku-Archiv käme parallel dazu).

| Aktueller Pfad | Vorgeschlagener Archivpfad | Warum Archiv statt Löschung | Risiko | Menschliche Entscheidung |
|----------------|----------------------------|------------------------------|--------|---------------------------|
| `_analysis_for_chatgpt/*.md` (5) | `99_archive/analysis/` | Historische Code-Overviews/Roadmaps, evtl. noch als Referenz nützlich | niedrig | Wird Analyse noch referenziert? |
| `01_repo/aelunor-core/reports/ai_smoke_*` (4) | `99_archive/reports/` | Smoke-Test-Momentaufnahmen mit `_after_fix`-Varianten | niedrig | Reproduzierbar oder dokumentationswert? |
| `01_repo/aelunor-core/reports/entity_guard_review*` (3) | `99_archive/reports/` | Review-Snapshots inkl. `_clean` | niedrig | Aktuell noch gültig? |
| `01_repo/aelunor-core/reports/world_bible_quality*` (3) | `99_archive/reports/` | Qualitäts-Snapshots inkl. `_clean` | niedrig | Aktuell noch gültig? |
| `01_repo/aelunor-core/docs/IST_ANALYSE_REHAUL_V1_2026-03-11.md` | `99_archive/docs/` | Datiertes Ist-Analyse-Dokument (V1, 2026-03-11) | niedrig | Durch neuere Doku ersetzt? |
| `01_repo/aelunor-core/docs/AELUNOR_STATUS_AUDIT.md` | `99_archive/docs/` | Status-Audit, vermutlich Momentaufnahme | niedrig | Aktuell? |
| `01_repo/aelunor-core/docs/refactor_codex_log.md` | `99_archive/docs/` | Logbuch eines abgeschlossenen Refactors | niedrig | Abgeschlossen? |
| `01_repo/aelunor-core/docs/codex_state_engine_dependency_inventory.md` | ggf. `02_docs/01_architecture/` | Inventar passt evtl. besser zur Architektur-Doku | niedrig | Aktiv gepflegt? |

> **Aktiv lassen** in `aelunor-core/docs/`: `WINDOWS_APP_BUILD.md` (Build-Anleitung)
> und `RULE_PROFILE_FOUNDATION.md` (vermutlich aktive Regel-Grundlage). Vor Archiv
> menschlich bestätigen.

---

## 5. Delete Candidates

> **Nur Kandidaten — nicht ausführen, außer eindeutig generiert + ungefährlich.**
> In diesem Slice wird **nichts gelöscht** (auch nicht das `.runtime-verify`-File),
> um die Guardrail „im Zweifel nicht löschen“ einzuhalten.

| Pfad | Warum löschbar | Wie verifiziert | Risiko |
|------|----------------|------------------|--------|
| `01_repo/aelunor-core/.runtime-verify/campaigns/camp_7734458b54.json` | Runtime-Campaign-Output; `.gitignore` ignoriert `**/.runtime-verify/` → eindeutig falsch versioniert. Entfernen via `git rm --cached` (Datei bleibt lokal auf Platte). | `git ls-files` zeigt nur diese eine Datei unter `.runtime-verify`; Ordner physisch vorhanden + ignoriert | niedrig — könnte theoretisch bewusst als Verify-Fixture dienen → vor `rm --cached` kurz bestätigen |
| `_tmp/se.diff`, `_tmp/se2.diff`, `_tmp/se3.diff`, `_tmp/te.diff`, `_tmp/tse.diff` | Temporäre Diff-Artefakte (Patch-Reste eines Refactors) | Dateiendung `.diff` im `_tmp/`-Ordner, kein Code-Import möglich | niedrig — Inhalt ggf. in PR-History gesichert |
| `_tmp/tse_old.py` | „old“-Snapshot einer Datei, nicht importiert | Name signalisiert Altstand; liegt in `_tmp/` | niedrig — vor Delete prüfen, ob Inhalt anderswo fehlt |

**Keine** generierten Build-/Cache-Artefakte (`__pycache__`, `.pytest_cache`,
`node_modules`, `dist`, `build`, `coverage`, `*.egg-info`) sind getrackt — verifiziert
per `git ls-files | grep -iE '(__pycache__|node_modules|/dist/|/build/|/coverage/|.pytest_cache|.egg-info)'`
→ **0 Treffer**. Hier gibt es also nichts zu löschen.

---

## 6. Ignore Candidates

Aktuelle `.gitignore` (Root) deckt bereits ab:

| Geforderte Regel | Vorhanden? |
|------------------|-----------|
| `.agent_tmp/` | ✅ (Zeile 44) |
| `**/.runtime/` | ✅ (Zeile 29) |
| `**/.runtime-verify/` | ✅ (Zeile 30) |
| `07_runtime/...` | ✅ (Zeilen 33–38, subdir-spezifisch) |
| `__pycache__/`, `*.py[cod]` | ✅ (Zeilen 1–2) |
| `.pytest_cache/` | ✅ (Zeile 3) |
| `.venv/`, `venv/` | ✅ (Zeilen 8–9) |
| `node_modules/` | ✅ (Zeile 10) |
| `dist/`, `build/` | ✅ (Zeilen 11–12) |
| `coverage/`, `.coverage`, `htmlcov/` | ✅ (Zeilen 6,7,15) |
| `*.log` + npm/yarn/pnpm-debug | ✅ (Zeilen 23–27) |
| IDE/OS (`.vscode/`, `.idea/`, `.DS_Store`, `Thumbs.db`, `desktop.ini`) | ✅ (Zeilen 16–20) |

**Ergebnis:** Keine sichere, eindeutige Ergänzung nötig → **`.gitignore` wird in
diesem Slice nicht geändert.**

> Hinweis: `**/.runtime-verify/` ist zwar ignoriert, untracked aber bestehende
> getrackte Dateien **nicht** automatisch. Das Entfernen der einen getrackten
> Datei (§5) ist eine separate, bewusste Aktion in Slice A — keine `.gitignore`-Frage.

---

## 7. Agent Context Hygiene

Gefundene Regel-/Kontext-Dateien (getrackt):

- `AGENTS.md` (Root, **254 Zeilen**) — Always-on-Regeln.
- `01_repo/aelunor-core/tests/AGENTS.md` — pfadbezogen (Tests).
- `01_repo/aelunor-core/ui/AGENTS.md` — pfadbezogen (UI).
- `01_repo/aelunor-core/ui/src/shared/design/AGENTS.md` — pfadbezogen (Design).
- `AELUNOR_HANDOFF.md` (Root, 70 Z.) — Handoff-Kontext.
- **Keine** `CLAUDE.md`, **keine** `.cursorrules`/`.cursor/`-Regeln gefunden.

Bewertung:

- **Root zu lang?** 254 Zeilen ist grenzwertig (Always-on-Kosten bei jedem Lauf).
  Tendenziell kürzbar, aber **kein** großer Rewrite in diesem Slice.
- **Pfadbezogene Regeln existieren bereits** für `tests/`, `ui/`, `ui/.../design/`
  — gute Struktur. Es fehlt eine nähere Regeldatei für `app/services/` (Kernlogik,
  Architekturgrenzen turn/state engine) — Kandidat für Slice C.
- **Empfehlung (dokumentiert, nicht ausgeführt):**
  - Architektur-Grenzen (main.py = Wiring, routers = dünn, services = Domain) als
    kurze Regel näher an `app/` / `app/services/` legen.
  - Lange Erklär-/Hintergrundabschnitte aus Root-`AGENTS.md` → `AELUNOR_HANDOFF.md`
    bzw. `02_docs/` verschieben (Handoff/Docs statt Always-on).
  - Doppelte Regeln zwischen Root und pfadbezogenen Dateien prüfen und deduplizieren.

Kein Rewrite jetzt — nur als **Slice C** vorgemerkt.

---

## 8. RAG Readiness

**Relevant für späteres RAG (Kandidaten-Quellen, read-only zu indexieren):**

| Bereich | Ort (aktiv) |
|---------|-------------|
| Campaign persistence | `app/services/campaigns/`, `app/services/persistence` |
| Chronicle / prior turn summaries | `app/services/diary.py`, Chronik-/Summary-Logik |
| World state | `app/services/world/`, `state_engine.py` |
| NPC facts | `app/services/extraction/npc_extractor.py`, `app/services/canon/` |
| Location facts | `app/services/world/`, `app/services/canon/` |
| Quest facts | `app/services/plotpoints.py` / progression |
| Prompt/Context builder | `app/services/context/`, `05_prompts/` |
| Turn pipeline | `app/services/turn_engine.py`, `app/services/turn/` |

> Die genauen Symbole sind vor RAG-Implementierung im RAG-Slice zu verifizieren —
> dieser Plan benennt nur die Bereiche, ändert nichts.

**NICHT in RAG indexieren (Ausschlussliste):**

- Secrets / `.env` (jede Variante).
- Runtime-Caches: `07_runtime/`, `**/.runtime/`, `**/.runtime-verify/`.
- Rohe Logs (`*.log`).
- Generierte Assets / Binärdateien (PNG/WEBP/SVG/ICO unter `static/`, `public/`, `03_brand/`).
- `node_modules/`, `dist/`, `build/`, `coverage/`, `__pycache__/`.
- Private/lokale Ordner: `14_private/`, `99_archive/legacy_data/`, `.agent_tmp/`.

---

## 9. Recommended Cleanup Slices

Kleine, sequentielle Folge-PRs (jeweils klar abgegrenzt):

### Slice A — Generated/misversioned artifacts cleanup
- **Ziel:** Falsch versionierte Runtime-Datei aus dem Index entfernen.
- **Erlaubte Dateien:** `git rm --cached 01_repo/aelunor-core/.runtime-verify/campaigns/camp_7734458b54.json` (Datei bleibt lokal). Ggf. `_tmp/`-Diffs.
- **Verbotene Dateien:** jeder aktive Code-Pfad, Assets, `02_docs`, `05_prompts`.
- **Tests/Checks:** `git status`, `git ls-files | grep .runtime-verify` → 0 Treffer danach.
- **Risiko:** niedrig.
- **Akzeptanzkriterien:** Keine getrackte Runtime-Datei mehr; Working tree clean; keine Produktdatei berührt.

### Slice B — Archive historical docs
- **Ziel:** Historische Reports/Analysen nach `99_archive/` verschieben.
- **Erlaubte Dateien:** §4-Kandidaten (`_analysis_for_chatgpt/`, `reports/`, datierte Docs).
- **Verbotene Dateien:** aktive Docs (`WINDOWS_APP_BUILD.md`, `RULE_PROFILE_FOUNDATION.md`), Code.
- **Tests/Checks:** Verschieben via `git mv`, Links/Referenzen prüfen.
- **Risiko:** niedrig.
- **Akzeptanzkriterien:** Keine toten internen Links; Archiv eindeutig benannt; menschliche Bestätigung je Datei.

### Slice C — Shrink/split agent rules
- **Ziel:** Root-`AGENTS.md` verschlanken; Architektur-Regeln näher an `app/services/`.
- **Erlaubte Dateien:** `AGENTS.md`, neue pfadbezogene `AGENTS.md`, `AELUNOR_HANDOFF.md`, `02_docs/`.
- **Verbotene Dateien:** jeglicher Produktcode.
- **Tests/Checks:** Manuelle Review (keine Logikänderung).
- **Risiko:** niedrig.
- **Akzeptanzkriterien:** Root kürzer + keine Regel verloren; Architekturgrenzen pfadnah dokumentiert.

### Slice D — Agent helper scripts
- **Ziel:** Fehlenden Helfer `.agent_scripts/compact_logs.py` ergänzen (dependency-light).
- **Erlaubte Dateien:** `.agent_scripts/*.py`.
- **Verbotene Dateien:** Produktcode.
- **Tests/Checks:** `python -m py_compile`.
- **Risiko:** niedrig.
- **Akzeptanzkriterien:** Offline, keine externen Deps, kompakte Ausgabe.
- **Status:** In diesem Slice teilweise vorgezogen (s. §10).

### Slice E — RAG foundation
- **Ziel:** RAG-Grundgerüst (eigener Slice, nicht hier).
- **Erlaubte Dateien:** neue RAG-Module unter `app/services/` (separat).
- **Verbotene Dateien:** Secrets, Runtime, Assets (s. §8-Ausschlussliste).
- **Tests/Checks:** Unit-Tests für Indexer; **keine** echten LLM-/Netzwerkaufrufe.
- **Risiko:** mittel–hoch (Kernnähe).
- **Akzeptanzkriterien:** Quellen aus §8 indexierbar; Ausschlussliste respektiert.

---

## 10. Commands Run

Read-only Inventar-Befehle (Outputs in `.agent_tmp/` zwischengespeichert, nur Aggregate gelesen):

| Befehl | Ergebnis (kurz) |
|--------|-----------------|
| `gh auth status` / `gh api user --jq .login` | Login = **Matchekk**, aktiv ✅ |
| `git config user.name/email`, `git var GIT_AUTHOR/COMMITTER_IDENT` | Matchekk + Matchekk-noreply-Mail ✅ |
| `git branch --show-current` | War `feature/rag-foundation` (= identisch mit `main`, 0 Commits Diff) |
| `git checkout -b chore/repo-inventory-cleanup` | Zielbranch von `main`/HEAD erstellt ✅ |
| `git status --porcelain` | Working tree clean ✅ |
| `git remote -v` | `Matchekk/Aelunor` ✅ |
| `git ls-files \| wc -l` | 746 getrackte Dateien |
| `git ls-files \| awk -F/ '{print $1}' \| uniq -c` | Top-Level-Verteilung (01_repo 635, 02_docs 57, 03_brand 31, …) |
| `git ls-files \| grep -oE '\.[a-z]+$' \| uniq -c` | Ext-Verteilung (324 .py, 102 .png, 93 .md, 89 .tsx, 77 .ts) |
| `git ls-files \| grep -iE '(__pycache__\|node_modules\|dist\|build\|coverage\|pytest_cache)'` | **0 Treffer** (keine getrackten Generate) |
| `git ls-files 01_repo/.../app/services` | 15 Domain-Subpakete |
| `git ls-files \| xargs du -k \| sort -rn \| head` | Größte Dateien = Wallpaper-PNGs (~2,4 MB), 3-fach (03_brand/ui/public/app/static) |
| `ls -d 07_runtime .runtime*` | Nur `.runtime-verify` physisch vorhanden (ignoriert) |

---

## Bekannte Beobachtungen / offene Punkte (needs-human-review)

1. **Wallpaper-Triplikation:** Identische ~2,4-MB-PNGs in `03_brand/wallpapers/`,
   `ui/public/brand/wallpapers/`, `app/static/brand/wallpapers/`. Vermutlich bewusst
   (Source → 2 Consumer). Dedupe nur nach Bestätigung — Assets werden aktiv ausgeliefert.
2. **Doc-Nummerierung:** `02_docs/02_gameplay/` vs `02_docs/02_features/` (Kollision)
   und unnummeriertes `02_docs/technical/` — reine Struktur-Kosmetik.
3. **`10_tools/car-hub/`:** Externes CAR-Tooling außerhalb des Kern-Stacks — Zugehörigkeit klären.
