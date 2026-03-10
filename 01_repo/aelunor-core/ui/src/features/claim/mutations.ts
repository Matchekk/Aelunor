import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { ClaimSlotResponse, TakeoverSlotResponse, UnclaimSlotResponse } from "../../shared/api/contracts";
import { invalidateCampaignQuery } from "../../entities/campaign/queries";
import { endpoints } from "../../shared/api/endpoints";
import { postJson } from "../../shared/api/httpClient";

export function useClaimSlotMutation(campaign_id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (slot_id: string) =>
      postJson<ClaimSlotResponse>(endpoints.campaigns.claim_slot(campaign_id, slot_id)),
    onSuccess: async () => {
      await invalidateCampaignQuery(queryClient, campaign_id);
    },
  });
}

export function useTakeoverSlotMutation(campaign_id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (slot_id: string) =>
      postJson<TakeoverSlotResponse>(endpoints.campaigns.takeover_slot(campaign_id, slot_id)),
    onSuccess: async () => {
      await invalidateCampaignQuery(queryClient, campaign_id);
    },
  });
}

export function useUnclaimSlotMutation(campaign_id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (slot_id: string) =>
      postJson<UnclaimSlotResponse>(endpoints.campaigns.unclaim_slot(campaign_id, slot_id)),
    onSuccess: async () => {
      await invalidateCampaignQuery(queryClient, campaign_id);
    },
  });
}
