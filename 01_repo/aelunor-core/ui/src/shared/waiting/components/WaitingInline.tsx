import type { WaitingSurfaceTarget } from "../model";
import { useWaitingForTarget } from "../hooks";
import { WaitingMotif } from "./WaitingMotif";

interface WaitingInlineProps {
  target: WaitingSurfaceTarget;
  className?: string;
}

export function WaitingInline({ target, className }: WaitingInlineProps) {
  const presentation = useWaitingForTarget(target, {
    min_scope: "inline",
    max_scope: "inline",
  });

  if (!presentation) {
    return null;
  }

  const classes = ["waiting-inline", `waiting-stage-${presentation.stage}`, className].filter(Boolean).join(" ");

  return (
    <div className={classes} role="status" aria-live="polite" aria-atomic="true">
      <WaitingMotif stage={presentation.stage} size="sm" />
      <div className="waiting-copy">
        <strong>{presentation.heading}</strong>
        <small>{presentation.detail}</small>
      </div>
    </div>
  );
}
