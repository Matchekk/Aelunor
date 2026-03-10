import type { FontPresetId, FontSizeId, ThemeId } from "../types/domain";

export interface ThemeState {
  theme: ThemeId;
  font_preset: FontPresetId;
  font_size: FontSizeId;
}

export interface PresenceActivity {
  kind: string;
  label: string;
  slot_id?: string | null;
  target_turn_id?: string | null;
  blocking: boolean;
  updated_at: string;
  expires_at: string;
}

export interface PresenceBlockingAction {
  kind: string;
  label: string;
  slot_id?: string | null;
  player_id?: string | null;
  started_at: string;
  expires_at: string;
}

export interface PresenceState {
  version: number;
  activities: Record<string, PresenceActivity>;
  blocking_action: PresenceBlockingAction | null;
}

export interface PlayerContext {
  player_id: string | null;
  display_name: string | null;
  is_host: boolean;
  claimed_slot_id: string | null;
  claimed_character: string | null;
  phase: string;
  needs_world_setup: boolean;
  needs_character_setup: boolean;
  pending_setup_question?: SetupPromptState | null;
}

export interface CampaignMeta {
  campaign_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  status: string;
  host_player_id: string;
}

export interface WorldTimeSnapshot {
  absolute_day?: number;
  year?: number;
  month?: number;
  day?: number;
  time_of_day?: string;
  weather?: string;
}

export interface CampaignTurn {
  turn_id: string;
  turn_number: number;
  status: string;
  actor: string;
  actor_display: string;
  player_id?: string | null;
  action_type: string;
  mode: string;
  input_text_display: string;
  gm_text_display: string;
  requests: TurnRequest[];
  retry_of_turn_id?: string | null;
  created_at: string;
  updated_at: string;
  edited_at?: string | null;
  edit_count: number;
  patch_summary: Record<string, number>;
  narrator_patch?: Record<string, unknown>;
  extractor_patch?: Record<string, unknown>;
  source_mode?: string;
  canon_applied?: boolean;
  scene_id?: string | null;
  scene_name?: string | null;
  can_edit: boolean;
  can_undo: boolean;
  can_retry: boolean;
}

export interface DisplayPartyEntry {
  slot_id: string;
  display_name: string;
}

export interface CampaignPlayer {
  player_id: string;
  display_name: string;
  joined_at?: string | null;
  last_seen_at?: string | null;
}

export interface PlotEssentialsBoard {
  premise: string;
  current_goal: string;
  current_threat: string;
  active_scene: string;
  open_loops: string[];
  tone: string;
  updated_at: string;
  updated_by?: string | null;
}

export interface AuthorsNoteBoard {
  content: string;
  updated_at: string;
  updated_by?: string | null;
}

export interface StoryCardEntry {
  card_id: string;
  title: string;
  kind: "npc" | "location" | "faction" | "item" | "hook" | "rule";
  content: string;
  tags: string[];
  archived: boolean;
  updated_at: string;
  updated_by?: string | null;
}

export interface WorldInfoEntry {
  entry_id: string;
  title: string;
  category: string;
  content: string;
  tags: string[];
  updated_at: string;
  updated_by?: string | null;
}

export interface MemorySummaryBoard {
  content: string;
  updated_through_turn: number;
  updated_at: string;
}

export interface PlayerDiaryBoardEntry {
  player_id: string;
  display_name: string;
  content: string;
  updated_at?: string | null;
  updated_by?: string | null;
}

export interface CampaignBoardsSnapshot {
  plot_essentials: PlotEssentialsBoard;
  authors_note: AuthorsNoteBoard;
  story_cards: StoryCardEntry[];
  world_info: WorldInfoEntry[];
  memory_summary: MemorySummaryBoard;
  player_diaries?: Record<string, PlayerDiaryBoardEntry>;
}

export interface PartyOverviewEntry {
  slot_id: string;
  display_name: string;
  claimed_by?: string | null;
  claimed_by_name?: string | null;
  scene_id?: string;
  scene_name?: string;
  class_name?: string;
  class_rank?: string;
  class_level?: number | null;
  class_level_max?: number | null;
  level?: number;
  hp_current?: number;
  hp_max?: number;
  sta_current?: number;
  sta_max?: number;
  res_current?: number;
  res_max?: number;
  resource_name?: string;
  injury_count?: number;
  scar_count?: number;
  conditions?: string[];
  in_combat?: boolean;
}

