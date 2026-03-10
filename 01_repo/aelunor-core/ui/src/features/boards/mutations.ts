import { useMutation, useQueryClient } from "@tanstack/react-query";

import type {
  AuthorsNotePatchRequest,
  CampaignDeleteResponse,
  CampaignMetaPatchRequest,
  CampaignMutationResponse,
  PlotEssentialsPatchRequest,
  StoryCardCreateRequest,
  StoryCardPatchRequest,
  WorldInfoCreateRequest,
  WorldInfoPatchRequest,
} from "../../shared/api/contracts";
import { invalidateCampaignQuery } from "../../entities/campaign/queries";
import { endpoints } from "../../shared/api/endpoints";
import { httpClient, postJson } from "../../shared/api/httpClient";

export function usePatchPlotEssentialsMutation(campaign_id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: PlotEssentialsPatchRequest) =>
      httpClient<CampaignMutationResponse>(endpoints.campaigns.patch_plot_essentials(campaign_id), {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    onSuccess: async () => {
      await invalidateCampaignQuery(queryClient, campaign_id);
    },
  });
}

export function usePatchAuthorsNoteMutation(campaign_id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: AuthorsNotePatchRequest) =>
      httpClient<CampaignMutationResponse>(endpoints.campaigns.patch_authors_note(campaign_id), {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    onSuccess: async () => {
      await invalidateCampaignQuery(queryClient, campaign_id);
    },
  });
}

export function useCreateStoryCardMutation(campaign_id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: StoryCardCreateRequest) =>
      postJson<CampaignMutationResponse>(endpoints.campaigns.create_story_card(campaign_id), payload),
    onSuccess: async () => {
      await invalidateCampaignQuery(queryClient, campaign_id);
    },
  });
}

export function usePatchStoryCardMutation(campaign_id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ card_id, payload }: { card_id: string; payload: StoryCardPatchRequest }) =>
      httpClient<CampaignMutationResponse>(endpoints.campaigns.patch_story_card(campaign_id, card_id), {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    onSuccess: async () => {
      await invalidateCampaignQuery(queryClient, campaign_id);
    },
  });
}

export function useCreateWorldInfoMutation(campaign_id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: WorldInfoCreateRequest) =>
      postJson<CampaignMutationResponse>(endpoints.campaigns.create_world_info(campaign_id), payload),
    onSuccess: async () => {
      await invalidateCampaignQuery(queryClient, campaign_id);
    },
  });
}

export function usePatchWorldInfoMutation(campaign_id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ entry_id, payload }: { entry_id: string; payload: WorldInfoPatchRequest }) =>
      httpClient<CampaignMutationResponse>(endpoints.campaigns.patch_world_info(campaign_id, entry_id), {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    onSuccess: async () => {
      await invalidateCampaignQuery(queryClient, campaign_id);
    },
  });
}

export function usePatchCampaignMetaMutation(campaign_id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CampaignMetaPatchRequest) =>
      httpClient<CampaignMutationResponse>(endpoints.campaigns.patch_meta(campaign_id), {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    onSuccess: async () => {
      await invalidateCampaignQuery(queryClient, campaign_id);
    },
  });
}

export function useDeleteCampaignMutation(campaign_id: string) {
  return useMutation({
    mutationFn: async () =>
      httpClient<CampaignDeleteResponse>(endpoints.campaigns.delete(campaign_id), {
        method: "DELETE",
      }),
  });
}
