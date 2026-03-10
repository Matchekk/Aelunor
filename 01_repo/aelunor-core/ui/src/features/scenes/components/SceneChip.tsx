import type { SceneOption } from "../selectors";

interface SceneChipProps {
  option: SceneOption;
  active: boolean;
  on_select: (scene_id: SceneOption["scene_id"]) => void;
}

export function SceneChip({ option, active, on_select }: SceneChipProps) {
  return (
    <button type="button" className={active ? "scene-chip is-active" : "scene-chip"} onClick={() => on_select(option.scene_id)}>
      <span>{option.scene_name}</span>
      <span className="status-muted">{option.member_count}</span>
    </button>
  );
}
