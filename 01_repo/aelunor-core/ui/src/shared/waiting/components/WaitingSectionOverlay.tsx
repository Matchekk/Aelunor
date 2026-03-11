import type { WaitingSurfaceTarget } from "../model";
import { useWaitingForTarget } from "../hooks";
import { WaitingMotif } from "./WaitingMotif";

interface WaitingSectionOverlayProps {
  target: WaitingSurfaceTarget;
  className?: string;
}

export function WaitingSectionOverlay({ target, className }: WaitingSectionOverlayProps) {
  const presentation = useWaitingForTarget(target, {
    min_scope: "section",
  });

  if (!presentation) {
    return null;
  }

  const classes = ["waiting-section-layer", `waiting-stage-${presentation.stage}`, className].filter(Boolean).join(" ");

  return (
    <div className={classes} role="status" aria-live="polite">
      <div className="waiting-section-card">
        <WaitingMotif stage={presentation.stage} size="lg" />
        <div className="waiting-copy">
          <strong>{presentation.heading}</strong>
          <small>{presentation.detail}</small>
        </div>
      </div>
    </div>
  );
}
