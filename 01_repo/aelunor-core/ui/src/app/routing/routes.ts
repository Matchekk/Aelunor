import type { CampaignSnapshot } from "../../shared/api/contracts";
import type { BoardTabId } from "../../features/boards/selectors";
import { BOARD_TABS } from "../../features/boards/selectors";
import type { CodexKind, DrawerType } from "../../features/drawers/drawerStore";
import { deriveSceneOptions, type SceneFilterId } from "../../features/scenes/selectors";

export type CampaignRouteWorkspace = "claim" | "setup" | "play";
export type V1RouteKind = "root" | "hub" | "campaign" | "unknown";
export type SurfaceHistoryKind = "boards" | "drawer" | "context" | "scene";

export interface ParsedV1RouteIntent {
  kind: V1RouteKind;
  campaign_id: string | null;
  workspace: CampaignRouteWorkspace | null;
}

export interface DrawerRouteIntent {
  drawer_type: DrawerType;
  entity_id: string;
  codex_kind: CodexKind | null;
}

export interface PlayRouteState {
  scene_id: SceneFilterId;
  boards_tab: BoardTabId | null;
  drawer: DrawerRouteIntent | null;
  context_open: boolean;
}

const BOARD_QUERY_TO_TAB: Record<string, BoardTabId> = {
  plot_essentials: "plot",
  authors_note: "note",
  story_cards: "cards",
  world_info: "world",
  memory_summary: "memory",
  session: "session",
};

const BOARD_TAB_TO_QUERY: Record<BoardTabId, string> = Object.entries(BOARD_QUERY_TO_TAB).reduce<Record<BoardTabId, string>>(
  (acc, [query, tab_id]) => {
    acc[tab_id] = query;
    return acc;
  },
  {
    plot: "plot_essentials",
    note: "authors_note",
    cards: "story_cards",
    world: "world_info",
    memory: "memory_summary",
    session: "session",
  },
);

const KNOWN_BOARD_TABS = new Set<BoardTabId>(BOARD_TABS.map((entry) => entry.id));

function normalizePathSegment(value: string | null | undefined): string | null {
  const normalized = String(value ?? "").trim();
  return normalized.length > 0 ? normalized : null;
}

function parseTruthLikeBoolean(value: string | null): boolean {
  return value === "1" || value === "true";
}

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

export function buildV1RootPath(): string {
  return "/v1";
}

export function buildV1HubPath(): string {
  return "/v1/hub";
}

export function buildCampaignPath(campaign_id: string, workspace: CampaignRouteWorkspace): string {
  return `/v1/campaign/${campaign_id}/${workspace}`;
}

export function parseV1RouteIntent(pathname: string): ParsedV1RouteIntent {
  const normalized = pathname.replace(/\/+$/, "") || "/";

  if (normalized === "/v1") {
    return {
      kind: "root",
      campaign_id: null,
      workspace: null,
    };
  }

  if (normalized === "/v1/hub") {
    return {
      kind: "hub",
      campaign_id: null,
      workspace: null,
    };
  }

  const campaignMatch = normalized.match(/^\/v1\/campaign\/([^/]+)\/([^/]+)$/);
  if (!campaignMatch) {
    return {
      kind: "unknown",
      campaign_id: null,
      workspace: null,
    };
  }

  const campaign_id = normalizePathSegment(decodeURIComponent(campaignMatch[1] ?? ""));
  const workspace = normalizePathSegment(decodeURIComponent(campaignMatch[2] ?? ""));
  if (!campaign_id || !workspace || !["claim", "setup", "play"].includes(workspace)) {
    return {
      kind: "unknown",
      campaign_id: null,
      workspace: null,
    };
  }

  return {
    kind: "campaign",
    campaign_id,
    workspace: workspace as CampaignRouteWorkspace,
  };
}

export function normalizeBoardTabQuery(value: string | null): BoardTabId | null {
  if (!value) {
    return null;
  }

  const normalized = value.trim();
  if (!normalized) {
    return null;
  }

  if (KNOWN_BOARD_TABS.has(normalized as BoardTabId)) {
    return normalized as BoardTabId;
  }

  return BOARD_QUERY_TO_TAB[normalized] ?? null;
}

export function serializeBoardTabQuery(tab_id: BoardTabId | null): string | null {
  if (!tab_id) {
    return null;
  }
  return BOARD_TAB_TO_QUERY[tab_id] ?? null;
}

function deriveCodexKindForEntity(campaign: CampaignSnapshot, entity_id: string): CodexKind | null {
  const world = readRecord(readRecord(campaign.state).world);
  const races = readRecord(world.races);
  if (entity_id in races) {
    return "race";
  }
  const beast_types = readRecord(world.beast_types);
  if (entity_id in beast_types) {
    return "beast";
  }
  return null;
}

