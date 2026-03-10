import { useEffect, useRef } from "react";

import type { SessionBootstrap } from "../../app/bootstrap/sessionStorage";
import type {
  CampaignExportPayload,
  CampaignSnapshot,
  SessionLibraryEntry,
  StoryCardCreateRequest,
  WorldInfoCreateRequest,
} from "../../shared/api/contracts";
import { getJson } from "../../shared/api/httpClient";
import { endpoints } from "../../shared/api/endpoints";
import { useSurfaceLayer } from "../../shared/ui/useSurfaceLayer";
import {
  useCreateStoryCardMutation,
  useCreateWorldInfoMutation,
  useDeleteCampaignMutation,
  usePatchAuthorsNoteMutation,
  usePatchCampaignMetaMutation,
  usePatchPlotEssentialsMutation,
  usePatchStoryCardMutation,
  usePatchWorldInfoMutation,
} from "./mutations";
import type { BoardTabId } from "./selectors";
import { canEditBoards, deriveBoardTabs } from "./selectors";
import { AuthorsNotePanel } from "./components/AuthorsNotePanel";
import { BoardsTabNav } from "./components/BoardsTabNav";
import { MemorySummaryPanel } from "./components/MemorySummaryPanel";
import { PlotEssentialsPanel } from "./components/PlotEssentialsPanel";
import { SessionPanel } from "./components/SessionPanel";
import { StoryCardsPanel } from "./components/StoryCardsPanel";
import { WorldInfoPanel } from "./components/WorldInfoPanel";

interface BoardsModalProps {
  campaign: CampaignSnapshot;
  session: SessionBootstrap;
  open: boolean;
  active_tab: BoardTabId;
  delete_confirm_open: boolean;
  local_entry: SessionLibraryEntry | null;
  rename_value: string;
  return_focus_element: HTMLElement | null;
  on_tab_change: (tab_id: BoardTabId) => void;
  on_close: () => void;
  on_clear_active_session: () => void;
  on_clear_board_novelty: (tab_id: BoardTabId) => void;
  on_rename_change: (value: string) => void;
  on_toggle_delete_confirm: (open: boolean) => void;
  on_remove_local_entry: () => void;
}

function asErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Unexpected error.";
}

