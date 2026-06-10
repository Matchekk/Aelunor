import type { PlayModeId } from "../modeConfig";
import { PLAY_MODE_CONFIG } from "../modeConfig";

interface ComposerModeTabsProps {
  current_mode: PlayModeId;
  disabled: boolean;
  on_change: (mode: PlayModeId) => void;
}

function modeVariant(mode_id: PlayModeId): string {
  if (mode_id === "story") {
    return "is-secondary";
  }
  if (mode_id === "canon" || mode_id === "context") {
    return "is-tool";
  }
  return "is-primary";
}

export function ComposerModeTabs({ current_mode, disabled, on_change }: ComposerModeTabsProps) {
  return (
    <section className="composer-mode-cluster" aria-label="Zugmodus">
      <div className="composer-mode-tabs action-switch" role="tablist" aria-label="Zugmodi">
        {PLAY_MODE_CONFIG.map((mode) => (
          <button
            key={mode.id}
            type="button"
            role="tab"
            aria-selected={current_mode === mode.id}
            className={`action-mode ${modeVariant(mode.id)}${current_mode === mode.id ? " is-active" : ""}`}
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
