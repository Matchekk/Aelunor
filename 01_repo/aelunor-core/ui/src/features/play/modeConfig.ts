export type PlayModeId = "do" | "say" | "story" | "canon" | "context";

export interface PlayModeConfig {
  id: PlayModeId;
  label: string;
  backend_mode: string | null;
  placeholder: string;
  hint: string;
  is_contextual: boolean;
  is_patching: boolean;
}

export const PLAY_MODE_CONFIG: PlayModeConfig[] = [
  {
    id: "do",
    label: "TUN",
    backend_mode: "TUN",
    placeholder: "Beschreibe, was dein Charakter als Nächstes tut.",
    hint: "Für konkrete Handlungen in der Szene.",
    is_contextual: false,
    is_patching: false,
  },
  {
    id: "say",
    label: "SAGEN",
    backend_mode: "SAGEN",
    placeholder: "Schreibe, was dein Charakter sagt.",
    hint: "Für direkte Rede oder kurze Dialogbeiträge.",
    is_contextual: false,
    is_patching: false,
  },
  {
    id: "story",
    label: "STORY",
    backend_mode: "STORY",
    placeholder: "Formuliere einen erzählerischen Beitrag für die aktuelle Szene.",
    hint: "Für gemeinsames Vorantreiben der Geschichte.",
    is_contextual: false,
    is_patching: false,
  },
  {
    id: "canon",
    label: "CANON",
    backend_mode: "CANON",
    placeholder: "Formuliere eine kanonische Zustandsänderung für die Welt.",
    hint: "Werkzeugmodus für gezielte Kanon-Änderungen.",
    is_contextual: false,
    is_patching: true,
  },
  {
    id: "context",
    label: "KONTEXT",
    backend_mode: null,
    placeholder: "Stelle eine Kontextfrage zu Kanon oder laufender Szene.",
    hint: "Werkzeugmodus: erstellt keinen Story-Turn.",
    is_contextual: true,
    is_patching: false,
  },
];

const PLAY_MODE_INDEX = PLAY_MODE_CONFIG.reduce<Record<PlayModeId, PlayModeConfig>>((acc, entry) => {
  acc[entry.id] = entry;
  return acc;
}, {} as Record<PlayModeId, PlayModeConfig>);

export function getPlayModeConfig(mode: PlayModeId): PlayModeConfig {
  return PLAY_MODE_INDEX[mode];
}
