import type { CampaignSnapshot } from "../shared/api/contracts";

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function deepMerge<T>(base: T, override: Partial<T>): T {
  if (!isRecord(base) || !isRecord(override)) {
    return override as T;
  }

  const next: Record<string, unknown> = { ...base };
  for (const [key, value] of Object.entries(override)) {
    if (value === undefined) {
      continue;
    }
    const current = next[key];
    next[key] = isRecord(current) && isRecord(value) ? deepMerge(current, value) : value;
  }
  return next as T;
}

export function createCampaignFixture(override: Partial<CampaignSnapshot> = {}): CampaignSnapshot {
  const base: CampaignSnapshot = {
    campaign_meta: {
      campaign_id: "cmp_fixture",
      title: "Fixture Campaign",
      created_at: "2026-03-10T10:00:00.000Z",
      updated_at: "2026-03-10T10:00:00.000Z",
      status: "active",
      host_player_id: "player-host",
    },
    state: {
      meta: {
        phase: "active",
      },
      scenes: {
        scene_square: { name: "Market Square" },
        scene_forest: { name: "Forest Edge" },
      },
      map: {
        nodes: {},
      },
      characters: {
        aria: {
          scene_id: "scene_square",
          class_current: { id: "class_guard", name: "Guard", rank: "D", level: 2, level_max: 10 },
          skills: {},
          injuries: [],
        },
        brann: {
          scene_id: "scene_forest",
          class_current: {},
          skills: {},
          injuries: [],
        },
      },
      codex: {
        races: {},
        beasts: {},
      },
      world: {
        races: {},
        beast_types: {},
      },
    },
    setup: {},
    setup_runtime: {
      phase: "active",
      phase_display: "Active",
      world: {
        completed: true,
      },
      claimed_slot_id: "aria",
      character: null,
      slot_statuses: [
        {
          slot_id: "aria",
          display_name: "Aria",
          status: "ready",
          completed: true,
        },
      ],
      ready_counter: {
        ready: 1,
        total: 1,
      },
      is_ready_to_start: true,
    },
    available_slots: [
      {
        slot_id: "aria",
        display_name: "Aria",
        claimed_by: "player-host",
        claimed_by_name: "Host",
        completed: true,
      },
    ],
    claims: {},
    active_party: ["aria"],
    display_party: [{ slot_id: "aria", display_name: "Aria" }],
    world_time: {
      day: 1,
      time_of_day: "dawn",
    },
    boards: {
      plot_essentials: {
        premise: "",
        current_goal: "",
        current_threat: "",
        active_scene: "",
        open_loops: [],
        tone: "",
        updated_at: "2026-03-10T10:00:00.000Z",
      },
      authors_note: {
        content: "",
        updated_at: "2026-03-10T10:00:00.000Z",
      },
      story_cards: [],
      world_info: [],
      memory_summary: {
        content: "",
        updated_through_turn: 0,
        updated_at: "2026-03-10T10:00:00.000Z",
      },
    },
    active_turns: [
      {
        turn_id: "turn-1",
        turn_number: 1,
        status: "active",
        actor: "aria",
        actor_display: "Aria",
        action_type: "do",
        mode: "TUN",
        input_text_display: "Aria watches the square.",
        gm_text_display: "The market wakes slowly.",
        requests: [],
        created_at: "2026-03-10T10:01:00.000Z",
        updated_at: "2026-03-10T10:01:00.000Z",
        edit_count: 0,
        patch_summary: {},
        narrator_patch: {
          characters: {
            aria: {
              scene_id: "scene_square",
            },
          },
        },
        extractor_patch: {},
        can_edit: true,
        can_undo: true,
        can_retry: true,
      },
    ],
    party_overview: [
      {
        slot_id: "aria",
        display_name: "Aria",
        claimed_by: "player-host",
        claimed_by_name: "Host",
        scene_id: "scene_square",
        scene_name: "Market Square",
        class_name: "Guard",
      },
      {
        slot_id: "brann",
        display_name: "Brann",
        scene_id: "scene_forest",
        scene_name: "Forest Edge",
        class_name: "Scout",
      },
    ],
    character_sheet_slots: ["aria", "brann"],
    ui_panels: {},
    players: [
      {
        player_id: "player-host",
        display_name: "Host",
      },
    ],
    viewer_context: {
      player_id: "player-host",
      display_name: "Host",
      is_host: true,
      claimed_slot_id: "aria",
      claimed_character: "Aria",
      phase: "active",
      needs_world_setup: false,
      needs_character_setup: false,
      pending_setup_question: null,
    },
    live: {
      version: 1,
      activities: {},
      blocking_action: null,
    },
  };

  return deepMerge(base, override);
}
