import { useMutation } from "@tanstack/react-query";

import type {
  ContextQueryRequest,
  ContextQueryResponse,
  SubmitTurnRequest,
  SubmitTurnResponse,
} from "../../shared/api/contracts";
import { endpoints } from "../../shared/api/endpoints";
import { postJson } from "../../shared/api/httpClient";

export function useSubmitTurnMutation(campaign_id: string) {
  return useMutation({
    mutationFn: async (payload: SubmitTurnRequest) =>
      postJson<SubmitTurnResponse>(endpoints.campaigns.create_turn(campaign_id), payload),
  });
}

export function useContextQueryMutation(campaign_id: string) {
  return useMutation({
    mutationFn: async (payload: ContextQueryRequest) =>
      postJson<ContextQueryResponse>(endpoints.campaigns.context_query(campaign_id), payload),
  });
}