export interface AvailableSlotSnapshot {
  slot_id: string;
  claimed_by?: string | null;
  claimed_by_name?: string | null;
  completed?: boolean;
  display_name: string;
  summary?: Record<string, unknown>;
  class_name?: string;
  class_rank?: string;
  class_level?: number;
  class_level_max?: number;
}

export interface SetupReadyCounter {
  ready: number;
  total: number;
}

export interface SetupSlotStatus {
  slot_id: string;
  display_name: string;
  claimed_by?: string | null;
  status: string;
  completed: boolean;
}

export interface SetupRuntimeWorld {
  completed?: boolean;
  progress?: SetupProgressPayload;
  global_progress?: SetupProgressPayload;
  next_question?: SetupPromptState | null;
  chapter_key?: string;
  chapter_label?: string;
  chapter_index?: number;
  chapter_total?: number;
  chapter_progress?: SetupProgressPayload;
  is_review_step?: boolean;
  summary_preview?: Record<string, unknown>;
  slot_statuses?: SetupSlotStatus[];
  ready_counter?: SetupReadyCounter;
}

export interface SetupRuntimeCharacter {
  question?: SetupQuestionPayload;
  progress?: SetupProgressPayload;
  global_progress?: SetupProgressPayload;
  chapter_key?: string;
  chapter_label?: string;
  chapter_index?: number;
  chapter_total?: number;
  chapter_progress?: SetupProgressPayload;
  is_review_step?: boolean;
  summary_preview?: Record<string, unknown>;
}

export interface SetupRuntimeSnapshot {
  phase?: string;
  phase_display?: string;
  world?: SetupRuntimeWorld;
  claimed_slot_id?: string | null;
  character?: SetupRuntimeCharacter | null;
  slot_statuses?: SetupSlotStatus[];
  ready_counter?: SetupReadyCounter;
  is_ready_to_start?: boolean;
}

export interface CampaignSnapshot {
  campaign_meta: CampaignMeta;
  state: Record<string, unknown>;
  setup: Record<string, unknown>;
  setup_runtime: SetupRuntimeSnapshot;
  available_slots: AvailableSlotSnapshot[];
  claims: Record<string, unknown>;
  active_party: string[];
  display_party: DisplayPartyEntry[];
  world_time: WorldTimeSnapshot;
  boards: CampaignBoardsSnapshot;
  active_turns: CampaignTurn[];
  party_overview: PartyOverviewEntry[];
  character_sheet_slots: string[];
  ui_panels: Record<string, string[]>;
  players: CampaignPlayer[];
  viewer_context: PlayerContext;
  live: PresenceState;
}

export interface CampaignSyncEvent {
  version: number;
  reason: string;
}

export interface IntroStateSnapshot {
  status: string;
  last_error?: string;
  last_attempt_at?: string;
  generated_turn_id?: string;
}

export interface TurnRequest {
  type: string;
  actor: string;
  question?: string;
  options?: string[];
}

export type SetupQuestionType = "text" | "textarea" | "boolean" | "select" | "multiselect";

export interface SetupOptionEntry {
  value: string;
  label: string;
  description?: string;
}

export interface SetupAnswerPayload {
  question_id: string;
  value?: string | boolean | null;
  selected?: string[];
  other_text?: string;
  other_values?: string[];
}

export interface SetupQuestionPayload {
  question_id: string;
  label: string;
  type: SetupQuestionType;
  required: boolean;
  options: string[];
  option_entries: SetupOptionEntry[];
  min_selected?: number | null;
  max_selected?: number | null;
  allow_other: boolean;
  other_hint?: string;
  ai_copy: string;
  existing_answer?: string | boolean | Record<string, unknown> | null;
}

export interface SetupProgressPayload {
  answered: number;
  total: number;
  step: number;
}

export interface SetupPromptState {
  question: SetupQuestionPayload;
  progress: SetupProgressPayload;
}

export interface SetupRandomPreviewEntry {
  question_id: string;
  label: string;
  type: SetupQuestionType;
  preview_text: string;
  answer: SetupAnswerPayload;
}

export interface CampaignMutationResponse {
  campaign: CampaignSnapshot;
}

export interface CampaignExportPayload extends CampaignSnapshot {}

export interface CampaignDeleteResponse {
  ok: boolean;
  campaign_id: string;
}

