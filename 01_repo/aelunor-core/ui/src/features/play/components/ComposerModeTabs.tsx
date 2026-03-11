import { useState } from "react";

import type { PlayModeId } from "../modeConfig";
import { PLAY_MODE_CONFIG } from "../modeConfig";

interface ComposerModeTabsProps {
  current_mode: PlayModeId;
  disabled: boolean;
  on_change: (mode: PlayModeId) => void;
}

export function ComposerModeTabs({ current_mode, disabled, on_change }: ComposerModeTabsProps) {
  const [toolsOpen, setToolsOpen] = useState(current_mode === "canon" || current_mode === "context");
  const primaryModes = PLAY_MODE_CONFIG.filter((mode) => mode.id === "do" || mode.id === "say");
  const secondaryModes = PLAY_MODE_CONFIG.filter((mode) => mode.id === "story");
  const toolModes = PLAY_MODE_CONFIG.filter((mode) => mode.id === "canon" || mode.id === "context");

  return (
    <section className="composer-mode-cluster" aria-label="Zugmodus">
      <div className="composer-mode-tabs action-switch" role="tablist" aria-label="Primäre Modi">
        {primaryModes.map((mode) => (
          <button
            key={mode.id}
            type="button"
            role="tab"
            aria-selected={current_mode === mode.id}
            className={current_mode === mode.id ? "is-active action-mode is-primary" : "action-mode is-primary"}
            disabled={disabled}
            onClick={() => on_change(mode.id)}
          >
            {mode.label}
          </button>
        ))}
        {secondaryModes.map((mode) => (
          <button
            key={mode.id}
            type="button"
            role="tab"
            aria-selected={current_mode === mode.id}
            className={current_mode === mode.id ? "is-active action-mode is-secondary" : "action-mode is-secondary"}
            disabled={disabled}
            onClick={() => on_change(mode.id)}
          >
            {mode.label}
          </button>
        ))}
        <button
          type="button"
          className={toolsOpen ? "action-mode is-tools-toggle is-active" : "action-mode is-tools-toggle"}
          disabled={disabled}
          aria-expanded={toolsOpen}
          onClick={() => {
            setToolsOpen((value) => !value);
          }}
        >
          Mehr
        </button>
      </div>
      {toolsOpen ? (
        <div className="composer-tools-tabs action-switch" role="tablist" aria-label="Werkzeugmodi">
          {toolModes.map((mode) => (
            <button
              key={mode.id}
              type="button"
              role="tab"
              aria-selected={current_mode === mode.id}
              className={current_mode === mode.id ? "is-active action-mode is-tool" : "action-mode is-tool"}
              disabled={disabled}
              onClick={() => on_change(mode.id)}
            >
              {mode.label}
            </button>
          ))}
        </div>
      ) : null}
    </section>
  );
}
