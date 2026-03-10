import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { normalizeSessionLibraryEntries } from "./sessionLibrary";

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

describe("normalizeSessionLibraryEntries", () => {
  beforeEach(() => {
    vi.stubGlobal("window", { localStorage: createLocalStorageMock() });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("normalizes legacy keys and keeps the newest duplicate entry", () => {
    const entries = normalizeSessionLibraryEntries([
      {
        campaignId: "cmp-1",
        playerId: "p-1",
        playerToken: "token-a",
        joinCode: "join-a",
        title: "Old",
        lastUsedAt: "2026-03-10T09:00:00.000Z",
      },
      {
        campaign_id: "cmp-1",
        player_id: "p-1",
        player_token: "token-b",
        join_code: "join-b",
        label: "New",
        updated_at: "2026-03-10T11:00:00.000Z",
      },
      {
        campaign_id: "",
      },
    ]);

    expect(entries).toHaveLength(1);
    expect(entries[0]).toMatchObject({
      campaign_id: "cmp-1",
      player_token: "token-b",
      label: "New",
      join_code: "join-b",
    });
  });
});
