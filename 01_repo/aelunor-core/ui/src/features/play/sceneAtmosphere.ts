import type { CampaignSnapshot } from "../../shared/api/contracts";
import { partyOverview, plotEssentials, worldTime } from "./partyHudModel";

export interface SceneAtmosphere {
  name: string;
  text: string;
}

const FALLBACK_TEXT = "Die genaue Lage ist noch nicht vollständig geklärt, aber die Szene wirkt dunkel, still und angespannt.";

const TIME_PHRASES: Record<string, string> = {
  dawn: "im ersten Morgengrauen",
  morning: "im Morgenlicht",
  midday: "unter hochstehender Sonne",
  noon: "unter hochstehender Sonne",
  afternoon: "im Nachmittagslicht",
  evening: "in der Abenddämmerung",
  dusk: "in der hereinbrechenden Dämmerung",
  night: "in tiefer Nacht",
};

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function readString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function shortenDescription(value: string, max_length = 180): string {
  if (value.length <= max_length) {
    return value;
  }
  const sentenceEnd = value.slice(0, max_length).lastIndexOf(". ");
  if (sentenceEnd > 40) {
    return value.slice(0, sentenceEnd + 1);
  }
  return `${value.slice(0, max_length).trimEnd()} …`;
}

export function deriveSceneAtmosphere(campaign: CampaignSnapshot, active_scene_label: string): SceneAtmosphere {
  const state = readRecord(campaign.state);
  const activeScene = readString(plotEssentials(campaign).active_scene);
  const name = active_scene_label && active_scene_label !== "Alle Szenen" ? active_scene_label : activeScene;
  const sceneId = partyOverview(campaign).find((entry) => entry.scene_name === name)?.scene_id ?? "";
  const scene = readRecord(readRecord(state.scenes)[sceneId]);

  const location = readString(scene.location) || readString(scene.region);
  const mood = readString(scene.mood);
  const description = readString(scene.description);
  const timePhrase = TIME_PHRASES[readString(worldTime(campaign).time_of_day).toLowerCase()] ?? "";
  const weather = readString(worldTime(campaign).weather);

  const sentences: string[] = [];
  if (description) {
    sentences.push(shortenDescription(description));
  } else if (location) {
    sentences.push(`Der Schauplatz liegt in ${location}.`);
  }
  if (weather && timePhrase) {
    sentences.push(`${capitalize(weather)} hängt ${timePhrase} über der Szene.`);
  } else if (weather) {
    sentences.push(`${capitalize(weather)} liegt über der Szene.`);
  } else if (timePhrase) {
    sentences.push(`Die Szene liegt ${timePhrase}.`);
  }
  if (mood) {
    sentences.push(`Die Stimmung wirkt ${mood}.`);
  }

  return {
    name: name || "Unbekannter Schauplatz",
    text: sentences.length > 0 ? sentences.join(" ") : FALLBACK_TEXT,
  };
}
