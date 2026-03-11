import type { PlayModeId } from "../../features/play/modeConfig";
import type { ComposerModePreference, TimelineDetailDefault } from "./types";

export function resolveInitialComposerMode(preference: ComposerModePreference): PlayModeId {
  if (preference === "say" || preference === "story") {
    return preference;
  }
  return "do";
}

export function shouldOpenTimelineDetails(value: TimelineDetailDefault): boolean {
  return value === "expanded";
}
