# UI States

Jede wichtige Surface soll folgende Zustaende sauber behandeln:

- Loading: `Waiting*` Komponenten oder layout-stabile Platzhalter
- Empty: klare naechste Aktion, keine leeren Boxen
- Error: nutzerlesbarer Fehler ueber `deriveUserFacingErrorMessage`
- Disabled: Grund sichtbar, besonders im Composer
- Success: kurz und nicht modal blockierend
- Mobile: einspaltig, keine horizontalen Ueberlaeufe

## Kritische Edge Cases

- Keine aktive Session
- Stale lokale Credentials
- Keine Kampagnen in der lokalen Library
- Kein geclaimter Charakter
- Noch keine Story-Turns
- Keine Quests/Boards/Scene Members
- API-Fehler beim Resume, Turn Submit, Diary Save
- Sehr lange Story-Texte oder Charakternamen
