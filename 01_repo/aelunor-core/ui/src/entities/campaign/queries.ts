import { useQuery, type QueryClient } from "@tanstack/react-query";

import type { CampaignSnapshot } from "../../shared/api/contracts";
import { endpoints } from "../../shared/api/endpoints";
import { getJson } from "../../shared/api/httpClient";

export const campaignQueryKeys = {
  by_id: (campaign_id: string) => ["campaign", campaign_id] as const,
};

export async function fetchCampaignSnapshot(campaign_id: string): Promise<CampaignSnapshot> {
  return getJson<CampaignSnapshot>(endpoints.campaigns.by_id(campaign_id));
}

export function campaignQueryOptions(campaign_id: string) {
  return {
    queryKey: campaignQueryKeys.by_id(campaign_id),
    queryFn: () => fetchCampaignSnapshot(campaign_id),
    retry: false,
  };
}

export function invalidateCampaignQuery(queryClient: QueryClient, campaign_id: string) {
  return queryClient.invalidateQueries({
    queryKey: campaignQueryKeys.by_id(campaign_id),
  });
}

export function useCampaignQuery(campaign_id: string | null) {
  return useQuery({
    queryKey: campaign_id ? campaignQueryKeys.by_id(campaign_id) : ["campaign", "missing"],
    queryFn: () => fetchCampaignSnapshot(campaign_id ?? ""),
    enabled: Boolean(campaign_id),
    retry: false,
  });
}
