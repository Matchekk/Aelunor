export type ScopeLabelKind = "self" | "party" | "host" | "scene";

export interface ScopeLabelDescriptor {
  key: string;
  kind: ScopeLabelKind;
  label: string;
}

export function selfScopeLabel(): ScopeLabelDescriptor {
  return { key: "self", kind: "self", label: "self" };
}

export function partyScopeLabel(): ScopeLabelDescriptor {
  return { key: "party", kind: "party", label: "party" };
}

export function hostScopeLabel(): ScopeLabelDescriptor {
  return { key: "host", kind: "host", label: "host/gm" };
}

export function sceneScopeLabel(scene_name: string, scene_id?: string | null): ScopeLabelDescriptor {
  const normalizedName = scene_name.trim();
  const normalizedId = (scene_id ?? "").trim();
  return {
    key: `scene:${normalizedId || normalizedName}`,
    kind: "scene",
    label: normalizedName ? `scene:${normalizedName}` : `scene:${normalizedId || "unknown"}`,
  };
}
