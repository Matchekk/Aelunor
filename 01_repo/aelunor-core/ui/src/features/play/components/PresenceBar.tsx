import { memo, useMemo } from "react";

import { usePresenceStore } from "../../../entities/presence/store";
import { derivePresenceSummary } from "../selectors";

export const PresenceBar = memo(function PresenceBar() {
  const sseConnected = usePresenceStore((state) => state.sseConnected);
  const activities = usePresenceStore((state) => state.activities);
  const blockingAction = usePresenceStore((state) => state.blockingAction);
  const version = usePresenceStore((state) => state.version);

  const activityList = useMemo(
    () =>
      Object.entries(activities).map(([player_id, activity]) => ({
        player_id,
        label: activity.label,
        kind: activity.kind,
      })),
    [activities],
  );
  const summary = derivePresenceSummary(sseConnected, activities, blockingAction);

  return (
    <section className="v1-presence">
      <div className="v1-presence-row">
        <span className={sseConnected ? "status-pill connected" : "status-pill disconnected"}>
          {sseConnected ? "SSE connected" : "SSE reconnecting"}
        </span>
        <span className="status-pill">version {version}</span>
        {blockingAction ? <span className="status-pill warning">{blockingAction.label}</span> : null}
      </div>
      <div className="v1-presence-row">
        <span className="status-muted">{summary}</span>
      </div>
      <div className="v1-presence-row">
        {activityList.length === 0 ? (
          <span className="status-muted">No active presence events yet.</span>
        ) : (
          activityList.map((entry) => (
            <span key={`${entry.player_id}-${entry.kind}`} className="status-pill">
              {entry.label}
            </span>
          ))
        )}
      </div>
    </section>
  );
});
