import type { PlayModeId } from "../modeConfig";
import { PLAY_MODE_CONFIG } from "../modeConfig";

interface ComposerModeTabsProps {
  current_mode: PlayModeId;
  disabled: boolean;
  on_change: (mode: PlayModeId) => void;
}

export function ComposerModeTabs({ current_mode, disabled, on_change }: ComposerModeTabsProps) {
  return (
    <div className="composer-mode-tabs" role="tablist" aria-label="Turn mode">
      {PLAY_MODE_CONFIG.map((mode) => (
        <button
          key={mode.id}
          type="button"
          role="tab"
          aria-selected={current_mode === mode.id}
          className={current_mode === mode.id ? "is-active" : ""}
          disabled={disabled}
          onClick={() => on_change(mode.id)}
        >
          {mode.label}
        </button>
      ))}
    </div>
  );
}
