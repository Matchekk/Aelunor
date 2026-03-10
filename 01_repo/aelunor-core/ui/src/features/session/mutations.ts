import { useMutation } from "@tanstack/react-query";

import type {
  CreateCampaignRequest,
  CreateCampaignResponse,
  JoinCampaignRequest,
  JoinCampaignResponse,
} from "../../shared/api/contracts";
import { writeSessionBootstrap } from "../../app/bootstrap/sessionStorage";
import { endpoints } from "../../shared/api/endpoints";
import { postJson } from "../../shared/api/httpClient";
import { upsertSessionLibraryEntry } from "./sessionLibrary";

function defaultSessionLabel(campaign_id: string, preferred: string): string {
  const normalizedPreferred = String(preferred ?? "").trim();
  if (normalizedPreferred) {
    return normalizedPreferred;
  }
  return `Session ${campaign_id.slice(0, 8)}`;
}

export function useCreateCampaignMutation() {
  return useMutation({
    mutationFn: async (payload: CreateCampaignRequest) =>
      postJson<CreateCampaignResponse>(endpoints.campaigns.create(), payload),
    onSuccess: (data, variables) => {
      const session = writeSessionBootstrap({
        campaign_id: data.campaign_id,
        player_id: data.player_id,
        player_token: data.player_token,
        join_code: data.join_code,
      });
      upsertSessionLibraryEntry({
        campaign_id: session.campaign_id ?? data.campaign_id,
        player_id: session.player_id ?? data.player_id,
        player_token: session.player_token ?? data.player_token,
        join_code: session.join_code ?? data.join_code,
        label: defaultSessionLabel(data.campaign_id, variables.title),
        campaign_title: data.campaign?.campaign_meta.title ?? variables.title,
        display_name: variables.display_name,
      });
    },
  });
}

export function useJoinCampaignMutation() {
  return useMutation({
    mutationFn: async (payload: JoinCampaignRequest) =>
      postJson<JoinCampaignResponse>(endpoints.campaigns.join(), payload),
    onSuccess: (data, variables) => {
      const session = writeSessionBootstrap({
        campaign_id: data.campaign_id,
        player_id: data.player_id,
        player_token: data.player_token,
        join_code: data.join_code,
      });
      upsertSessionLibraryEntry({
        campaign_id: session.campaign_id ?? data.campaign_id,
        player_id: session.player_id ?? data.player_id,
        player_token: session.player_token ?? data.player_token,
        join_code: session.join_code ?? data.join_code,
        label: defaultSessionLabel(data.campaign_id, data.campaign_summary?.title ?? data.campaign?.campaign_meta.title ?? ""),
        campaign_title: data.campaign_summary?.title ?? data.campaign?.campaign_meta.title ?? null,
        display_name: variables.display_name,
      });
    },
  });
}
