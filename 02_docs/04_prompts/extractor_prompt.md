# Extractor Prompt

Extractor-Logik extrahiert strukturierte State-/Progression-Hinweise aus Story-Kontext.

## Aktueller Architekturhinweis

Extractor-Ergebnisse laufen durch Confidence- und Canon-Gate-Regeln. Low-confidence Ergebnisse duerfen nicht still in den Campaign State gelangen.

## Testregel

Automatisierte Tests patchen/faken den Extractor und rufen kein echtes Ollama auf.
