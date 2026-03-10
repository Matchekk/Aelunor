import { memo } from "react";

import type { CampaignSnapshot } from "../../shared/api/contracts";
import { SceneChip } from "./components/SceneChip";
import { SceneMembershipList } from "./components/SceneMembershipList";
import {
  deriveSceneFilteringNote,
  deriveSceneMembership,
  deriveSceneOptions,
  deriveSceneSummary,
  hasMeaningfulSceneData,
  type SceneFilterId,
} from "./selectors";

interface SceneSwitcherProps {
  campaign: CampaignSnapshot;
  selected_scene_id: SceneFilterId;
  on_change: (scene_id: SceneFilterId) => void;
}

export const SceneSwitcher = memo(function SceneSwitcher({ campaign, selected_scene_id, on_change }: SceneSwitcherProps) {
  if (!hasMeaningfulSceneData(campaign)) {
    return null;
  }

  const options = deriveSceneOptions(campaign);
  const members = deriveSceneMembership(campaign, selected_scene_id);
  const note = deriveSceneFilteringNote(selected_scene_id);

  return (
    <section className="v1-panel scene-switcher">
      <div className="v1-panel-head">
        <h2>Scene Context</h2>
        <span>{deriveSceneSummary(campaign, selected_scene_id)}</span>
      </div>
      <div className="scene-chip-row" role="tablist" aria-label="Scene filter">
        {options.map((option) => (
          <SceneChip key={option.scene_id} option={option} active={option.scene_id === selected_scene_id} on_select={on_change} />
        ))}
      </div>
      <SceneMembershipList members={members} selected_scene_id={selected_scene_id} />
      {note ? <p className="status-muted">{note}</p> : null}
    </section>
  );
});
