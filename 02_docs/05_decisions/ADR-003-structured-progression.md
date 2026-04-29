# ADR-003 Structured Progression

## Status

Accepted.

## Entscheidung

Progression wird als strukturierter Charakter-State gefuehrt und nicht nur aus Narrator-Text abgeleitet.

## Konsequenzen

- Extractor-/Narrator-Ausgaben brauchen Confidence-Metadaten.
- Low-confidence Progression wird nicht committed.
- Medium-confidence kann Review-/Flagged-State erzeugen.
- Tests muessen Fake Extractor/Narrator verwenden.
