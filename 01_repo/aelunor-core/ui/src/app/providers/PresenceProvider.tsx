import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, type ReactNode } from "react";

import type { SessionBootstrap } from "../bootstrap/sessionStorage";
import { campaignQueryKeys } from "../../entities/campaign/queries";
import { usePresenceStore } from "../../entities/presence/store";
import { createCampaignSseClient } from "../../shared/sse/sseClient";

interface PresenceProviderProps {
  children: ReactNode;
  session: SessionBootstrap;
}

function debugSse(message: string, meta: Record<string, unknown>): void {
  if (!import.meta.env.DEV) {
    return;
  }
  console.debug(`[v1-sse] ${message}`, meta);
}

export function PresenceProvider({ children, session }: PresenceProviderProps) {
  const queryClient = useQueryClient();
  const clientRef = useRef<Awaited<ReturnType<typeof createCampaignSseClient>> | null>(null);
  const setSseConnected = usePresenceStore((state) => state.setSseConnected);
  const applyPresenceSync = usePresenceStore((state) => state.applyPresenceSync);
  const resetPresence = usePresenceStore((state) => state.resetPresence);

  useEffect(() => {
    const campaign_id = session.campaign_id;
    const player_id = session.player_id;
    const player_token = session.player_token;

    if (!campaign_id || !player_id || !player_token) {
      clientRef.current?.close();
      clientRef.current = null;
      resetPresence();
      return undefined;
    }

    clientRef.current?.close();
    debugSse("connect", { campaign_id, player_id });

    let cancelled = false;

    void createCampaignSseClient({
      campaign_id,
      player_id,
      player_token,
      onOpen: () => {
        debugSse("open", { campaign_id });
        setSseConnected(true);
      },
      onError: (event) => {
        debugSse("error", {
          campaign_id,
          ready_state: clientRef.current?.ready_state() ?? null,
          event_type: event.type,
        });
        setSseConnected(false);
      },
      onCampaignSync: (payload) => {
        debugSse("campaign_sync", { campaign_id, reason: payload.reason, version: payload.version });
        queryClient.invalidateQueries({
          queryKey: campaignQueryKeys.by_id(campaign_id),
        });
      },
      onPresenceSync: (snapshot) => {
        applyPresenceSync(snapshot);
      },
    }).then((client) => {
      if (cancelled) {
        client.close();
        return;
      }
      clientRef.current = client;
    }).catch((error) => {
      debugSse("ticket_failed", {
        campaign_id,
        error: error instanceof Error ? error.message : "unknown",
      });
      setSseConnected(false);
    });

    return () => {
      cancelled = true;
      debugSse("close", { campaign_id });
      clientRef.current?.close();
      clientRef.current = null;
      resetPresence();
    };
  }, [
    applyPresenceSync,
    queryClient,
    resetPresence,
    session.campaign_id,
    session.player_id,
    session.player_token,
    setSseConnected,
  ]);

  return <>{children}</>;
}
