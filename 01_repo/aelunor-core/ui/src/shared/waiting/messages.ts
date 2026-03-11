import type { WaitingContextId } from "./model";

interface WaitingCopy {
  heading: string;
  detail_by_stage: [string, string, string, string];
}

const WAITING_COPY_MAP: Record<WaitingContextId, WaitingCopy> = {
  story_turn: {
    heading: "Die Welt reagiert auf euren Zug",
    detail_by_stage: [
      "Du kannst währenddessen weiter in der Timeline lesen.",
      "Antwort formt sich und wird gleich eingebunden.",
      "Die Reaktion dauert etwas länger als üblich.",
      "Immer noch in Arbeit. Der Verlauf bleibt weiter lesbar.",
    ],
  },
  context_query: {
    heading: "Kontextabfrage läuft",
    detail_by_stage: [
      "Die Antwort wird vorbereitet.",
      "Kontext wird verdichtet.",
      "Die Abfrage braucht noch etwas Zeit.",
      "Weiterhin aktiv. Du kannst später erneut versuchen.",
    ],
  },
  campaign_open: {
    heading: "Kampagne wird geöffnet",
    detail_by_stage: [
      "Der aktuelle Snapshot wird geladen.",
      "Zustände und Einstieg werden vorbereitet.",
      "Der Einstieg dauert etwas länger.",
      "Noch in Arbeit. Der Übergang bleibt aktiv.",
    ],
  },
  campaign_create: {
    heading: "Neue Kampagne wird erstellt",
    detail_by_stage: [
      "Grundstruktur wird angelegt.",
      "Session und Einstieg werden vorbereitet.",
      "Die Erstellung dauert etwas länger.",
      "Weiterhin aktiv. Bitte kurz warten.",
    ],
  },
  campaign_join: {
    heading: "Raum wird verbunden",
    detail_by_stage: [
      "Join-Code wird geprüft.",
      "Session wird mit Kampagne verknüpft.",
      "Die Verbindung braucht noch einen Moment.",
      "Immer noch aktiv. Bitte kurz warten.",
    ],
  },
  session_resume: {
    heading: "Session wird geprüft",
    detail_by_stage: [
      "Lokale Daten werden gegen den Snapshot validiert.",
      "Einstiegspfad wird vorbereitet.",
      "Die Validierung dauert etwas länger.",
      "Weiterhin aktiv. Fallback bleibt verfügbar.",
    ],
  },
  setup_step: {
    heading: "Nächster Setup-Schritt wird vorbereitet",
    detail_by_stage: [
      "Antwort wird verarbeitet.",
      "Die nächsten Optionen werden berechnet.",
      "Setup benötigt etwas mehr Zeit.",
      "Weiterhin aktiv. Du bleibst im Setup-Kontext.",
    ],
  },
  setup_random: {
    heading: "Vorschlag wird generiert",
    detail_by_stage: [
      "Zufallsvorschlag wird erstellt.",
      "Varianten werden verfeinert.",
      "Die Generierung dauert etwas länger.",
      "Weiterhin aktiv. Vorschlag folgt.",
    ],
  },
  setup_waiting_host: {
    heading: "Welt-Setup läuft beim Host",
    detail_by_stage: [
      "Sobald der Host fertig ist, geht es weiter.",
      "Fortschritt wird weiterhin synchronisiert.",
      "Das Setup dauert noch an.",
      "Weiterhin in Arbeit. Du kannst den Fortschritt beobachten.",
    ],
  },
  scene_switch: {
    heading: "Szenenansicht wird gewechselt",
    detail_by_stage: [
      "Ansicht wird angepasst.",
      "Szenenfokus wird neu aufgebaut.",
      "Der Wechsel dauert etwas länger.",
      "Weiterhin aktiv. Die Ansicht stabilisiert sich.",
    ],
  },
  panel_load: {
    heading: "Bereich wird geladen",
    detail_by_stage: [
      "Inhalt wird vorbereitet.",
      "Details werden aufgebaut.",
      "Der Bereich lädt noch.",
      "Weiterhin aktiv. Du kannst später erneut prüfen.",
    ],
  },
};

export function deriveWaitingCopy(
  context: WaitingContextId,
  stage: 0 | 1 | 2 | 3,
  message_override: string | null,
  detail_override: string | null,
): { heading: string; detail: string } {
  const base = WAITING_COPY_MAP[context];
  if (!base) {
    return {
      heading: message_override || "Bitte kurz warten",
      detail: detail_override || "Der angeforderte Bereich wird vorbereitet.",
    };
  }

  return {
    heading: message_override || base.heading,
    detail: detail_override || base.detail_by_stage[stage],
  };
}
