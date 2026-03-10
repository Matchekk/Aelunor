import { useMutation, useQueryClient } from "@tanstack/react-query";

import type {
  SetupAdvanceResponse,
  SetupAnswerPayload,
  SetupRandomApplyRequest,
  SetupRandomResponse,
} from "../../shared/api/contracts";
import { invalidateCampaignQuery } from "../../entities/campaign/queries";
import { endpoints } from "../../shared/api/endpoints";
import { postJson } from "../../shared/api/httpClient";
import type { SetupFlowMode } from "./selectors";

interface SetupMutationScope {
  campaign_id: string;
  mode: SetupFlowMode;
  slot_id?: string | null;
}

function requireSlotId(scope: SetupMutationScope): string {
  if (!scope.slot_id) {
    throw new Error("Character setup requires a slot_id.");
  }
  return scope.slot_id;
}

function setupNextEndpoint(scope: SetupMutationScope): string {
  return scope.mode === "world"
    ? endpoints.campaigns.setup_world_next(scope.campaign_id)
    : endpoints.campaigns.setup_character_next(scope.campaign_id, requireSlotId(scope));
}

function setupAnswerEndpoint(scope: SetupMutationScope): string {
  return scope.mode === "world"
    ? endpoints.campaigns.setup_world_answer(scope.campaign_id)
    : endpoints.campaigns.setup_character_answer(scope.campaign_id, requireSlotId(scope));
}

function setupRandomEndpoint(scope: SetupMutationScope): string {
  return scope.mode === "world"
    ? endpoints.campaigns.setup_world_random(scope.campaign_id)
    : endpoints.campaigns.setup_character_random(scope.campaign_id, requireSlotId(scope));
}

function setupRandomApplyEndpoint(scope: SetupMutationScope): string {
  return scope.mode === "world"
    ? endpoints.campaigns.setup_world_random_apply(scope.campaign_id)
    : endpoints.campaigns.setup_character_random_apply(scope.campaign_id, requireSlotId(scope));
}

export function useSetupNextMutation(scope: SetupMutationScope) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => postJson<SetupAdvanceResponse>(setupNextEndpoint(scope)),
    onSuccess: async () => {
      await invalidateCampaignQuery(queryClient, scope.campaign_id);
    },
  });
}

export function useSetupAnswerMutation(scope: SetupMutationScope) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: SetupAnswerPayload) =>
      postJson<SetupAdvanceResponse>(setupAnswerEndpoint(scope), payload),
    onSuccess: async () => {
      await invalidateCampaignQuery(queryClient, scope.campaign_id);
    },
  });
}

export function useSetupRandomMutation(scope: SetupMutationScope) {
  return useMutation({
    mutationFn: async (payload: { mode: "single" | "all"; question_id?: string | null; preview_answers: SetupAnswerPayload[] }) =>
      postJson<SetupRandomResponse>(setupRandomEndpoint(scope), payload),
  });
}

export function useSetupRandomApplyMutation(scope: SetupMutationScope) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: SetupRandomApplyRequest) =>
      postJson<SetupAdvanceResponse>(setupRandomApplyEndpoint(scope), payload),
    onSuccess: async () => {
      await invalidateCampaignQuery(queryClient, scope.campaign_id);
    },
  });
}