export interface PlotEssentialsPatchRequest {
  premise?: string;
  current_goal?: string;
  current_threat?: string;
  active_scene?: string;
  open_loops?: string[];
  tone?: string;
}

export interface AuthorsNotePatchRequest {
  content: string;
}

export interface StoryCardCreateRequest {
  title: string;
  kind: StoryCardEntry["kind"];
  content: string;
  tags: string[];
}

export interface StoryCardPatchRequest {
  title?: string;
  kind?: StoryCardEntry["kind"];
  content?: string;
  tags?: string[];
  archived?: boolean;
}

export interface WorldInfoCreateRequest {
  title: string;
  category: string;
  content: string;
  tags: string[];
}

export interface WorldInfoPatchRequest {
  title?: string;
  category?: string;
  content?: string;
  tags?: string[];
}

export interface CampaignMetaPatchRequest {
  title: string;
}

export interface CharacterResourceBar {
  hp_current?: number;
  hp_max?: number;
  sta_current?: number;
  sta_max?: number;
  res_current?: number;
  res_max?: number;
  resource_name?: string;
}

export interface CharacterClassSnapshot {
  id?: string;
  name?: string;
  rank?: string;
  level?: number;
  level_max?: number;
  xp?: number;
  xp_next?: number;
  affinity_tags?: string[];
  description?: string;
  ascension?: Record<string, unknown>;
}

export interface CharacterProgressionSnapshot {
  level?: number;
  xp_current?: number;
  xp_to_next?: number;
  xp_total?: number;
}

export interface CharacterSkillSnapshot {
  id?: string;
  name?: string;
  level?: number;
  level_max?: number;
  xp?: number;
  next_xp?: number;
  rank?: string;
  mastery?: number;
  tags?: string[];
  description?: string;
  cost?: string;
  price?: string;
  cooldown_turns?: number | null;
  unlocked_from?: string;
  synergy_notes?: string;
  class_match?: boolean;
  effective_progress_multiplier?: number;
}

export interface CharacterSheetOverview {
  bio?: Record<string, unknown>;
  resources?: CharacterResourceBar;
  resource_label?: string;
  class_current?: CharacterClassSnapshot | null;
  character_progression?: CharacterProgressionSnapshot;
  injury_count?: number;
  scar_count?: number;
  location?: {
    scene_id?: string;
    scene_name?: string;
  };
  claim_status?: string;
  appearance?: Record<string, unknown>;
  ageing?: Record<string, unknown>;
}

export interface CharacterEquipmentEntry {
  item_id?: string | null;
  name: string;
  rarity?: string;
  weight?: number;
}

export interface CharacterInventoryItem {
  item_id: string;
  name: string;
  stack: number;
  rarity?: string;
  weight?: number;
  slot?: string;
  cursed?: boolean;
}

export interface CharacterInjuryEntry {
  id?: string;
  title?: string;
  severity?: string;
  healing_stage?: string;
  will_scar?: boolean;
  effects?: string[];
  notes?: string;
  description?: string;
  created_turn?: number;
}

export interface CharacterSheetResponse {
  slot_id: string;
  display_name: string;
  scene_id?: string;
  scene_name?: string;
  claimed_by_name?: string | null;
  sheet: {
    overview: CharacterSheetOverview;
    stats: {
      attributes?: Record<string, number>;
      attribute_scale?: {
        label?: string;
        min?: number;
        max?: number;
      };
      derived?: Record<string, unknown>;
      resistances?: Record<string, unknown>;
      age_modifiers?: Record<string, unknown>;
      modifier_summary?: Record<string, number>;
    };
    skills: CharacterSkillSnapshot[];
    class: {
      current?: CharacterClassSnapshot | null;
      ascension_plotpoint?: Record<string, unknown> | null;
    };
    injuries_scars: {
      injuries: CharacterInjuryEntry[];
      scars: CharacterInjuryEntry[];
    };
    gear_inventory: {
      equipment: Record<string, CharacterEquipmentEntry>;
      quick_slots?: Record<string, unknown>;
      inventory_items: CharacterInventoryItem[];
      carry_weight?: number;
      carry_limit?: number;
      encumbrance_state?: string;
    };
    effects?: Record<string, unknown>[];
    journal?: Record<string, unknown>;
    progression?: Record<string, unknown>;
    skill_meta?: {
      fusion_possible?: boolean;
      fusion_hints?: Array<{ label?: string; result_rank?: string }>;
      resource_name?: string;
    };
    meta?: {
      faction_memberships?: Record<string, unknown>[];
    };
  };
  derived_explainer?: Record<string, string>;
  timeline_refs?: Record<string, unknown>[];
}

