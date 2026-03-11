import { useCallback, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import "./sessionHub.css";

import type { SessionBootstrap } from "../../app/bootstrap/sessionStorage";
import { clearSessionBootstrap, readSessionBootstrap, writeSessionBootstrap } from "../../app/bootstrap/sessionStorage";
import { buildCampaignPath } from "../../app/routing/routes";
import { deriveRouteRenderState } from "../../app/routing/selectors";
import { campaignQueryOptions } from "../../entities/campaign/queries";
import { useWaitingSignal } from "../../shared/waiting/hooks";
import type { CreateCampaignRequest, JoinCampaignRequest, SessionLibraryEntry } from "../../shared/api/contracts";
import { useCreateCampaignMutation, useJoinCampaignMutation } from "./mutations";
import {
  deleteSessionLibraryEntry,
  exportSessionLibraryEntry,
  forgetSessionLibraryEntry,
  readSessionLibrary,
  renameSessionLibraryEntry,
  upsertSessionLibraryEntry,
} from "./sessionLibrary";
import { hasActiveSession, toSessionBootstrap } from "./selectors";
import { CreateCampaignCard } from "./components/CreateCampaignCard";
import { HubContinuationPanel } from "./components/HubContinuationPanel";
import { HubTopBar } from "./components/HubTopBar";
import { JoinCampaignCard } from "./components/JoinCampaignCard";
import { LlmStatusPanel } from "./components/LlmStatusPanel";
import { SessionEditorDialog } from "./components/SessionEditorDialog";
import { SessionLibraryPanel } from "./components/SessionLibraryPanel";

interface SessionHubWorkspaceProps {
  active_session: SessionBootstrap;
  on_active_session_change: (session: SessionBootstrap) => void;
  route_error_message?: string | null;
}

interface SessionLibraryLocalMeta {
  label?: string;
  campaign_title?: string | null;
  display_name?: string | null;
}

function asErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Unexpected error";
}

function normalizeLabel(campaign_id: string, label: string | undefined): string {
  const normalized = String(label ?? "").trim();
  if (normalized) {
    return normalized;
  }
  return `Session ${campaign_id.slice(0, 8)}`;
}

function buildLocalMeta(input: {
  label?: string | null | undefined;
  campaign_title?: string | null;
  display_name?: string | null;
}): SessionLibraryLocalMeta {
  const next: SessionLibraryLocalMeta = {};

  if (typeof input.label === "string" && input.label.trim()) {
    next.label = input.label;
  }
  if (input.campaign_title !== undefined) {
    next.campaign_title = input.campaign_title;
  }
  if (input.display_name !== undefined) {
    next.display_name = input.display_name;
  }

  return next;
}

