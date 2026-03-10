import { useEffect, useMemo, useRef, type ReactNode } from "react";

import { useQuery } from "@tanstack/react-query";

import type { CampaignSnapshot, CharacterSheetResponse, NpcSheetResponse } from "../../shared/api/contracts";
import { endpoints } from "../../shared/api/endpoints";
import { getJson } from "../../shared/api/httpClient";
import { useSurfaceLayer } from "../../shared/ui/useSurfaceLayer";
import { clearCharacterNovelty, clearCodexNovelty } from "../play/novelty";
import { useDrawerStore } from "./drawerStore";
import { buildCodexDrawerPayload, deriveCharacterDrawerSubtitle, deriveDrawerTabs, deriveNpcDrawerSubtitle } from "./selectors";
import { CharacterDrawer } from "./components/CharacterDrawer";
import { CodexDrawer } from "./components/CodexDrawer";
import { DrawerErrorState } from "./components/DrawerErrorState";
import { DrawerHeader } from "./components/DrawerHeader";
import { DrawerLoadingState } from "./components/DrawerLoadingState";
import { DrawerTabs } from "./components/DrawerTabs";
import { NpcDrawer } from "./components/NpcDrawer";

interface DrawerHostProps {
  campaign: CampaignSnapshot;
  on_novelty_change: () => void;
  on_close: () => void;
}

function asErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Unexpected drawer error.";
}

export function DrawerHost({ campaign, on_novelty_change, on_close }: DrawerHostProps) {
  const dialogRef = useRef<HTMLElement | null>(null);
  const drawer_open = useDrawerStore((state) => state.drawer_open);
  const drawer_type = useDrawerStore((state) => state.drawer_type);
  const drawer_entity_id = useDrawerStore((state) => state.drawer_entity_id);
  const drawer_codex_kind = useDrawerStore((state) => state.drawer_codex_kind);
  const active_drawer_tab = useDrawerStore((state) => state.active_drawer_tab);
  const return_focus_element = useDrawerStore((state) => state.return_focus_element);
  const set_active_tab = useDrawerStore((state) => state.set_active_tab);
  useSurfaceLayer({
    open: drawer_open,
    kind: "drawer",
    priority: 20,
    container: dialogRef.current,
    return_focus_element,
    on_close,
  });

  const characterQuery = useQuery({
    queryKey: ["drawer", "character", campaign.campaign_meta.campaign_id, drawer_entity_id],
    queryFn: () => getJson<CharacterSheetResponse>(endpoints.campaigns.character_sheet(campaign.campaign_meta.campaign_id, drawer_entity_id ?? "")),
    enabled: drawer_open && drawer_type === "character" && Boolean(drawer_entity_id),
    retry: false,
  });

  const npcQuery = useQuery({
    queryKey: ["drawer", "npc", campaign.campaign_meta.campaign_id, drawer_entity_id],
    queryFn: () => getJson<NpcSheetResponse>(endpoints.campaigns.npc_sheet(campaign.campaign_meta.campaign_id, drawer_entity_id ?? "")),
    enabled: drawer_open && drawer_type === "npc" && Boolean(drawer_entity_id),
    retry: false,
  });

  const codexPayload = useMemo(
    () =>
      drawer_open && drawer_type === "codex" && drawer_entity_id && drawer_codex_kind
        ? buildCodexDrawerPayload(campaign, drawer_codex_kind, drawer_entity_id)
        : null,
    [campaign, drawer_codex_kind, drawer_entity_id, drawer_open, drawer_type],
  );

  const tabs =
    drawer_open && drawer_type && drawer_entity_id
      ? deriveDrawerTabs(drawer_type, campaign.campaign_meta.campaign_id, drawer_entity_id, drawer_codex_kind)
      : [];

  useEffect(() => {
    if (!drawer_open || !drawer_type || !drawer_entity_id) {
      return;
    }

    if (drawer_type === "character") {
      if (clearCharacterNovelty(campaign.campaign_meta.campaign_id, drawer_entity_id, active_drawer_tab)) {
        on_novelty_change();
      }
    }
    if (drawer_type === "codex" && drawer_codex_kind) {
      if (clearCodexNovelty(campaign.campaign_meta.campaign_id, drawer_codex_kind, drawer_entity_id)) {
        on_novelty_change();
      }
    }
  }, [active_drawer_tab, campaign.campaign_meta.campaign_id, drawer_codex_kind, drawer_entity_id, drawer_open, drawer_type, on_novelty_change]);

  if (!drawer_open || !drawer_type || !drawer_entity_id) {
    return null;
  }

  let title = "Drawer";
  let subtitle = "Read-only";
  let body: ReactNode = null;

  if (drawer_type === "character") {
    if (characterQuery.isPending) {
      body = <DrawerLoadingState />;
    } else if (characterQuery.isError || !characterQuery.data) {
      body = <DrawerErrorState message={asErrorMessage(characterQuery.error)} on_retry={() => void characterQuery.refetch()} on_close={on_close} />;
    } else {
      title = characterQuery.data.display_name;
      subtitle = deriveCharacterDrawerSubtitle(characterQuery.data);
      body = <CharacterDrawer sheet={characterQuery.data} active_tab={active_drawer_tab} />;
    }
  } else if (drawer_type === "npc") {
    if (npcQuery.isPending) {
      body = <DrawerLoadingState />;
    } else if (npcQuery.isError || !npcQuery.data) {
      body = <DrawerErrorState message={asErrorMessage(npcQuery.error)} on_retry={() => void npcQuery.refetch()} on_close={on_close} />;
    } else {
      title = npcQuery.data.name;
      subtitle = deriveNpcDrawerSubtitle(npcQuery.data);
      body = <NpcDrawer sheet={npcQuery.data} active_tab={active_drawer_tab} />;
    }
  } else {
    if (!codexPayload) {
      body = <DrawerErrorState message="Codex entry could not be derived from the current snapshot." on_close={on_close} />;
    } else {
      title = codexPayload.name;
      subtitle = `${codexPayload.kind === "race" ? "Race" : "Beast"} • knowledge ${codexPayload.knowledge_level}/4`;
      body = <CodexDrawer payload={codexPayload} active_tab={active_drawer_tab} />;
    }
  }

  return (
    <div className="drawer-backdrop" role="presentation" onClick={on_close}>
      <aside
        ref={dialogRef}
        className="drawer-shell"
        role="dialog"
        aria-modal="true"
        aria-label="Campaign drawer"
        onClick={(event) => event.stopPropagation()}
      >
        <DrawerHeader title={title} subtitle={subtitle} on_close={on_close} />
        <DrawerTabs tabs={tabs} active_tab={active_drawer_tab} on_change={set_active_tab} />
        <div className="drawer-body">{body}</div>
      </aside>
    </div>
  );
}
