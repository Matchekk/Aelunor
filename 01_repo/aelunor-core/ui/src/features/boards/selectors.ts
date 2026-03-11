import type { CampaignSnapshot, StoryCardEntry, WorldInfoEntry } from "../../shared/api/contracts";
import { formatDateTime as formatLocaleDateTime } from "../../shared/formatting/locale";
import { deriveBoardNoveltyCount, getNoveltyCount, noveltyLabel } from "../play/novelty";

export type BoardTabId = "plot" | "note" | "cards" | "world" | "memory" | "session";

export interface BoardTabConfig {
  id: BoardTabId;
  label: string;
}

export const BOARD_TABS: BoardTabConfig[] = [
  { id: "plot", label: "Plot Essentials" },
  { id: "note", label: "Author's Note" },
  { id: "cards", label: "Story Cards" },
  { id: "world", label: "World Info" },
  { id: "memory", label: "Memory Summary" },
  { id: "session", label: "Session" },
];

function formatBoardDateTime(value: string | null | undefined): string {
  if (!value) {
    return "Unknown";
  }
  const formatted = formatLocaleDateTime(value);
  if (!formatted) {
    return "Unknown";
  }
  return formatted;
}

export function deriveBoardTabs(campaign_id: string): Array<BoardTabConfig & { novelty_label: string | null }> {
  const keyByTab: Record<BoardTabId, string> = {
    plot: "board:plot",
    note: "board:note",
    cards: "board:cards",
    world: "board:world",
    memory: "board:memory",
    session: "board:session",
  };

  return BOARD_TABS.map((tab) => ({
    ...tab,
    novelty_label: noveltyLabel(getNoveltyCount(campaign_id, keyByTab[tab.id])),
  }));
}

export function deriveBoardsTriggerNovelty(campaign: CampaignSnapshot): string | null {
  return noveltyLabel(deriveBoardNoveltyCount(campaign.campaign_meta.campaign_id));
}

export function canEditBoards(campaign: CampaignSnapshot): boolean {
  return campaign.viewer_context.is_host;
}

export function formatBoardTimestamp(value: string | null | undefined): string {
  return formatBoardDateTime(value);
}

export function deriveStoryCardSubtitle(card: StoryCardEntry): string {
  const tags = card.tags.length > 0 ? ` • ${card.tags.join(", ")}` : "";
  return `${card.kind}${card.archived ? " • archived" : ""}${tags}`;
}

export function deriveWorldInfoSubtitle(entry: WorldInfoEntry): string {
  const tags = entry.tags.length > 0 ? ` • ${entry.tags.join(", ")}` : "";
  return `${entry.category}${tags}`;
}
