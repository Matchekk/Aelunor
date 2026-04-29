# ADR-004 Split Travel Rules

## Status

Proposed.

## Kontext

Spieler koennen potenziell in unterschiedlichen Szenen/Orten agieren. Der aktuelle MVP behandelt Szenenfilter und Scene Membership, aber kein komplexes Reise-/Split-Merge-System.

## Entscheidung

Split Travel wird erst ausgebaut, wenn der Kernflow stabil bleibt. Bis dahin sind Szene, Map und Party-Zuordnung strukturierte Hinweise, aber kein separates Simulationssystem.

## Konsequenzen

- Presence bleibt Live-Sync, nicht Weltwahrheit.
- Scene Membership muss reload-sicher sein.
- Split-/Merge-Regeln brauchen Tests fuer Host, beteiligte Spieler, fremde Spieler und unautorisierte Zugriffe.