export interface NpcSkillSnapshot {
  id?: string;
  name?: string;
  level?: number;
  level_max?: number;
  rank?: string;
  tags?: string[];
  description?: string;
}

export interface NpcSheetResponse {
  npc_id: string;
  name: string;
  race?: string;
  age?: string;
  goal?: string;
  level?: number;
  xp_total?: number;
  xp_current?: number;
  xp_to_next?: number;
  backstory_short?: string;
  role_hint?: string;
  faction?: string;
  status?: string;
  last_seen_scene_id?: string;
  last_seen_scene_name?: string;
  first_seen_turn?: number;
  last_seen_turn?: number;
  mention_count?: number;
  relevance_score?: number;
  history_notes?: string[];
  tags?: string[];
  class_current?: CharacterClassSnapshot | null;
  skills?: NpcSkillSnapshot[];
  resources?: CharacterResourceBar;
  conditions?: string[];
  injuries?: CharacterInjuryEntry[];
  scars?: CharacterInjuryEntry[];
}

export interface CreateCampaignRequest {
  title: string;
  display_name: string;
}

export interface JoinCampaignRequest {
  join_code: string;
  display_name: string;
}

export interface CampaignSummary {
  title: string;
  status: string;
}

export interface CreateCampaignResponse {
  campaign_id: string;
  join_code: string;
  player_id: string;
  player_token: string;
  campaign?: CampaignSnapshot;
}

export interface JoinCampaignResponse {
  campaign_id: string;
  join_code: string;
  player_id: string;
  player_token: string;
  campaign_summary?: CampaignSummary;
  campaign?: CampaignSnapshot;
}

export interface ClaimSlotResponse {
  campaign: CampaignSnapshot;
}

export interface TakeoverSlotResponse {
  campaign: CampaignSnapshot;
}

export interface UnclaimSlotResponse {
  campaign: CampaignSnapshot;
}

export interface SetupAdvanceResponse {
  completed: boolean;
  question: SetupQuestionPayload | null;
  progress: SetupProgressPayload;
  campaign: CampaignSnapshot;
  started_adventure?: boolean;
  turn_id?: string | null;
  randomized_count?: number;
}

export interface SetupRandomRequest {
  question_id?: string | null;
  mode: "single" | "all";
  preview_answers: SetupAnswerPayload[];
}

export interface SetupRandomResponse {
  mode: "single" | "all";
  question_id?: string | null;
  preview_answers: SetupRandomPreviewEntry[];
  randomized_count: number;
}

export interface SetupRandomApplyRequest {
  question_id?: string | null;
  mode: "single" | "all";
  preview_answers: SetupAnswerPayload[];
}

export interface SubmitTurnRequest {
  actor: string;
  mode: string;
  text: string;
}

export interface SubmitTurnResponse {
  turn_id: string;
  trace_id: string;
  campaign: CampaignSnapshot;
}

export interface ContextQueryRequest {
  actor: string;
  text: string;
}

export interface ContextQueryResultSource {
  type: string;
  id: string;
  label: string;
}

export interface ContextQueryResult {
  status: string;
  intent?: string;
  target?: string;
  confidence?: string;
  entity_type?: string;
  entity_id?: string;
  title?: string;
  explanation?: string;
  facts?: string[];
  sources?: ContextQueryResultSource[];
  suggestions?: string[];
}

export interface ContextQueryResponse {
  answer: string;
  actor: string;
  question: string;
  result: ContextQueryResult;
}

export interface LlmModelStatus {
  name: string;
  size: number | null;
  parameter_size: string | null;
  family: string | null;
}

export interface LlmStatusResponse {
  ollama_url: string;
  configured_model: string;
  request_timeout_sec: number;
  seed: number | null;
  temperature: number;
  num_ctx: number;
  ollama_ok: boolean;
  configured_model_available: boolean;
  available_models: LlmModelStatus[];
  error: string;
}

export interface SessionLibraryEntry {
  campaign_id: string;
  player_id: string;
  player_token: string;
  join_code: string;
  label: string;
  updated_at: string;
  campaign_title?: string | null;
  display_name?: string | null;
}
