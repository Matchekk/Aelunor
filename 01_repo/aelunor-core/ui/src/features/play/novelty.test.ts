import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearBoardNovelty, clearCharacterNovelty, getNoveltyCount, trackCampaignNovelty } from "./novelty";
import { createCampaignFixture } from "../../test/campaignFixture";

function createLocalStorageMock() {
  const store = new Map<string, string>();
  return {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => {
      store.set(key, value);
    },
    removeItem: (key: string) => {
      store.delete(key);
    },
    clear: () => {
      store.clear();
    },
  };
}

describe("novelty helpers", () => {
  beforeEach(() => {
    vi.stubGlobal("window", { localStorage: createLocalStorageMock() });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("tracks and clears only the targeted board novelty key", () => {
    const previousCampaign = createCampaignFixture();
    const nextCampaign = createCampaignFixture({
      boards: {
        ...previousCampaign.boards,
        plot_essentials: {
          ...previousCampaign.boards.plot_essentials,
          updated_at: "2026-03-10T12:00:00.000Z",
        },
        authors_note: {
          ...previousCampaign.boards.authors_note,
          updated_at: "2026-03-10T12:00:00.000Z",
        },
      },
    });

    trackCampaignNovelty(previousCampaign, nextCampaign);
    expect(getNoveltyCount("cmp_fixture", "board:plot")).toBe(1);
    expect(getNoveltyCount("cmp_fixture", "board:note")).toBe(1);

    clearBoardNovelty("cmp_fixture", "plot");
    expect(getNoveltyCount("cmp_fixture", "board:plot")).toBe(0);
    expect(getNoveltyCount("cmp_fixture", "board:note")).toBe(1);
  });

  it("clears only the requested character novelty scope", () => {
    const previousCampaign = createCampaignFixture();
    const nextCampaign = createCampaignFixture({
      state: {
        ...previousCampaign.state,
        characters: {
          aria: {
            scene_id: "scene_square",
            class_current: { id: "class_guard", name: "Guard", rank: "C", level: 3, level_max: 10 },
            skills: {
              skill_guard: { name: "Guard Stance", rank: "D", level: 1 },
            },
            injuries: [],
          },
          brann: {
            scene_id: "scene_forest",
            class_current: {},
            skills: {},
            injuries: [],
          },
        },
      },
    });

    trackCampaignNovelty(previousCampaign, nextCampaign);
    expect(getNoveltyCount("cmp_fixture", "class:aria")).toBeGreaterThan(0);
    expect(getNoveltyCount("cmp_fixture", "skill:aria")).toBeGreaterThan(0);

    clearCharacterNovelty("cmp_fixture", "aria", "class");
    expect(getNoveltyCount("cmp_fixture", "class:aria")).toBe(0);
    expect(getNoveltyCount("cmp_fixture", "skill:aria")).toBeGreaterThan(0);
  });
});
