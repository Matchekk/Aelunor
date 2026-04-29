import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createCampaignSseClient } from "./sseClient";

const CAMPAIGN_ID = "campaign_test_1";
const PLAYER_ID = "player_test_1";
const PLAYER_TOKEN = "REAL_PLAYER_TOKEN_SHOULD_NOT_LEAK";
const STREAM_TOKEN = "stream_test_123";

type ListenerMap = Record<string, Array<(event: MessageEvent) => void>>;

class MemoryStorage implements Storage {
  private map = new Map<string, string>();

  get length(): number {
    return this.map.size;
  }

  clear(): void {
    this.map.clear();
  }

  getItem(key: string): string | null {
    return this.map.get(key) ?? null;
  }

  key(index: number): string | null {
    return Array.from(this.map.keys())[index] ?? null;
  }

  removeItem(key: string): void {
    this.map.delete(key);
  }

  setItem(key: string, value: string): void {
    this.map.set(key, value);
  }
}

class FakeEventSource {
  static instances: FakeEventSource[] = [];

  public onopen: ((event: Event) => void) | null = null;
  public onerror: ((event: Event) => void) | null = null;
  public readonly listeners: ListenerMap = {};
  public readonly close = vi.fn();
  public readyState = 1;

  public constructor(public readonly url: string) {
    FakeEventSource.instances.push(this);
  }

  public addEventListener(type: string, listener: (event: MessageEvent) => void): void {
    this.listeners[type] = [...(this.listeners[type] ?? []), listener];
  }

  public emit(type: string, data: unknown): void {
    const event = { data: typeof data === "string" ? data : JSON.stringify(data) } as MessageEvent;
    for (const listener of this.listeners[type] ?? []) {
      listener(event);
    }
  }

  public emitInvalidJson(type: string): void {
    const event = { data: "not-json" } as MessageEvent;
    for (const listener of this.listeners[type] ?? []) {
      listener(event);
    }
  }
}

function ticketResponse(payload: unknown, ok = true): Response {
  return {
    ok,
    status: ok ? 200 : 500,
    headers: new Headers({ "content-type": "application/json" }),
    json: () => Promise.resolve(payload),
    text: () => Promise.resolve(JSON.stringify(payload)),
  } as Response;
}

function installSessionStorage(): MemoryStorage {
  const localStorage = new MemoryStorage();
  localStorage.setItem("isekaiCampaignId", CAMPAIGN_ID);
  localStorage.setItem("isekaiPlayerId", PLAYER_ID);
  localStorage.setItem("isekaiPlayerToken", PLAYER_TOKEN);
  vi.stubGlobal("window", { localStorage });
  return localStorage;
}

describe("createCampaignSseClient", () => {
  beforeEach(() => {
    FakeEventSource.instances = [];
    installSessionStorage();
    vi.stubGlobal("EventSource", FakeEventSource);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("requests a stream ticket before opening EventSource and never leaks the player token in the URL", async () => {
    const fetchMock = vi.fn().mockResolvedValue(ticketResponse({ stream_token: STREAM_TOKEN, expires_in_sec: 120 }));
    vi.stubGlobal("fetch", fetchMock);

    const onCampaignSync = vi.fn();
    const onPresenceSync = vi.fn();
    const onOpen = vi.fn();
    const onError = vi.fn();

    const client = await createCampaignSseClient({
      campaign_id: CAMPAIGN_ID,
      player_id: PLAYER_ID,
      player_token: PLAYER_TOKEN,
      onCampaignSync,
      onPresenceSync,
      onOpen,
      onError,
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [ticketUrl, ticketInit] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(ticketUrl).toBe(`/api/campaigns/${CAMPAIGN_ID}/events/ticket`);
    expect(ticketInit.method).toBe("POST");
    const headers = ticketInit.headers as Headers;
    expect(headers.get("X-Player-Id")).toBe(PLAYER_ID);
    expect(headers.get("X-Player-Token")).toBe(PLAYER_TOKEN);

    expect(FakeEventSource.instances).toHaveLength(1);
    const eventSource = FakeEventSource.instances[0];
    if (!eventSource) {
      throw new Error("Expected EventSource to be created.");
    }
    expect(eventSource.url).toContain("stream_token=stream_test_123");
    expect(eventSource.url).not.toContain("player_token");
    expect(eventSource.url).not.toContain(PLAYER_TOKEN);
    expect(eventSource.url).not.toContain("X-Player-Token");
    expect(eventSource.url).not.toContain("player_id");

    eventSource.onopen?.(new Event("open"));
    expect(onOpen).toHaveBeenCalledTimes(1);

    eventSource.emit("campaign_sync", { version: 7, reason: "campaign_updated" });
    expect(onCampaignSync).toHaveBeenCalledWith({ version: 7, reason: "campaign_updated" });

    eventSource.emit("presence_sync", {
      version: 3,
      activities: { [PLAYER_ID]: { kind: "typing_turn", label: "typing", blocking: false, updated_at: "now", expires_at: "soon" } },
      blocking_action: null,
    });
    expect(onPresenceSync).toHaveBeenCalledWith({
      version: 3,
      activities: { [PLAYER_ID]: { kind: "typing_turn", label: "typing", blocking: false, updated_at: "now", expires_at: "soon" } },
      blocking_action: null,
    });

    eventSource.emitInvalidJson("campaign_sync");
    expect(onCampaignSync).toHaveBeenCalledTimes(1);

    eventSource.onerror?.(new Event("error"));
    expect(onError).toHaveBeenCalledTimes(1);

    expect(client.ready_state()).toBe(1);
    client.close();
    expect(eventSource.close).toHaveBeenCalledTimes(1);
  });

  it("does not open EventSource when the ticket request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(ticketResponse({ detail: "bad auth" }, false)));

    await expect(
      createCampaignSseClient({
        campaign_id: CAMPAIGN_ID,
        player_id: PLAYER_ID,
        player_token: PLAYER_TOKEN,
      }),
    ).rejects.toThrow("bad auth");

    expect(FakeEventSource.instances).toHaveLength(0);
  });

  it("does not open EventSource when the ticket response lacks a stream token", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(ticketResponse({ expires_in_sec: 120 })));

    await expect(
      createCampaignSseClient({
        campaign_id: CAMPAIGN_ID,
        player_id: PLAYER_ID,
        player_token: PLAYER_TOKEN,
      }),
    ).rejects.toThrow("stream token");

    expect(FakeEventSource.instances).toHaveLength(0);
  });
});
