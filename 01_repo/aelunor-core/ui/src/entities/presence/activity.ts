import { useCallback, useEffect, useMemo } from "react";

import type {
  PresenceActivityClearResponse,
  PresenceActivitySetRequest,
  PresenceActivitySetResponse,
} from "../../shared/api/contracts";
import { endpoints } from "../../shared/api/endpoints";
import { postJson } from "../../shared/api/httpClient";
import { usePresenceStore } from "./store";

export type PresenceActivityKind =
  | "typing_turn"
  | "building_world"
  | "building_character"
  | "editing_turn"
  | "claiming_slot";

export type PresenceActivityContext =
  | "typing"
  | "world_setup"
  | "character_setup"
  | "turn_edit"
  | "slot_claim";

export function derivePresenceKindForContext(context: PresenceActivityContext): PresenceActivityKind {
  if (context === "typing") {
    return "typing_turn";
  }
  if (context === "world_setup") {
    return "building_world";
  }
  if (context === "character_setup") {
    return "building_character";
  }
  if (context === "turn_edit") {
    return "editing_turn";
  }
  return "claiming_slot";
}

export function deriveSetupPresenceKind(mode: "world" | "character"): PresenceActivityKind {
  return mode === "world" ? derivePresenceKindForContext("world_setup") : derivePresenceKindForContext("character_setup");
}

interface UsePresenceActivityClientResult {
  set_activity: (payload: PresenceActivitySetRequest) => Promise<void>;
  clear_activity: () => Promise<void>;
}

function debugPresence(message: string, meta: Record<string, unknown>): void {
  if (!import.meta.env.DEV) {
    return;
  }
  console.debug(`[v1-presence] ${message}`, meta);
}

export function usePresenceActivityClient(campaign_id: string | null | undefined): UsePresenceActivityClientResult {
  const applyPresenceSync = usePresenceStore((state) => state.applyPresenceSync);

  const set_activity = useCallback(
    async (payload: PresenceActivitySetRequest) => {
      if (!campaign_id) {
        return;
      }
      try {
        const response = await postJson<PresenceActivitySetResponse>(endpoints.campaigns.presence_activity(campaign_id), payload);
        applyPresenceSync(response.live);
      } catch (error) {
        debugPresence("set_activity_failed", {
          campaign_id,
          kind: payload.kind,
          error: error instanceof Error ? error.message : "unknown",
        });
      }
    },
    [applyPresenceSync, campaign_id],
  );

  const clear_activity = useCallback(async () => {
    if (!campaign_id) {
      return;
    }
    try {
      const response = await postJson<PresenceActivityClearResponse>(endpoints.campaigns.presence_clear(campaign_id));
      applyPresenceSync(response.live);
    } catch (error) {
      debugPresence("clear_activity_failed", {
        campaign_id,
        error: error instanceof Error ? error.message : "unknown",
      });
    }
  }, [applyPresenceSync, campaign_id]);

  return useMemo(
    () => ({
      set_activity,
      clear_activity,
    }),
    [clear_activity, set_activity],
  );
}

interface PresenceActivityHeartbeatOptions {
  active: boolean;
  campaign_id: string | null | undefined;
  kind: PresenceActivityKind;
  slot_id?: string | null;
  target_turn_id?: string | null;
  interval_ms?: number;
}

export function usePresenceActivityHeartbeat(options: PresenceActivityHeartbeatOptions): void {
  const { active, campaign_id, kind, slot_id = null, target_turn_id = null, interval_ms = 8000 } = options;
  const { set_activity, clear_activity } = usePresenceActivityClient(campaign_id);

  useEffect(() => {
    if (!active || !campaign_id) {
      return undefined;
    }

    const payload: PresenceActivitySetRequest = {
      kind,
      slot_id,
      target_turn_id,
    };
    void set_activity(payload);

    const timer = window.setInterval(() => {
      void set_activity(payload);
    }, interval_ms);

    return () => {
      window.clearInterval(timer);
      void clear_activity();
    };
  }, [active, campaign_id, clear_activity, interval_ms, kind, set_activity, slot_id, target_turn_id]);
}
