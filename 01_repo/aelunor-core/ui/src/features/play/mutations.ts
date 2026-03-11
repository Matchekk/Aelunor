import { useMutation, useQueryClient } from "@tanstack/react-query";

import type {
  CampaignMutationResponse,
  ContextQueryRequest,
  ContextQueryResponse,
  PlayerDiaryPatchRequest,
  RetryIntroResponse,
  SubmitTurnRequest,
  SubmitTurnResponse,
  TurnEditRequest,
  TurnEditResponse,
  TurnRetryResponse,
  TurnUndoResponse,
} from "../../shared/api/contracts";
import { invalidateCampaignQuery } from "../../entities/campaign/queries";
import { endpoints } from "../../shared/api/endpoints";
import { httpClient, postJson } from "../../shared/api/httpClient";

export function useSubmitTurnMutation(campaign_id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: SubmitTurnRequest) =>
      postJson<SubmitTurnResponse>(endpoints.campaigns.create_turn(campaign_id), payload),
    onSuccess: async () => {
      await invalidateCampaignQuery(queryClient, campaign_id);
    },
  });
}

export function useContextQueryMutation(campaign_id: string) {
  return useMutation({
    mutationFn: async (payload: ContextQueryRequest) =>
      postJson<ContextQueryResponse>(endpoints.campaigns.context_query(campaign_id), payload),
  });
}

export function useRetryIntroMutation(campaign_id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => postJson<RetryIntroResponse>(endpoints.campaigns.retry_intro(campaign_id)),
    onSuccess: async () => {
      await invalidateCampaignQuery(queryClient, campaign_id);
    },
  });
}

export function useEditTurnMutation(campaign_id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ turn_id, payload }: { turn_id: string; payload: TurnEditRequest }) =>
      httpClient<TurnEditResponse>(endpoints.campaigns.edit_turn(campaign_id, turn_id), {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    onSuccess: async () => {
      await invalidateCampaignQuery(queryClient, campaign_id);
    },
  });
}

export function useUndoTurnMutation(campaign_id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (turn_id: string) =>
      postJson<TurnUndoResponse>(endpoints.campaigns.undo_turn(campaign_id, turn_id)),
    onSuccess: async () => {
      await invalidateCampaignQuery(queryClient, campaign_id);
    },
  });
}

export function useRetryTurnMutation(campaign_id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (turn_id: string) =>
      postJson<TurnRetryResponse>(endpoints.campaigns.retry_turn(campaign_id, turn_id)),
    onSuccess: async () => {
      await invalidateCampaignQuery(queryClient, campaign_id);
    },
  });
}

export function usePatchPlayerDiaryMutation(campaign_id: string, player_id: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: PlayerDiaryPatchRequest) => {
      if (!player_id) {
        throw new Error("Spieler-ID für Diary fehlt.");
      }
      return httpClient<CampaignMutationResponse>(endpoints.campaigns.patch_player_diary(campaign_id, player_id), {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
    },
    onSuccess: async () => {
      await invalidateCampaignQuery(queryClient, campaign_id);
    },
  });
}
