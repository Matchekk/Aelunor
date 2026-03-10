import type { BoardTabId } from "../selectors";

interface BoardsTabNavProps {
  tabs: Array<{ id: BoardTabId; label: string; novelty_label: string | null }>;
  active_tab: BoardTabId;
  on_change: (tab_id: BoardTabId) => void;
}

export function BoardsTabNav({ tabs, active_tab, on_change }: BoardsTabNavProps) {
  return (
    <div className="boards-tab-nav" role="tablist" aria-label="Boards tabs">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={active_tab === tab.id}
          className={active_tab === tab.id ? "is-active" : ""}
          onClick={() => on_change(tab.id)}
        >
          <span>{tab.label}</span>
          {tab.novelty_label ? <span className="status-pill warning">{tab.novelty_label}</span> : null}
        </button>
      ))}
    </div>
  );
}
