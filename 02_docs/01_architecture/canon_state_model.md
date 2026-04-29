# Canon State Model

Canon ist die persistente, spielrelevante Wahrheit der Kampagne. Freier Story-Text allein ist nicht genug; relevante Aenderungen muessen strukturiert im State oder Patch landen.

## Bestandteile

- `state.meta`: Phase, Turn-Zaehler, Timing, Intro-State
- `state.characters`: Charakterzustand, Ressourcen, Progression, Szene
- `state.world`: Weltparameter, Elemente, Races, Beast Types
- `state.scenes` und `state.map`: Orte und Szenen
- `state.codex` / `state.npc_codex`: entdecktes Wissen
- `boards`: Plot Essentials, Authors Note, Story Cards, World Info, Memory Summary, Player Diaries
- `active_turns`: sichtbarer Turn-Verlauf

## Canon-Gate

Das Canon-Gate bewertet strukturierte Narrator-/Extractor-Patches:

- `committed`: ausreichend sicher und strukturiert
- `flagged`: sichtbar, aber Review-/Vorsichtssignal
- `skipped`: nicht sicher oder bereits strukturiert vorhanden

## Nicht brechen

- Turn-Record-Format
- Patch-Summary
- Reload-Konsistenz
- Claim-/Player-Token-Regeln
- Setup- und Phase-Transitions
