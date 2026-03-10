from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


ACTION_TYPES = ("do", "say", "story", "canon")


class CampaignCreateIn(BaseModel):
    title: str = "Neue Aelunor-Kampagne"
    display_name: str


class JoinCampaignIn(BaseModel):
    join_code: str
    display_name: str


class SlotClaimIn(BaseModel):
    slot_id: str


class SetupAnswerIn(BaseModel):
    question_id: str
    value: Optional[Any] = None
    selected: Optional[Any] = None
    other_text: str = ""
    other_values: List[str] = Field(default_factory=list)


class SetupRandomIn(BaseModel):
    question_id: Optional[str] = None
    mode: Literal["single", "all"] = "single"
    preview_answers: List["SetupAnswerIn"] = Field(default_factory=list)


class SetupRandomApplyIn(BaseModel):
    question_id: Optional[str] = None
    mode: Literal["single", "all"] = "single"
    preview_answers: List[SetupAnswerIn] = Field(default_factory=list)


class TurnCreateIn(BaseModel):
    actor: str
    mode: Optional[str] = None
    text: Optional[str] = None
    action_type: Optional[Literal["do", "say", "story", "canon"]] = None
    content: Optional[str] = None

    def normalized_action_type(self) -> str:
        raw_mode = str(self.mode or self.action_type or "").strip().lower()
        mapping = {
            "tun": "do",
            "do": "do",
            "sagen": "say",
            "say": "say",
            "story": "story",
            "canon": "canon",
            "kanon": "canon",
        }
        normalized = mapping.get(raw_mode, "")
        if normalized not in ACTION_TYPES:
            raise ValueError("Unbekannter Turn-Modus.")
        return normalized

    def normalized_content(self) -> str:
        return str(self.text if self.text is not None else self.content or "")


class TurnEditIn(BaseModel):
    input_text_display: str
    gm_text_display: str


class ContextQueryIn(BaseModel):
    text: str
    actor: Optional[str] = None


class PresenceActivityIn(BaseModel):
    kind: Literal["typing_turn", "editing_turn", "claiming_slot", "building_character", "building_world", "reviewing_choices"]
    slot_id: Optional[str] = None
    target_turn_id: Optional[str] = None


class PlotEssentialsPatchIn(BaseModel):
    premise: Optional[str] = None
    current_goal: Optional[str] = None
    current_threat: Optional[str] = None
    active_scene: Optional[str] = None
    open_loops: Optional[List[str]] = None
    tone: Optional[str] = None


class AuthorsNotePatchIn(BaseModel):
    content: str


class PlayerDiaryPatchIn(BaseModel):
    content: str


class StoryCardCreateIn(BaseModel):
    title: str
    kind: Literal["npc", "location", "faction", "item", "hook", "rule"]
    content: str
    tags: List[str] = Field(default_factory=list)


class StoryCardPatchIn(BaseModel):
    title: Optional[str] = None
    kind: Optional[Literal["npc", "location", "faction", "item", "hook", "rule"]] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    archived: Optional[bool] = None


class WorldInfoCreateIn(BaseModel):
    title: str
    category: str
    content: str
    tags: List[str] = Field(default_factory=list)


class WorldInfoPatchIn(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None


class CampaignMetaPatchIn(BaseModel):
    title: str


class TimeAdvanceIn(BaseModel):
    days: int = 0
    time_of_day: Optional[str] = None
    reason: str = ""


class ClassUnlockIn(BaseModel):
    class_id: str
    class_name: Optional[str] = None
    visual_modifiers: List[Dict[str, Any]] = Field(default_factory=list)


class FactionJoinIn(BaseModel):
    faction_id: str
    name: str
    rank: str = ""
    visual_modifiers: List[Dict[str, Any]] = Field(default_factory=list)

