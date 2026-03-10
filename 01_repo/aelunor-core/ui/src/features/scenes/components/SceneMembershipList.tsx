import type { SceneMember } from "../selectors";

interface SceneMembershipListProps {
  members: SceneMember[];
  selected_scene_id: string;
}

export function SceneMembershipList({ members, selected_scene_id }: SceneMembershipListProps) {
  if (members.length === 0) {
    return <p className="status-muted">No party members are currently mapped to this scene.</p>;
  }

  return (
    <ul className="scene-membership-list">
      {members.map((member) => (
        <li key={member.slot_id} className="scene-membership-item">
          <strong>{member.display_name}</strong>
          <span className="status-muted">
            {member.class_name || "No class"}
            {selected_scene_id === "all" && member.scene_name ? ` • ${member.scene_name}` : ""}
          </span>
        </li>
      ))}
    </ul>
  );
}
