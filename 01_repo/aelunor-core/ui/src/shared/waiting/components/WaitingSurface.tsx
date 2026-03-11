import type { WaitingSurfaceTarget } from "../model";
import { useWaitingForTarget } from "../hooks";
import { WaitingMotif } from "./WaitingMotif";

interface WaitingSurfaceProps {
  target: WaitingSurfaceTarget;
  className?: string;
}

export function WaitingSurface({ target, className }: WaitingSurfaceProps) {
  const presentation = useWaitingForTarget(target, {
    min_scope: "surface",
  });

  if (!presentation) {
    return null;
  }

  const blocking = presentation.signal.blocking_level !== "non_blocking";
  const classes = [
    "waiting-surface-layer",
    `waiting-stage-${presentation.stage}`,
    blocking ? "is-blocking" : "is-passive",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={classes} role="status" aria-live="polite">
      <div className="waiting-surface-card">
        <WaitingMotif stage={presentation.stage} size="md" />
        <div className="waiting-copy">
          <strong>{presentation.heading}</strong>
          <small>{presentation.detail}</small>
        </div>
      </div>
    </div>
  );
}
