import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { useLocation, useNavigate, type NavigateOptions } from "react-router-dom";

import { buildCampaignPath, buildSurfaceHistoryState, buildV1HubPath, normalizePlayRouteState, serializePlayRouteState, withBoardsRouteState, withContextRouteState, withDrawerRouteState, withSceneRouteState } from "../../app/routing/routes";
import type { SessionBootstrap } from "../../app/bootstrap/sessionStorage";
import type { CampaignSnapshot, ContextQueryResponse } from "../../shared/api/contracts";
import { usePresenceStore } from "../../entities/presence/store";
import { deriveUserFacingErrorMessage } from "../../shared/errors/userFacing";
import { BoardsModal } from "../boards/BoardsModal";
import type { BoardTabId } from "../boards/selectors";
import { ContextModal } from "../context/ContextModal";
import { readContextCache, writeContextCache } from "../context/cache";
import { useContextStore } from "../context/contextStore";
import { DrawerHost } from "../drawers/DrawerHost";
import { useDrawerStore } from "../drawers/drawerStore";
import { deriveFilteredTimelineEntries, deriveSceneOptions, type SceneFilterId } from "../scenes/selectors";
import { clearBoardNovelty, trackCampaignNovelty } from "./novelty";
import { readSessionLibrary, deleteSessionLibraryEntry } from "../session/sessionLibrary";
import { useLayoutStore } from "../../state/layoutStore";
import { useUserSettingsStore } from "../../entities/settings/store";
import { StoryTimeline } from "./components/StoryTimeline";
import { TopBar } from "./components/TopBar";
import { Composer } from "./components/Composer";
import { TurnEditModal } from "./components/TurnEditModal";
import { derivePlayPhaseState } from "./selectors";
import type { TimelineEntry } from "./selectors";
import { useEditTurnMutation, useRetryIntroMutation, useRetryTurnMutation, useSubmitTurnMutation, useUndoTurnMutation } from "./mutations";
import { buildContinueTurnPayload, shouldShowContinueAction } from "./turnActions";
import { useUnclaimSlotMutation } from "../claim/mutations";
import { PrePlayOverview } from "./components/PrePlayOverview";
import { PrePlayComposerHint } from "./components/PrePlayComposerHint";
import { readPlayUiMemory, writePlayUiMemory } from "./uiMemory";
import { AelunorSceneBackground } from "../../shared/ui/aelunorAssets";
import { WorldRail } from "./components/WorldRail";
import { ActorDock } from "./components/ActorDock";
import { resolveSelectedActorId } from "./actorDockModel";
import { useResizableComposerHeight } from "./composerResize";

interface CampaignWorkspaceProps {
  campaign: CampaignSnapshot;
  session: SessionBootstrap;
  on_clear_active_session: () => void;
}

function activeElement(): HTMLElement | null {
  return document.activeElement instanceof HTMLElement ? document.activeElement : null;
}

