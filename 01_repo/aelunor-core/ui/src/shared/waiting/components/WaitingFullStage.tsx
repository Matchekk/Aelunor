import type { WaitingContextId, WaitingSurfaceTarget } from "../model";
import { useWaitingForTarget, useWaitingSignal } from "../hooks";
import { WaitingMotif } from "./WaitingMotif";

interface WaitingFullStageProps {
  target: WaitingSurfaceTarget;
  context: WaitingContextId;
  active: boolean;
  heading?: string;
  detail?: string;
}

export function WaitingFullStage({ target, context, active, heading, detail }: WaitingFullStageProps) {
  useWaitingSignal({
    key: `full-stage:${target}:${context}`,
    active,
    context,
    scope: "full",
    blocking_level: "full_blocking",
    surface_target: target,
    message_override: heading ?? null,
    detail_override: detail ?? null,
  });

  const presentation = useWaitingForTarget(target, {
    min_scope: "full",
  });

  const fallbackHeading = heading ?? "Bitte kurz warten";
  const fallbackDetail = detail ?? "Der angeforderte Bereich wird vorbereitet.";
  const stage = presentation?.stage ?? 0;
  const displayHeading = presentation?.heading ?? fallbackHeading;
  const displayDetail = presentation?.detail ?? fallbackDetail;

  if (!active) {
    return null;
  }

  return (
    <main className="v1-app-shell waiting-full-stage" role="status" aria-live="polite">
      <section className="v1-panel waiting-full-card">
        <WaitingMotif stage={stage} size="lg" />
        <div className="waiting-copy">
          <h2>{displayHeading}</h2>
          <p>{displayDetail}</p>
        </div>
      </section>
    </main>
  );
}