function downloadJson(filename: string, payload: unknown): void {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function BoardsModal({
  campaign,
  session,
  open,
  active_tab,
  delete_confirm_open,
  local_entry,
  rename_value,
  return_focus_element,
  on_tab_change,
  on_close,
  on_clear_active_session,
  on_clear_board_novelty,
  on_rename_change,
  on_toggle_delete_confirm,
  on_remove_local_entry,
}: BoardsModalProps) {
  const dialogRef = useRef<HTMLElement | null>(null);
  const canEdit = canEditBoards(campaign);
  const tabs = deriveBoardTabs(campaign.campaign_meta.campaign_id);
  useSurfaceLayer({
    open,
    kind: "modal",
    priority: 40,
    container: dialogRef.current,
    return_focus_element,
    close_on_escape: !delete_confirm_open,
    on_close,
  });

  const plotMutation = usePatchPlotEssentialsMutation(campaign.campaign_meta.campaign_id);
  const noteMutation = usePatchAuthorsNoteMutation(campaign.campaign_meta.campaign_id);
  const createStoryCardMutation = useCreateStoryCardMutation(campaign.campaign_meta.campaign_id);
  const patchStoryCardMutation = usePatchStoryCardMutation(campaign.campaign_meta.campaign_id);
  const createWorldInfoMutation = useCreateWorldInfoMutation(campaign.campaign_meta.campaign_id);
  const patchWorldInfoMutation = usePatchWorldInfoMutation(campaign.campaign_meta.campaign_id);
  const renameMutation = usePatchCampaignMetaMutation(campaign.campaign_meta.campaign_id);
  const deleteCampaignMutation = useDeleteCampaignMutation(campaign.campaign_meta.campaign_id);

  useEffect(() => {
    if (!open) {
      return;
    }
    on_clear_board_novelty(active_tab);
  }, [active_tab, on_clear_board_novelty, open]);

  if (!open) {
    return null;
  }

  const sessionError = renameMutation.isError
    ? asErrorMessage(renameMutation.error)
    : deleteCampaignMutation.isError
      ? asErrorMessage(deleteCampaignMutation.error)
      : null;

  const renderActivePanel = () => {
    switch (active_tab) {
      case "plot":
        return (
          <PlotEssentialsPanel
            board={campaign.boards.plot_essentials}
            can_edit={canEdit}
            pending={plotMutation.isPending}
            error_message={plotMutation.isError ? asErrorMessage(plotMutation.error) : null}
            on_save={(payload) => {
              void plotMutation.mutateAsync(payload);
            }}
          />
        );
      case "note":
        return (
          <AuthorsNotePanel
            board={campaign.boards.authors_note}
            can_edit={canEdit}
            pending={noteMutation.isPending}
            error_message={noteMutation.isError ? asErrorMessage(noteMutation.error) : null}
            on_save={(content) => {
              void noteMutation.mutateAsync({ content });
            }}
          />
        );
      case "cards":
        return (
          <StoryCardsPanel
            cards={campaign.boards.story_cards}
            can_edit={canEdit}
            create_pending={createStoryCardMutation.isPending}
            patch_pending={patchStoryCardMutation.isPending}
            error_message={
              createStoryCardMutation.isError
                ? asErrorMessage(createStoryCardMutation.error)
                : patchStoryCardMutation.isError
                  ? asErrorMessage(patchStoryCardMutation.error)
                  : null
            }
            on_create={(payload: StoryCardCreateRequest) => {
              void createStoryCardMutation.mutateAsync(payload);
            }}
            on_patch={(card_id, payload) => {
              void patchStoryCardMutation.mutateAsync({ card_id, payload });
            }}
          />
        );
      case "world":
        return (
          <WorldInfoPanel
            entries={campaign.boards.world_info}
            can_edit={canEdit}
            create_pending={createWorldInfoMutation.isPending}
            patch_pending={patchWorldInfoMutation.isPending}
            error_message={
              createWorldInfoMutation.isError
                ? asErrorMessage(createWorldInfoMutation.error)
                : patchWorldInfoMutation.isError
                  ? asErrorMessage(patchWorldInfoMutation.error)
                  : null
            }
            on_create={(payload: WorldInfoCreateRequest) => {
              void createWorldInfoMutation.mutateAsync(payload);
            }}
            on_patch={(entry_id, payload) => {
              void patchWorldInfoMutation.mutateAsync({ entry_id, payload });
            }}
          />
        );
      case "memory":
        return <MemorySummaryPanel board={campaign.boards.memory_summary} />;
      case "session":
        return (
          <SessionPanel
            campaign_title={campaign.campaign_meta.title}
            updated_at={campaign.campaign_meta.updated_at}
            session={session}
            local_entry={local_entry}
            can_edit={canEdit}
            rename_value={rename_value}
            rename_pending={renameMutation.isPending}
            delete_pending={deleteCampaignMutation.isPending}
            error_message={sessionError}
            delete_confirm_open={delete_confirm_open}
            on_rename_change={on_rename_change}
            on_save_rename={() => {
              void renameMutation.mutateAsync({ title: rename_value.trim() || "Untitled session" });
            }}
            on_export_campaign={() => {
              void getJson<CampaignExportPayload>(endpoints.campaigns.export(campaign.campaign_meta.campaign_id)).then((data) => {
                downloadJson(`${campaign.campaign_meta.title || "campaign"}.json`, data);
              });
            }}
            on_toggle_delete_confirm={on_toggle_delete_confirm}
            on_delete_campaign={() => {
              void deleteCampaignMutation.mutateAsync(undefined, {
                onSuccess: () => {
                  on_remove_local_entry();
                  on_close();
                  on_clear_active_session();
                },
              });
            }}
            on_remove_local_entry={on_remove_local_entry}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="boards-modal-backdrop" role="presentation" onClick={on_close}>
      <section
        ref={dialogRef}
        className="boards-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Boards workspace"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="boards-modal-header">
          <div>
            <div className="v1-topbar-kicker">Campaign Meta</div>
            <h1>{campaign.campaign_meta.title || "Campaign boards"}</h1>
            <p className="status-muted">
              Boards stay separate from the main story flow. Only the active tab mounts inside this workspace.
            </p>
          </div>
          <div className="session-inline-actions">
            <button type="button" onClick={on_close}>
              Close boards
            </button>
          </div>
        </header>

        <BoardsTabNav tabs={tabs} active_tab={active_tab} on_change={on_tab_change} />

        <div className="boards-modal-body">{renderActivePanel()}</div>
      </section>
    </div>
  );
}
