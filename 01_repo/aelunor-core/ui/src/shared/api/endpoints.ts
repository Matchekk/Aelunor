function encodePath(value: string): string {
  return encodeURIComponent(String(value).trim());
}

export const endpoints = {
  campaigns: {
    by_id: (campaign_id: string) => `/api/campaigns/${encodePath(campaign_id)}`,
    create: () => "/api/campaigns",
    join: () => "/api/campaigns/join",
    create_turn: (campaign_id: string) => `/api/campaigns/${encodePath(campaign_id)}/turns`,
    context_query: (campaign_id: string) => `/api/campaigns/${encodePath(campaign_id)}/context/query`,
    character_sheet: (campaign_id: string, slot_id: string) =>
      `/api/campaigns/${encodePath(campaign_id)}/characters/${encodePath(slot_id)}`,
    npc_sheet: (campaign_id: string, npc_id: string) =>
      `/api/campaigns/${encodePath(campaign_id)}/npcs/${encodePath(npc_id)}`,
    patch_meta: (campaign_id: string) => `/api/campaigns/${encodePath(campaign_id)}/meta`,
    export: (campaign_id: string) => `/api/campaigns/${encodePath(campaign_id)}/export`,
    delete: (campaign_id: string) => `/api/campaigns/${encodePath(campaign_id)}`,
    patch_plot_essentials: (campaign_id: string) =>
      `/api/campaigns/${encodePath(campaign_id)}/boards/plot-essentials`,
    patch_authors_note: (campaign_id: string) =>
      `/api/campaigns/${encodePath(campaign_id)}/boards/authors-note`,
    create_story_card: (campaign_id: string) =>
      `/api/campaigns/${encodePath(campaign_id)}/boards/story-cards`,
    patch_story_card: (campaign_id: string, card_id: string) =>
      `/api/campaigns/${encodePath(campaign_id)}/boards/story-cards/${encodePath(card_id)}`,
    create_world_info: (campaign_id: string) =>
      `/api/campaigns/${encodePath(campaign_id)}/boards/world-info`,
    patch_world_info: (campaign_id: string, entry_id: string) =>
      `/api/campaigns/${encodePath(campaign_id)}/boards/world-info/${encodePath(entry_id)}`,
    setup_world_next: (campaign_id: string) => `/api/campaigns/${encodePath(campaign_id)}/setup/world/next`,
    setup_world_answer: (campaign_id: string) => `/api/campaigns/${encodePath(campaign_id)}/setup/world/answer`,
    setup_world_random: (campaign_id: string) => `/api/campaigns/${encodePath(campaign_id)}/setup/world/random`,
    setup_world_random_apply: (campaign_id: string) => `/api/campaigns/${encodePath(campaign_id)}/setup/world/random/apply`,
    setup_character_next: (campaign_id: string, slot_id: string) =>
      `/api/campaigns/${encodePath(campaign_id)}/slots/${encodePath(slot_id)}/setup/next`,
    setup_character_answer: (campaign_id: string, slot_id: string) =>
      `/api/campaigns/${encodePath(campaign_id)}/slots/${encodePath(slot_id)}/setup/answer`,
    setup_character_random: (campaign_id: string, slot_id: string) =>
      `/api/campaigns/${encodePath(campaign_id)}/slots/${encodePath(slot_id)}/setup/random`,
    setup_character_random_apply: (campaign_id: string, slot_id: string) =>
      `/api/campaigns/${encodePath(campaign_id)}/slots/${encodePath(slot_id)}/setup/random/apply`,
    claim_slot: (campaign_id: string, slot_id: string) =>
      `/api/campaigns/${encodePath(campaign_id)}/slots/${encodePath(slot_id)}/claim`,
    takeover_slot: (campaign_id: string, slot_id: string) =>
      `/api/campaigns/${encodePath(campaign_id)}/slots/${encodePath(slot_id)}/takeover`,
    unclaim_slot: (campaign_id: string, slot_id: string) =>
      `/api/campaigns/${encodePath(campaign_id)}/slots/${encodePath(slot_id)}/unclaim`,
    events: (campaign_id: string, player_id: string, player_token: string) => {
      const params = new URLSearchParams({
        player_id,
        player_token,
      });
      return `/api/campaigns/${encodePath(campaign_id)}/events?${params.toString()}`;
    },
  },
  system: {
    llm_status: () => "/api/llm/status",
  },
};
