# Turn Flow

Der Turn-Flow ist der Kern des Spiels. Er muss reload-sicher, claim-sicher und canon-kompatibel bleiben.

## Normaler Ablauf

1. Spieler schreibt im v1-Composer einen Beitrag.
2. Frontend sendet `POST /api/campaigns/{campaign_id}/turns` mit Actor, Mode und Text.
3. Backend prueft Player-Credentials, Claim, Phase und Blocking Actions.
4. Turn-Service ruft Turn-/Narrator-Engine.
5. Turn-Engine nutzt explizite Ports fuer LLM, Extraction/Canon/NPC, Progression/Skill/Codex, Pacing/Timing und Attribute-Meta.
6. Narrator erzeugt Story-Text und optional strukturierte Patches.
7. Canon-Gate entscheidet, welche strukturierten Aenderungen in den Patch-State duerfen.
8. Campaign JSON wird persistiert.
9. Response liefert `turn_id`, `trace_id` und neuen Campaign Snapshot.
10. Presence/SSE informiert andere Clients ueber Sync.

## Modi

| UI-Modus | Zweck |
| --- | --- |
| `do` / TUN | Spieleraktion |
| `say` / SAGEN | Dialog |
| `story` / STORY | erzaehlerischer Beitrag |
| `canon` / CANON | gezielte Welt-/State-Aenderung |
| `context` / KONTEXT | Kontextabfrage ohne Story-Turn |

## Fehlerpfade

- Fehlende Claims blockieren Turn-Submit.
- Nicht aktive Kampagnenphase blockiert neue Turns.
- Laufende Blocking Actions sollen sauber auslaufen oder geloescht werden.
- LLM-/Extractor-Fehler duerfen Tests nicht erreichen; automatisierte Tests nutzen Fakes.
- Canon-Gate kann Patches committen, flaggen oder skippen.
- Legacy-`runtime_symbols()`-Wiring darf nicht als neue Turn-API wachsen; neue Abhaengigkeiten gehoeren in kleine Ports.

## Regressionen, die Tests abdecken sollten

- Setup -> Claim -> Character Setup -> Play -> Turn -> Persist/Reload
- Retry/Undo/Edit fuer letzte Turns
- Canon/Patch-State vor und nach Reload
- Player-Token/Claim-Zugriff fuer Host, eigener Spieler, fremder Spieler, unautorisiert
- SSE/Presence reconnect und Blocking Action Cleanup

## Turn-Port-Stand

- `TurnLlmDependencies`: Ollama-/LLM-Client-Wrapper und JSON-/Schema-Calls.
- `TurnExtractionDependencies`: Extractor-Kontext, Canon-/NPC-Extractor, Conflict-/Quarantine-Helfer.
- `TurnProgressionDependencies`: Progression-, Skill- und Character-Change-Events.
- `TurnCodexDependencies`: Codex-Trigger sammeln und anwenden.
- `TurnPacingDependencies`: Pacing Profile, Milestones, Turn-Budget und Timing-EMA.
- `TurnAttributeDependencies`: Attribute-Influence-Meta-Normalisierung.

Naechster sicherer Refactoring-Schritt: `state_engine.runtime_symbols()` um die
jetzt explizit portierten Turn-Abhaengigkeiten reduzieren und danach
Turn-Materialization/Patch-Grenzen weiter isolieren.
