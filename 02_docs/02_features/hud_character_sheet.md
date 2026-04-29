# HUD and Character Sheet

## Aktive Surfaces

- Party-/Taktik-RightRail im Play Screen
- Character Drawer fuer Details
- Composer-Kontext fuer aktiven Actor

## UX-Ziel

Spieler sollen sofort erkennen:

- Wer handelt?
- In welcher Szene?
- Welche Ressourcen/Conditions sind relevant?
- Welche Progression oder Patches haben sich geaendert?

## Architekturregel

Character Sheet UI liest Backend-Snapshots. Sie darf Ressourcen, Claims oder Progression nicht lokal neu berechnen, wenn das Backend bereits die Wahrheit liefert.
