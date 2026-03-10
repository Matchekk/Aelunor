import type { CampaignSyncEvent, PresenceState } from "../api/contracts";
import { endpoints } from "../api/endpoints";

export interface CampaignSseClientOptions {
  campaign_id: string;
  player_id: string;
  player_token: string;
  onOpen?: () => void;
  onError?: (event: Event) => void;
  onCampaignSync?: (payload: CampaignSyncEvent) => void;
  onPresenceSync?: (payload: PresenceState) => void;
}

export interface CampaignSseClient {
  close: () => void;
  ready_state: () => number;
}

function parsePayload<T>(event: MessageEvent): T | null {
  if (!event.data || typeof event.data !== "string") {
    return null;
  }
  try {
    return JSON.parse(event.data) as T;
  } catch (_error) {
    return null;
  }
}

export function createCampaignSseClient(options: CampaignSseClientOptions): CampaignSseClient {
  const { campaign_id, player_id, player_token } = options;
  const eventSource = new EventSource(endpoints.campaigns.events(campaign_id, player_id, player_token));

  eventSource.onopen = () => {
    options.onOpen?.();
  };

  eventSource.onerror = (event) => {
    options.onError?.(event);
  };

  eventSource.addEventListener("campaign_sync", (rawEvent) => {
    const payload = parsePayload<CampaignSyncEvent>(rawEvent as MessageEvent);
    if (payload) {
      options.onCampaignSync?.(payload);
    }
  });

  eventSource.addEventListener("presence_sync", (rawEvent) => {
    const payload = parsePayload<PresenceState>(rawEvent as MessageEvent);
    if (payload) {
      options.onPresenceSync?.(payload);
    }
  });

  return {
    close: () => {
      eventSource.close();
    },
    ready_state: () => eventSource.readyState,
  };
}
