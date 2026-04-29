# Combat Philosophy

Combat ist im MVP ein Story- und State-Kontext, kein separates Taktikspiel.

## Prinzipien

- Kampf soll Story-Turns nicht ersetzen.
- Ressourcen, Conditions und Szenenstatus muessen sichtbar bleiben.
- Combat-State darf keine ungueltigen Zwischenzustaende nach Retry/Undo/Reload erzeugen.

## Aktueller Zustand

`state.meta.combat` existiert als strukturierter Bereich. Weitere Kampfsysteme sollten nur ausgebaut werden, wenn sie den Kernloop direkt verbessern.