function downloadJson(filename: string, payload: Record<string, unknown>): void {
  if (typeof window === "undefined") {
    return;
  }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function activeElement(): HTMLElement | null {
  return document.activeElement instanceof HTMLElement ? document.activeElement : null;
}

export function SessionHubWorkspace({
  active_session,
  on_active_session_change,
  route_error_message = null,
}: SessionHubWorkspaceProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [libraryVersion, setLibraryVersion] = useState(0);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [resumeError, setResumeError] = useState<string | null>(null);
  const [resumePendingCampaignId, setResumePendingCampaignId] = useState<string | null>(null);
  const [lastFailedCampaignId, setLastFailedCampaignId] = useState<string | null>(null);
  const [editingEntry, setEditingEntry] = useState<SessionLibraryEntry | null>(null);
  const [editorReturnFocus, setEditorReturnFocus] = useState<HTMLElement | null>(null);

  const createMutation = useCreateCampaignMutation();
  const joinMutation = useJoinCampaignMutation();

  const libraryEntries = useMemo(() => readSessionLibrary(), [libraryVersion]);
  const latestLibraryEntry = libraryEntries[0] ?? null;
  const currentSessionIsActive = hasActiveSession(active_session);
  const suggestedDisplayName = useMemo(() => {
    if (latestLibraryEntry?.display_name) {
      return latestLibraryEntry.display_name;
    }
    return null;
  }, [latestLibraryEntry]);

  const refreshLibrary = useCallback(() => {
    setLibraryVersion((prev) => prev + 1);
  }, []);

  const clearCurrentSession = useCallback(() => {
    clearSessionBootstrap();
    on_active_session_change(readSessionBootstrap());
    setStatusMessage("Local active session cleared.");
    setResumeError(null);
    setLastFailedCampaignId(null);
  }, [on_active_session_change]);

  const bootstrapSession = useCallback(
    async (session: SessionBootstrap, sourceLabel: string, localMeta: SessionLibraryLocalMeta = {}) => {
      if (!session.campaign_id || !session.player_id || !session.player_token) {
        setResumeError("Session credentials are incomplete.");
        return;
      }

      const rollbackSession = active_session;
      const persisted = writeSessionBootstrap(session);
      const campaign_id = persisted.campaign_id;
      const player_id = persisted.player_id;
      const player_token = persisted.player_token;
      if (!campaign_id || !player_id || !player_token) {
        setResumeError("Session credentials are incomplete.");
        return;
      }
      setResumePendingCampaignId(campaign_id);
      setResumeError(null);
      setStatusMessage(null);
      setLastFailedCampaignId(null);

      try {
        const campaign = await queryClient.fetchQuery(campaignQueryOptions(campaign_id));
        const existingLibraryEntry = readSessionLibrary().find((entry) => entry.campaign_id === campaign_id);
        upsertSessionLibraryEntry({
          campaign_id,
          player_id,
          player_token,
          join_code: persisted.join_code ?? "",
          label: normalizeLabel(campaign_id, localMeta.label ?? existingLibraryEntry?.label),
          campaign_title: localMeta.campaign_title ?? existingLibraryEntry?.campaign_title ?? campaign.campaign_meta.title,
          display_name: localMeta.display_name ?? existingLibraryEntry?.display_name ?? null,
        });
        on_active_session_change(persisted);
        refreshLibrary();
        setStatusMessage(`${sourceLabel}: campaign state validated.`);
        navigate(buildCampaignPath(campaign_id, deriveRouteRenderState(campaign).canonical_workspace));
      } catch (error) {
        const restored = writeSessionBootstrap(rollbackSession);
        on_active_session_change(restored);
        setResumeError(`${sourceLabel} failed: ${asErrorMessage(error)}`);
        setLastFailedCampaignId(campaign_id);
      } finally {
        setResumePendingCampaignId(null);
      }
    },
    [active_session, navigate, on_active_session_change, queryClient, refreshLibrary],
  );

  const handleCreateSubmit = useCallback(
    async (payload: CreateCampaignRequest) => {
      try {
        setStatusMessage(null);
        setResumeError(null);
        await createMutation.mutateAsync(payload);
        refreshLibrary();
        await bootstrapSession(
          readSessionBootstrap(),
          "Create campaign",
          buildLocalMeta({
            label: payload.title,
            campaign_title: payload.title,
            display_name: payload.display_name,
          }),
        );
      } catch (_error) {
        // Error is exposed via mutation state.
      }
    },
    [bootstrapSession, createMutation, refreshLibrary],
  );

  const handleJoinSubmit = useCallback(
    async (payload: JoinCampaignRequest) => {
      try {
        setStatusMessage(null);
        setResumeError(null);
        await joinMutation.mutateAsync(payload);
        refreshLibrary();
        const session = readSessionBootstrap();
        const libraryEntry = session.campaign_id
          ? readSessionLibrary().find((entry) => entry.campaign_id === session.campaign_id)
          : null;
        await bootstrapSession(
          session,
          "Join campaign",
          buildLocalMeta({
            campaign_title: libraryEntry?.campaign_title ?? null,
            display_name: payload.display_name,
          }),
        );
      } catch (_error) {
        // Error is exposed via mutation state.
      }
    },
    [bootstrapSession, joinMutation, refreshLibrary],
  );

  const handleResumeEntry = useCallback(
    async (entry: SessionLibraryEntry) => {
      await bootstrapSession(
        toSessionBootstrap(entry),
        "Resume session",
        buildLocalMeta({
          label: entry.label,
          campaign_title: entry.campaign_title ?? null,
          display_name: entry.display_name ?? null,
        }),
      );
    },
    [bootstrapSession],
  );

  const handleForgetEntry = useCallback(
    (campaign_id: string) => {
      forgetSessionLibraryEntry(campaign_id);
      refreshLibrary();
      if (active_session.campaign_id === campaign_id) {
        clearCurrentSession();
      } else {
        setStatusMessage("Local session entry removed.");
      }
      if (lastFailedCampaignId === campaign_id) {
        setLastFailedCampaignId(null);
      }
    },
    [active_session.campaign_id, clearCurrentSession, lastFailedCampaignId, refreshLibrary],
  );

  const handleRenameEntry = useCallback(
    (campaign_id: string, label: string) => {
      const updated = renameSessionLibraryEntry(campaign_id, label);
      refreshLibrary();
      if (updated) {
        setEditingEntry(updated);
        setStatusMessage("Local session label updated.");
      }
    },
    [refreshLibrary],
  );

  const handleDeleteEntry = useCallback(
    (campaign_id: string) => {
      deleteSessionLibraryEntry(campaign_id);
      refreshLibrary();
      setEditingEntry(null);
      if (active_session.campaign_id === campaign_id) {
        clearCurrentSession();
      } else {
        setStatusMessage("Local session entry deleted.");
      }
      if (lastFailedCampaignId === campaign_id) {
        setLastFailedCampaignId(null);
      }
    },
    [active_session.campaign_id, clearCurrentSession, lastFailedCampaignId, refreshLibrary],
  );

  const handleExportEntry = useCallback((campaign_id: string) => {
    const payload = exportSessionLibraryEntry(campaign_id);
    if (!payload) {
      setResumeError("Unable to export local session entry.");
      return;
    }
    downloadJson(`aelunor-session-${campaign_id}.json`, payload);
    setStatusMessage("Local session exported.");
  }, []);

  const createError = createMutation.isError ? asErrorMessage(createMutation.error) : null;
  const joinError = joinMutation.isError ? asErrorMessage(joinMutation.error) : null;
  const globalErrorMessage = resumeError ?? route_error_message;

  useWaitingSignal({
    key: "hub-create-campaign",
    active: createMutation.isPending,
    context: "campaign_create",
    scope: "surface",
    blocking_level: "local_blocking",
    surface_target: "hub_create",
  });

  useWaitingSignal({
    key: "hub-join-campaign",
    active: joinMutation.isPending,
    context: "campaign_join",
    scope: "surface",
    blocking_level: "local_blocking",
    surface_target: "hub_join",
  });

  useWaitingSignal({
    key: "hub-resume-session",
    active: resumePendingCampaignId !== null,
    context: "session_resume",
    scope: "section",
    blocking_level: "major_blocking",
    surface_target: "hub_resume",
  });

  return (
    <main className="v1-app-shell session-hub-shell gateway-shell">
      <HubTopBar session_count={libraryEntries.length} has_active_session={currentSessionIsActive} />

      {lastFailedCampaignId ? (
        <section className="v1-panel session-card hub-alert-card">
          <div className="v1-panel-head">
            <h2>Stale local credentials</h2>
          </div>
          <p className="status-muted">The stored credentials could not load campaign state from the server.</p>
          <div className="session-inline-actions">
            <button type="button" onClick={() => handleForgetEntry(lastFailedCampaignId)}>
              Forget failed local session
            </button>
            <button type="button" onClick={clearCurrentSession}>
              Clear active credentials
            </button>
          </div>
        </section>
      ) : null}

      <section className="hub-primary-grid">
        <HubContinuationPanel
          has_active_session={currentSessionIsActive}
          active_campaign_id={active_session.campaign_id}
          active_join_code={active_session.join_code}
          latest_entry={latestLibraryEntry}
          resume_pending_campaign_id={resumePendingCampaignId}
          status_message={statusMessage}
          resume_error={globalErrorMessage}
          on_resume_current={() => {
            const libraryEntry = readSessionLibrary().find((entry) => entry.campaign_id === active_session.campaign_id);
            void bootstrapSession(
              active_session,
              "Resume current session",
              buildLocalMeta({
                label: libraryEntry?.label,
                campaign_title: libraryEntry?.campaign_title ?? null,
                display_name: libraryEntry?.display_name ?? null,
              }),
            );
          }}
          on_resume_latest={() => {
            if (!latestLibraryEntry) {
              return;
            }
            void handleResumeEntry(latestLibraryEntry);
          }}
          on_clear_current={clearCurrentSession}
        />

        <section className="hub-actions-grid">
          <CreateCampaignCard
            is_pending={createMutation.isPending}
            error_message={createError}
            default_display_name={suggestedDisplayName}
            on_submit={handleCreateSubmit}
          />
          <JoinCampaignCard
            is_pending={joinMutation.isPending}
            error_message={joinError}
            default_display_name={suggestedDisplayName}
            on_submit={handleJoinSubmit}
          />
        </section>
      </section>

      <section className="hub-campaigns-main">
        <SessionLibraryPanel
          entries={libraryEntries}
          resume_pending_campaign_id={resumePendingCampaignId}
          on_resume={handleResumeEntry}
          on_edit={(entry) => {
            setEditorReturnFocus(activeElement());
            setEditingEntry(entry);
          }}
          on_forget={handleForgetEntry}
        />
      </section>

      <details className="hub-diagnostics">
        <summary>System / Diagnose (optional)</summary>
        <LlmStatusPanel />
      </details>

      <SessionEditorDialog
        open={Boolean(editingEntry)}
        entry={editingEntry}
        return_focus_element={editorReturnFocus}
        on_close={() => setEditingEntry(null)}
        on_rename={handleRenameEntry}
        on_export={handleExportEntry}
        on_delete={handleDeleteEntry}
      />
    </main>
  );
}
