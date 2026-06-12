# Routers Context

Router in `app/routers/` sind HTTP-Adapter. Sie sollen Payloads lesen,
Dependencies abrufen, Service-Funktionen aufrufen und Responses zurueckgeben.
Fachlogik gehoert in `app/services/`.

## Router-Landkarte

| Datei | Bereich |
| --- | --- |
| `campaigns.py` | Create, Join, Get, Meta, Export, Delete, Intro/Time/Class-Aktionen |
| `setup.py` | World-/Character-Setup, Antworten, Random Preview, Finalisierung |
| `claim.py` | Claim, Takeover, Unclaim |
| `turns.py` | Turn erstellen, editieren, undo, retry |
| `boards.py` | Boards, Diary, Story Cards, Revisionen |
| `context.py` | Read-only Kontext-/Canon-Fragen |
| `sheets.py` | Party-, Character- und NPC-Sheets |
| `presence.py` | SSE-Tickets, Stream, Activity, Clear |
| `llm.py` | Lokale Ollama-Modellliste und kurzer GM-Test |

## Dependency-Regel

Router bekommen ihre Service-Dependencies ueber Factories aus
`app/dependencies/factories.py`, verdrahtet in `app/main.py`.

Nicht tun:

- neue `app.main.<state_helper>`-Patches nur fuer Tests einfuehren,
- Domain-Helfer ueber `main.py` re-exportieren,
- Router mit State-/Canon-/Narrator-Logik anreichern.

Wenn ein Test patchen muss, dann an der Stelle patchen, an der der Service oder
das Zielmodul die Funktion wirklich nutzt.