export function normalizePlayRouteState(campaign: CampaignSnapshot, search: string): PlayRouteState {
  const searchParams = new URLSearchParams(search);
  const scene = normalizePathSegment(searchParams.get("scene"));
  const scene_id =
    scene && deriveSceneOptions(campaign).some((entry) => entry.scene_id === scene)
      ? scene
      : ("all" as SceneFilterId);

  const boards_tab = normalizeBoardTabQuery(searchParams.get("boards"));
  const drawer_param = normalizePathSegment(searchParams.get("drawer"));
  const context_open = parseTruthLikeBoolean(searchParams.get("context"));

  let drawer: DrawerRouteIntent | null = null;
  if (drawer_param === "character") {
    const slot_id = normalizePathSegment(searchParams.get("slot"));
    if (slot_id) {
      drawer = {
        drawer_type: "character",
        entity_id: slot_id,
        codex_kind: null,
      };
    }
  } else if (drawer_param === "npc") {
    const npc_id = normalizePathSegment(searchParams.get("npc"));
    if (npc_id) {
      drawer = {
        drawer_type: "npc",
        entity_id: npc_id,
        codex_kind: null,
      };
    }
  } else if (drawer_param === "codex") {
    const codex_id = normalizePathSegment(searchParams.get("codex"));
    if (codex_id) {
      const codex_kind = deriveCodexKindForEntity(campaign, codex_id);
      if (codex_kind) {
        drawer = {
          drawer_type: "codex",
          entity_id: codex_id,
          codex_kind,
        };
      }
    }
  }

  if (boards_tab) {
    return {
      scene_id,
      boards_tab,
      drawer: null,
      context_open: false,
    };
  }

  if (context_open) {
    return {
      scene_id,
      boards_tab: null,
      drawer: null,
      context_open: true,
    };
  }

  return {
    scene_id,
    boards_tab: null,
    drawer,
    context_open: false,
  };
}

export function serializePlayRouteState(state: PlayRouteState): string {
  const searchParams = new URLSearchParams();

  if (state.scene_id !== "all") {
    searchParams.set("scene", state.scene_id);
  }

  if (state.boards_tab) {
    const boards = serializeBoardTabQuery(state.boards_tab);
    if (boards) {
      searchParams.set("boards", boards);
    }
  } else if (state.context_open) {
    searchParams.set("context", "1");
  } else if (state.drawer) {
    searchParams.set("drawer", state.drawer.drawer_type);
    if (state.drawer.drawer_type === "character") {
      searchParams.set("slot", state.drawer.entity_id);
    } else if (state.drawer.drawer_type === "npc") {
      searchParams.set("npc", state.drawer.entity_id);
    } else {
      searchParams.set("codex", state.drawer.entity_id);
    }
  }

  const rendered = searchParams.toString();
  return rendered ? `?${rendered}` : "";
}

export function withSceneRouteState(current: PlayRouteState, scene_id: SceneFilterId): PlayRouteState {
  return {
    ...current,
    scene_id,
  };
}

export function withBoardsRouteState(current: PlayRouteState, boards_tab: BoardTabId): PlayRouteState {
  return {
    scene_id: current.scene_id,
    boards_tab,
    drawer: null,
    context_open: false,
  };
}

export function withoutBoardsRouteState(current: PlayRouteState): PlayRouteState {
  return {
    scene_id: current.scene_id,
    boards_tab: null,
    drawer: current.drawer,
    context_open: current.context_open,
  };
}

export function withDrawerRouteState(current: PlayRouteState, drawer: DrawerRouteIntent): PlayRouteState {
  return {
    scene_id: current.scene_id,
    boards_tab: null,
    drawer,
    context_open: false,
  };
}

export function withoutDrawerRouteState(current: PlayRouteState): PlayRouteState {
  return {
    scene_id: current.scene_id,
    boards_tab: current.boards_tab,
    drawer: null,
    context_open: current.context_open,
  };
}

export function withContextRouteState(current: PlayRouteState): PlayRouteState {
  return {
    scene_id: current.scene_id,
    boards_tab: null,
    drawer: null,
    context_open: true,
  };
}

export function withoutContextRouteState(current: PlayRouteState): PlayRouteState {
  return {
    scene_id: current.scene_id,
    boards_tab: current.boards_tab,
    drawer: current.drawer,
    context_open: false,
  };
}

export function buildSurfaceHistoryState(surface: SurfaceHistoryKind, path: string, search: string): Record<string, string> {
  return {
    aelunor_surface: surface,
    aelunor_return_to: `${path}${search}`,
  };
}
