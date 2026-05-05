# Rule Profile Foundation

## Ziel

Aelunor soll nicht an ein einzelnes Regelwerk gebunden sein. Das Spielsystem bleibt für Story, State, Canon, Entities und Konsequenzen verantwortlich. Das Regelprofil entscheidet nur, wie unsichere Aktionen aufgelöst werden.

Leitlinie:

```text
Aelunor Core = Welt, Story, State, Canon, Entities
Rule Profile = Erfolgslogik für riskante Aktionen
```

## MVP-Profile

Für den ersten spielbaren Kern sind nur drei Profile als MVP-ready markiert:

1. `cinematic_ai`
   - keine sichtbaren Würfel
   - KI bewertet Risiko, Vorbereitung, Szene und Charakterzustand
   - niedrigste Einstiegshürde

2. `simple_d6`
   - einfacher W6
   - gut für schnelle, klare Zufallsentscheidungen
   - keine komplexe Fantasy-Regelmaschinerie

3. `d20_fantasy`
   - W20-Checks
   - Fantasy-RPG-Gefühl ohne volles 5e-System
   - bessere Basis für spätere 5e-Annäherung

## Spätere Profile

`five_e_inspired` und `custom` sind bewusst noch nicht MVP-ready.

Grund: Vollständige 5e- oder Custom-Regellogik würde zu früh zu viel Komplexität erzeugen. Diese Profile brauchen später eigene Validierung, UI-Erklärungen, Balancing und State-Contracts.

## Architekturregel

Kein Spielsystem-Code sollte direkt fragen, ob ein Profil 5e, W6 oder KI-basiert ist. Stattdessen soll später ein zentraler `ResolutionService` das aktive Regelprofil lesen und daraus ein strukturiertes Ergebnis erzeugen.

Zielstruktur:

```text
PlayerAction
→ GameAction
→ ResolutionService
→ ResolutionResult
→ StatePatch
→ Narration
```

## Nächster technischer Schritt

Dieses Dokument und `ui/src/shared/rules/ruleProfiles.ts` sind nur die erste, risikoarme Frontend-Foundation.

Als nächstes sinnvoll:

1. RuleProfile im World-Setup auswählbar machen.
2. Auswahl im Campaign State speichern.
3. Backend-seitiges RuleProfile-Modell ergänzen.
4. ResolutionService als eigene Domain-Schicht vorbereiten.
5. Turn Pipeline so umbauen, dass KI nur erzählt, aber nicht unkontrolliert die Erfolgslogik bestimmt.
