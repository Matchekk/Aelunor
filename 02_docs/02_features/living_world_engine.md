# Living World Engine (P0/P1)

Die Living World Engine erweitert World Bible v1 kompatibel um kausale
Welt-Systeme. Ziel ist keine isolierte Lore, sondern Ursache, Druck, Spuren,
Konsequenzen und Orte mit Gedaechtnis. Sie ist ein **additiver Block** in der
bestehenden World Bible, kein paralleles System.

## Zweck

Eine Welt wirkt lebendig, wenn lokale Probleme aus groesseren Druckwellen
entstehen:

```
Theme -> Root Cause -> World Laws -> Ripple Effects -> Settlements
-> Cultures -> Factions -> NPCs -> Local Problems -> Quest Hooks
-> Clues -> Consequences -> Escalation -> Memory
```

Grundregel: niemals isolierte Lore generieren, sondern Systeme, Druck, Spuren
und Konsequenzen.

## State-Pfad

```text
campaign["state"]["world"]["bible"]["living_world"]
```

Die World Bible bleibt `version: 1`. `living_world` ist optional. Alte Saves
ohne den Block bleiben ladbar; `normalize_world_bible` setzt eine deterministische
Default-Shape.

## P0/P1-Shape

Unter `living_world`:

- `theme_engine` — `primary_theme`, `secondary_themes`, `theme_questions`,
  `theme_antipatterns`
- `root_cause` — `type` (mundane|political|ecological|metaphysical|divine|
  technological|unknown), `public_surface`, `hidden_truth`, `scale`
  (local|regional|continental|cosmic), `known_to_players`
- `world_wound` — `old_break`, `current_echoes`, `false_explanations`,
  `visible_traces`
- `world_laws_extended` — Liste aus `id`, `principle`, `cost`, `limit`,
  `social_effect`, `failure_mode`
- `ripple_engine` — `root_to_ripples` (cause/primary/secondary/local_symptom/
  quest_hooks/clues/if_players_do_nothing), `active_pressure_points`,
  `escalation_style`
- `settlement_logic` — `default_questions`, `settlement_rules`,
  `institution_rules`, `ritual_rules`
- `faction_logic` — `default_questions`, `pressure_rules`, `reaction_rules`
- `plot_logic` — `quest_design_rules`, `clue_rules`, `anti_railroad_rules`,
  `consequence_rules`

## Ableitung aus dem Setup

`generate_world_bible_fallback` leitet `living_world` deterministisch aus
vorhandenen Setup-Antworten ab (keine LLM-Calls, stabile Seeds):

- `theme` -> `theme_engine.primary_theme`
- `central_conflict` -> `root_cause.public_surface` (+ verdeckte Ursache)
- `world_laws` -> `world_laws_extended`
- `world_structure` -> Settlement-/Plot-Logic
- `factions_raw` -> Faction-Logic `pressure_rules`
- `taboos` -> `theme_antipatterns` / Grenzen

## Wie die World Bible Summary es nutzt

`build_world_bible_prompt_summary` haengt wenige kompakte Zeilen an:

```text
Living World: Theme=<primary>; <Root Cause bekannt ODER hidden pressure>.
Ripples: <cause -> ripple>; ...
Settlement Logic: <Regel>.
Faction Logic: <Regel>.
Quest Logic: Keine harte Hauptquest aufzwingen; lokale Symptome, Hinweise und
Konsequenzen ausspielen.
```

`root_cause.hidden_truth` wird **nie** in die Summary geschrieben. Der Root Cause
wird nur namentlich genannt, wenn `known_to_players=true`, sonst nur als
allgemeiner "hidden pressure".

## Bewusst nicht implementiert (P2/P3)

- kein RAG, keine echten LLM-Calls in der Ableitung
- kein neues Worldbuilding-Frontend
- keine generative NPC-/Settlement-Datenbank
- keine Turn-seitigen Ripple-Patches (Profile-/World-Updates nach Turns sind
  nur vorbereitet, nicht gebaut)
- keine Pflicht-Hunderte-Felder; alles optional mit deterministischem Default

## Anti-Patterns

- Lore-Dump statt Ursache ueber Spuren und Konsequenzen
- isolierte Lore ohne Druck oder Gedaechtnis
- singulaere Hauptquest aufzwingen, wenn Spieler andere Spuren verfolgen
- Orte/Fraktionen ohne Existenzgrund, Ressource, Angst, Status, Mangel
