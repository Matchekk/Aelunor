# Multiplayer Split/Merge

Multiplayer ist derzeit session-/claim-basiert, nicht ein verteiltes Merge-System.

## Aktuelle Regeln

- Spieler authentifizieren sich lokal ueber `player_id` und `player_token`.
- Slots werden geclaimt oder freigegeben.
- Presence/SSE zeigt Aktivitaet, ist aber keine persistente Wahrheit.
- Blocking Actions verhindern ungueltige gleichzeitige Aktionen.

## Wichtige Faelle

- Host
- Geclaimter Spieler
- Fremder Spieler
- Unautorisierter Zugriff
- Reload/Reconnect

## Offene Richtung

Falls spaeter echtes Split/Merge noetig wird, muss es auf Campaign JSON und Turn-Records aufsetzen. Es darf Presence nicht zur Wahrheit machen.
