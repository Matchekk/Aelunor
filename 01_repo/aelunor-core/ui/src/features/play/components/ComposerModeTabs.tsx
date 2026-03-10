import type { PlayModeId } from "../modeConfig";
import { PLAY_MODE_CONFIG } from "../modeConfig";

interface ComposerModeTabsProps {
  current_mode: PlayModeId;
  disabled: boolean;
  on_change: (mode: PlayModeId) => void;
}

export function ComposerModeTabs({ current_mode, disabled, on_change }: ComposerModeTabsProps) {
  return (
    <section className="composer-mode-cluster" aria-label="Turn mode">
      <div className="composer-mode-tabs action-switch" role="tablist" aria-label="Turn modes">
        {PLAY_MODE_CONFIG.map((mode) => (
          <button
            key={mode.id}
            type="button"
            role="tab"
            aria-selected={current_mode === mode.id}
            className={current_mode === mode.id ? "is-active action-mode" : "action-mode"}
            disabled={disabled}
            onClick={() => on_change(mode.id)}
          >
            {mode.label}
          </button>
        ))}
      </div>
    </section>
  );
}
