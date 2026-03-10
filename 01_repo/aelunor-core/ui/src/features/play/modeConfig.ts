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
    placeholder: "Describe what your character does next.",
    hint: "Use this for concrete in-world actions.",
    is_contextual: false,
    is_patching: false,
  },
  {
    id: "say",
    label: "SAGEN",
    backend_mode: "SAGEN",
    placeholder: "Write what your character says.",
    hint: "Use this for direct speech or a spoken exchange.",
    is_contextual: false,
    is_patching: false,
  },
  {
    id: "story",
    label: "STORY",
    backend_mode: "STORY",
    placeholder: "Write a story-forward contribution for the current scene.",
    hint: "Use this to push the current fiction forward collaboratively.",
    is_contextual: false,
    is_patching: false,
  },
  {
    id: "canon",
    label: "CANON",
    backend_mode: "CANON",
    placeholder: "Write a canonical state change that should become true in the world.",
    hint: "Use this carefully for direct canon contributions.",
    is_contextual: false,
    is_patching: true,
  },
  {
    id: "context",
    label: "KONTEXT",
    backend_mode: null,
    placeholder: "Ask a context question about the current canon or story.",
    hint: "This does not submit a story turn; it queries context.",
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