export function CampaignWorkspace({ campaign, session, on_clear_active_session }: CampaignWorkspaceProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const rightRailOpen = useLayoutStore((state) => state.rightRailOpen);
  const setRightRailOpen = useLayoutStore((state) => state.setRightRailOpen);
  const rememberFilters = useUserSettingsStore((state) => state.interaction.remember_filters);
  const phaseState = useMemo(() => derivePlayPhaseState(campaign), [campaign]);
  const [boardsDeleteConfirmOpen, setBoardsDeleteConfirmOpen] = useState(false);
  const [boardsReturnFocus, setBoardsReturnFocus] = useState<HTMLElement | null>(null);
  const [editTurnEntry, setEditTurnEntry] = useState<TimelineEntry | null>(null);
  const [editTurnReturnFocus, setEditTurnReturnFocus] = useState<HTMLElement | null>(null);
  const [sessionRenameValue, setSessionRenameValue] = useState(campaign.campaign_meta.title || "");
  const [noveltyVersion, setNoveltyVersion] = useState(0);
  const [selectedActorId, setSelectedActorId] = useState<string | null>(null);
  const previousCampaignRef = useRef<CampaignSnapshot | null>(null);
  const rememberedUiHydratedRef = useRef<string | null>(null);
  const drawerReturnFocusRef = useRef<HTMLElement | null>(null);
  const contextReturnFocusRef = useRef<HTMLElement | null>(null);
  const centerColumnRef = useRef<HTMLElement | null>(null);
  const { composer_height, handle_props } = useResizableComposerHeight(centerColumnRef);
  const playRouteState = useMemo(() => normalizePlayRouteState(campaign, location.search), [campaign, location.search]);
  const selectedSceneId = playRouteState.scene_id as SceneFilterId;
  const claimedSlotId = campaign.viewer_context?.claimed_slot_id || null;
  const boardsOpen = playRouteState.boards_tab !== null;
  const activeBoardTab: BoardTabId = playRouteState.boards_tab ?? "plot";
  const openCharacter = useDrawerStore((state) => state.open_character);
  const openNpc = useDrawerStore((state) => state.open_npc);
  const openCodex = useDrawerStore((state) => state.open_codex);
  const closeDrawerStore = useDrawerStore((state) => state.close_drawer);
  const setActiveDrawerTab = useDrawerStore((state) => state.set_active_tab);
  const drawerOpen = useDrawerStore((state) => state.drawer_open);
  const drawerType = useDrawerStore((state) => state.drawer_type);
  const drawerEntityId = useDrawerStore((state) => state.drawer_entity_id);
  const drawerCodexKind = useDrawerStore((state) => state.drawer_codex_kind);
  const contextOpen = useContextStore((state) => state.open);
  const openContextStore = useContextStore((state) => state.open_context);
  const closeContextStore = useContextStore((state) => state.close_context);
  const blockingAction = usePresenceStore((state) => state.blockingAction);
  const unclaimMutation = useUnclaimSlotMutation(campaign.campaign_meta.campaign_id);
  const retryIntroMutation = useRetryIntroMutation(campaign.campaign_meta.campaign_id);
  const continueTurnMutation = useSubmitTurnMutation(campaign.campaign_meta.campaign_id);
  const editTurnMutation = useEditTurnMutation(campaign.campaign_meta.campaign_id);
  const undoTurnMutation = useUndoTurnMutation(campaign.campaign_meta.campaign_id);
  const retryTurnMutation = useRetryTurnMutation(campaign.campaign_meta.campaign_id);

  useEffect(() => {
    setSessionRenameValue(campaign.campaign_meta.title || "");
  }, [campaign.campaign_meta.title]);

  useEffect(() => {
    const changed = trackCampaignNovelty(previousCampaignRef.current, campaign);
    previousCampaignRef.current = campaign;
    if (changed) {
      setNoveltyVersion((value) => value + 1);
    }
  }, [campaign]);

  const localEntry = useMemo(
    () => readSessionLibrary().find((entry) => entry.campaign_id === campaign.campaign_meta.campaign_id) ?? null,
    [campaign.campaign_meta.campaign_id, noveltyVersion],
  );
  const sceneOptions = useMemo(() => deriveSceneOptions(campaign), [campaign]);
  const selectedScene = useMemo(
    () => sceneOptions.find((entry) => entry.scene_id === selectedSceneId) ?? null,
    [sceneOptions, selectedSceneId],
  );
  const selectedActorSlotId = useMemo(() => resolveSelectedActorId(campaign, selectedActorId), [campaign, selectedActorId]);
  const selectedActorLabel = useMemo(() => {
    if (!selectedActorSlotId) {
      return "Kein Akteur";
    }
    return (
      (campaign.party_overview ?? []).find((entry) => entry.slot_id === selectedActorSlotId)?.display_name ??
      (campaign.display_party ?? []).find((entry) => entry.slot_id === selectedActorSlotId)?.display_name ??
      selectedActorSlotId
    );
  }, [campaign.display_party, campaign.party_overview, selectedActorSlotId]);
  const isPreplay = !phaseState.is_active_play;
  const activeSceneLabel = selectedScene?.scene_name ?? (selectedSceneId === "all" ? "Alle Szenen" : selectedSceneId);
  const visibleTimelineEntries = useMemo(
    () => deriveFilteredTimelineEntries(campaign, selectedSceneId),
    [campaign.active_turns, campaign.state, selectedSceneId],
  );
  const canContinueTurn = shouldShowContinueAction({
    is_active_play: phaseState.is_active_play,
    is_latest_turn: visibleTimelineEntries.length > 0,
    claimed_slot_id: claimedSlotId,
  });
  const turnActionsPending =
    continueTurnMutation.isPending || editTurnMutation.isPending || undoTurnMutation.isPending || retryTurnMutation.isPending;
  const turnActionPendingId =
    undoTurnMutation.variables ?? retryTurnMutation.variables ?? editTurnMutation.variables?.turn_id ?? null;
  const turnActionError = continueTurnMutation.isError
    ? deriveUserFacingErrorMessage(continueTurnMutation.error, "Der Fortsetzen-Zug konnte nicht erstellt werden.")
    : editTurnMutation.isError
      ? deriveUserFacingErrorMessage(editTurnMutation.error, "Der Zug konnte nicht gespeichert werden.")
      : undoTurnMutation.isError
        ? deriveUserFacingErrorMessage(undoTurnMutation.error, "Der Zug konnte nicht zurückgenommen werden.")
        : retryTurnMutation.isError
          ? deriveUserFacingErrorMessage(retryTurnMutation.error, "Der Zug konnte nicht erneut ausgeführt werden.")
          : null;
  const editTurnError = editTurnMutation.isError
    ? deriveUserFacingErrorMessage(editTurnMutation.error, "Der Zug konnte nicht gespeichert werden.")
    : null;

  const navigatePlayState = useCallback(
    (nextState: typeof playRouteState, options?: NavigateOptions) => {
      navigate(`${buildCampaignPath(campaign.campaign_meta.campaign_id, "play")}${serializePlayRouteState(nextState)}`, options);
    },
    [campaign.campaign_meta.campaign_id, navigate],
  );

  const closeSurface = useCallback(
    (surface: "boards" | "drawer" | "context", fallbackState: typeof playRouteState) => {
      const routeState = location.state as Record<string, unknown> | null;
      if (routeState?.aelunor_surface === surface) {
        navigate(-1);
        return;
      }
      navigatePlayState(fallbackState, { replace: true });
    },
    [location.state, navigate, navigatePlayState],
  );

  useEffect(() => {
    if (!rememberFilters) {
      rememberedUiHydratedRef.current = null;
      return;
    }

    const campaignId = campaign.campaign_meta.campaign_id;
    if (rememberedUiHydratedRef.current === campaignId) {
      return;
    }

    const remembered = readPlayUiMemory(campaignId);
    if (typeof remembered.right_rail_open === "boolean") {
      setRightRailOpen(remembered.right_rail_open);
    }

    const hasExplicitScene = new URLSearchParams(location.search).has("scene");
    if (!hasExplicitScene && remembered.scene_id && remembered.scene_id !== "all") {
      const hasRememberedScene = sceneOptions.some((entry) => entry.scene_id === remembered.scene_id);
      if (hasRememberedScene) {
        const nextState = withSceneRouteState(playRouteState, remembered.scene_id as SceneFilterId);
        navigatePlayState(nextState, { replace: true });
      }
    }

    rememberedUiHydratedRef.current = campaignId;
  }, [
    campaign.campaign_meta.campaign_id,
    location.search,
    navigatePlayState,
    playRouteState,
    rememberFilters,
    sceneOptions,
    setRightRailOpen,
  ]);

  useEffect(() => {
    if (!rememberFilters) {
      return;
    }
    writePlayUiMemory(campaign.campaign_meta.campaign_id, {
      scene_id: selectedSceneId,
      right_rail_open: rightRailOpen,
    });
  }, [campaign.campaign_meta.campaign_id, rememberFilters, rightRailOpen, selectedSceneId]);

  useEffect(() => {
    if (selectedActorSlotId !== selectedActorId) {
      setSelectedActorId(selectedActorSlotId);
    }
  }, [selectedActorId, selectedActorSlotId]);

  const openCharacterDrawer = useCallback(
    (slot_id: string, tab_id?: string) => {
      setActiveDrawerTab(tab_id ?? "overview");
      drawerReturnFocusRef.current = activeElement();
      navigatePlayState(withDrawerRouteState(playRouteState, { drawer_type: "character", entity_id: slot_id, codex_kind: null }), {
        state: buildSurfaceHistoryState("drawer", location.pathname, location.search),
      });
    },
    [location.pathname, location.search, navigatePlayState, playRouteState, setActiveDrawerTab],
  );
  const openNpcDrawer = useCallback(
    (npc_id: string, tab_id?: string) => {
      setActiveDrawerTab(tab_id ?? "overview");
      drawerReturnFocusRef.current = activeElement();
      navigatePlayState(withDrawerRouteState(playRouteState, { drawer_type: "npc", entity_id: npc_id, codex_kind: null }), {
        state: buildSurfaceHistoryState("drawer", location.pathname, location.search),
      });
    },
    [location.pathname, location.search, navigatePlayState, playRouteState, setActiveDrawerTab],
  );
  const openCodexDrawer = useCallback(
    (kind: "race" | "beast", entity_id: string, tab_id?: string) => {
      setActiveDrawerTab(tab_id ?? "overview");
      drawerReturnFocusRef.current = activeElement();
      navigatePlayState(withDrawerRouteState(playRouteState, { drawer_type: "codex", entity_id, codex_kind: kind }), {
        state: buildSurfaceHistoryState("drawer", location.pathname, location.search),
      });
    },
    [location.pathname, location.search, navigatePlayState, playRouteState, setActiveDrawerTab],
  );
  const openBoards = useCallback((tab_id: BoardTabId = activeBoardTab) => {
    if (boardsOpen && activeBoardTab === tab_id) {
      return;
    }
    setBoardsReturnFocus(activeElement());
    setBoardsDeleteConfirmOpen(false);
    navigatePlayState(withBoardsRouteState(playRouteState, tab_id), {
      state: buildSurfaceHistoryState("boards", location.pathname, location.search),
    });
  }, [activeBoardTab, boardsOpen, location.pathname, location.search, navigatePlayState, playRouteState]);

  const openContextModal = useCallback(
    (payload: ContextQueryResponse, returnFocus: HTMLElement | null) => {
      contextReturnFocusRef.current = returnFocus;
      writeContextCache(campaign.campaign_meta.campaign_id, payload);
      openContextStore(payload, returnFocus);
      navigatePlayState(withContextRouteState(playRouteState), {
        state: buildSurfaceHistoryState("context", location.pathname, location.search),
      });
    },
    [campaign.campaign_meta.campaign_id, location.pathname, location.search, navigatePlayState, openContextStore, playRouteState],
  );

  useEffect(() => {
    const drawerIntent = playRouteState.drawer;
    if (!drawerIntent) {
      if (drawerOpen) {
        closeDrawerStore();
      }
      return;
    }

    const matchesCurrentDrawer =
      drawerOpen &&
      drawerType === drawerIntent.drawer_type &&
      drawerEntityId === drawerIntent.entity_id &&
      drawerCodexKind === drawerIntent.codex_kind;

    if (matchesCurrentDrawer) {
      return;
    }

    if (drawerIntent.drawer_type === "character") {
      openCharacter(drawerIntent.entity_id, undefined, drawerReturnFocusRef.current);
    } else if (drawerIntent.drawer_type === "npc") {
      openNpc(drawerIntent.entity_id, undefined, drawerReturnFocusRef.current);
    } else {
      openCodex(drawerIntent.codex_kind ?? "race", drawerIntent.entity_id, undefined, drawerReturnFocusRef.current);
    }

    drawerReturnFocusRef.current = null;
  }, [
    closeDrawerStore,
    drawerCodexKind,
    drawerEntityId,
    drawerOpen,
    drawerType,
    openCharacter,
    openCodex,
    openNpc,
    playRouteState.drawer,
  ]);

  useEffect(() => {
    if (!playRouteState.context_open) {
      if (contextOpen) {
        closeContextStore();
      }
      return;
    }

    if (contextOpen) {
      return;
    }

    const cachedPayload = readContextCache(campaign.campaign_meta.campaign_id);
    if (!cachedPayload) {
      navigatePlayState({ ...playRouteState, context_open: false }, { replace: true });
      return;
    }

    openContextStore(cachedPayload, contextReturnFocusRef.current);
    contextReturnFocusRef.current = null;
  }, [campaign.campaign_meta.campaign_id, closeContextStore, contextOpen, navigatePlayState, openContextStore, playRouteState]);

  return (
    <main className="v1-app-shell campaign-play-shell aelunor-game-shell">
      <AelunorSceneBackground wallpaper="wallpaper-ancient-temple-arcane" />
      <div className="campaign-play-content">
        <TopBar
          campaign={campaign}
          session={session}
          active_scene_label={activeSceneLabel}
          active_actor_label={selectedActorLabel}
          can_unclaim={Boolean(claimedSlotId)}
          unclaim_pending={unclaimMutation.isPending}
          on_open_codex={() => openBoards("world")}
          on_open_notifications={() => openBoards("memory")}
          on_unclaim={() => {
            if (!claimedSlotId) {
              return;
            }
            void unclaimMutation.mutateAsync(claimedSlotId);
          }}
          on_leave_session={() => {
            on_clear_active_session();
            navigate(buildV1HubPath(), { replace: true });
          }}
        />
        <section className={rightRailOpen ? "campaign-play-grid" : "campaign-play-grid is-actor-collapsed"}>
          <WorldRail
            campaign={campaign}
            active_scene_label={activeSceneLabel}
            selected_actor_id={selectedActorSlotId}
            on_select_actor={setSelectedActorId}
            on_open_scene={() => openBoards("world")}
            on_open_quest={() => openBoards("plot")}
            on_open_map={() => openBoards("world")}
          />
          <section
            ref={centerColumnRef}
            className={`campaign-main-column story-workspace story-surface timeline-column${isPreplay ? " is-preplay" : " is-active-play"}`}
            style={{ "--play-composer-height": `${composer_height}px` } as CSSProperties}
          >
            {isPreplay ? (
              <PrePlayOverview
                campaign={campaign}
                on_open_boards={openBoards}
                on_retry_intro={() => {
                  void retryIntroMutation.mutateAsync();
                }}
                intro_retry_pending={retryIntroMutation.isPending}
              />
            ) : null}
            <StoryTimeline
              entries={visibleTimelineEntries}
              character_sheet_slots={campaign.character_sheet_slots ?? []}
              selected_scene_id={selectedSceneId}
              selected_scene_name={selectedSceneId === "all" ? null : selectedScene?.scene_name ?? selectedSceneId}
              scene_options={sceneOptions}
              is_preplay={isPreplay}
              can_continue_turn={canContinueTurn}
              turn_actions_pending={turnActionsPending || Boolean(blockingAction)}
              turn_action_pending_id={turnActionPendingId}
              turn_action_error={turnActionError}
              on_scene_change={(scene_id) => {
                navigatePlayState(withSceneRouteState(playRouteState, scene_id), {
                  state: buildSurfaceHistoryState("scene", location.pathname, location.search),
                });
              }}
              on_open_character={openCharacterDrawer}
              on_edit_turn={(entry) => {
                setEditTurnReturnFocus(activeElement());
                setEditTurnEntry(entry);
              }}
              on_undo_turn={(turn_id) => {
                void undoTurnMutation.mutateAsync(turn_id);
              }}
              on_retry_turn={(turn_id) => {
                void retryTurnMutation.mutateAsync(turn_id);
              }}
              on_continue_turn={() => {
                if (!claimedSlotId || !phaseState.is_active_play) {
                  return;
                }
                void continueTurnMutation.mutateAsync(buildContinueTurnPayload(claimedSlotId));
              }}
            />
            {isPreplay ? (
              <PrePlayComposerHint phase_display={phaseState.phase_display} />
            ) : (
              <>
                <div className="composer-resize-handle" {...handle_props}>
                  <i aria-hidden="true" />
                </div>
                <Composer
                  campaign={campaign}
                  selected_actor_id={selectedActorSlotId}
                  on_actor_select={setSelectedActorId}
                  on_open_context={openContextModal}
                />
              </>
            )}
          </section>
          <button
            type="button"
            className="actor-rail-drawer-handle"
            aria-label={rightRailOpen ? "Akteurleiste ausblenden" : "Akteurleiste einblenden"}
            aria-expanded={rightRailOpen}
            title={rightRailOpen ? "Akteurleiste ausblenden" : "Akteurleiste einblenden"}
            onClick={() => setRightRailOpen(!rightRailOpen)}
          >
            <span className="actor-rail-drawer-grip" aria-hidden="true">{rightRailOpen ? "}" : "{"}</span>
          </button>
          {rightRailOpen ? (
            <ActorDock
              campaign={campaign}
              selected_slot_id={selectedActorSlotId}
              on_open_character={openCharacterDrawer}
            />
          ) : null}
        </section>
      </div>
      <BoardsModal
        campaign={campaign}
        session={session}
        open={boardsOpen}
        active_tab={activeBoardTab}
        delete_confirm_open={boardsDeleteConfirmOpen}
        local_entry={localEntry}
        rename_value={sessionRenameValue}
        return_focus_element={boardsReturnFocus}
        on_tab_change={(tab_id) => {
          navigatePlayState(withBoardsRouteState(playRouteState, tab_id), {
            replace: true,
            state: location.state,
          });
        }}
        on_close={() => {
          setBoardsDeleteConfirmOpen(false);
          closeSurface("boards", { ...playRouteState, boards_tab: null });
        }}
        on_clear_active_session={on_clear_active_session}
        on_clear_board_novelty={(tab_id) => {
          if (clearBoardNovelty(campaign.campaign_meta.campaign_id, tab_id)) {
            setNoveltyVersion((value) => value + 1);
          }
        }}
        on_rename_change={setSessionRenameValue}
        on_toggle_delete_confirm={setBoardsDeleteConfirmOpen}
        on_remove_local_entry={() => {
          deleteSessionLibraryEntry(campaign.campaign_meta.campaign_id);
          setNoveltyVersion((value) => value + 1);
        }}
      />
      <DrawerHost
        campaign={campaign}
        on_novelty_change={() => setNoveltyVersion((value) => value + 1)}
        on_close={() => {
          closeSurface("drawer", { ...playRouteState, drawer: null });
        }}
      />
      <ContextModal
        campaign={campaign}
        on_close={() => {
          closeSurface("context", { ...playRouteState, context_open: false });
        }}
      />
      <TurnEditModal
        campaign_id={campaign.campaign_meta.campaign_id}
        open={Boolean(editTurnEntry)}
        turn={
          editTurnEntry
            ? {
                turn_id: editTurnEntry.turn_id,
                turn_number: editTurnEntry.turn_number,
                actor_display: editTurnEntry.actor_display,
                input_text_display: editTurnEntry.input_text_display,
                gm_text_display: editTurnEntry.gm_text_display,
                slot_id: claimedSlotId,
              }
            : null
        }
        pending={editTurnMutation.isPending}
        error_message={editTurnError}
        return_focus_element={editTurnReturnFocus}
        on_close={() => {
          if (!editTurnMutation.isPending) {
            setEditTurnEntry(null);
          }
        }}
        on_save={({ turn_id, input_text_display, gm_text_display }) => {
          void editTurnMutation.mutateAsync(
            {
              turn_id,
              payload: {
                input_text_display,
                gm_text_display,
              },
            },
            {
              onSuccess: () => {
                setEditTurnEntry(null);
              },
            },
          );
        }}
      />
    </main>
  );
}
