import { useRef } from "react";

import type { CampaignSnapshot } from "../../shared/api/contracts";
import { useSurfaceLayer } from "../../shared/ui/useSurfaceLayer";
import { useContextStore } from "./contextStore";
import { deriveContextActorLabel, deriveContextScopeLabels, deriveContextSourceKinds, deriveContextTitle } from "./selectors";
import { ContextHeader } from "./components/ContextHeader";
import { ContextMetaBar } from "./components/ContextMetaBar";
import { ContextResultPanel } from "./components/ContextResultPanel";

interface ContextModalProps {
  campaign: CampaignSnapshot;
  on_close: () => void;
}

export function ContextModal({ campaign, on_close }: ContextModalProps) {
  const dialogRef = useRef<HTMLElement | null>(null);
  const open = useContextStore((state) => state.open);
  const payload = useContextStore((state) => state.payload);
  const return_focus_element = useContextStore((state) => state.return_focus_element);
  useSurfaceLayer({
    open,
    kind: "modal",
    priority: 45,
    container: dialogRef.current,
    return_focus_element,
    on_close,
  });

  if (!open || !payload) {
    return null;
  }

  return (
    <div className="context-modal-backdrop" role="presentation" onClick={on_close}>
      <section
        ref={dialogRef}
        className="context-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Context result"
        onClick={(event) => event.stopPropagation()}
      >
        <ContextHeader title={deriveContextTitle(payload)} question={payload.question} on_close={on_close} />
        <ContextMetaBar
          actor_label={deriveContextActorLabel(payload, campaign)}
          status={payload.result.status}
          intent={payload.result.intent || "unknown"}
          confidence={payload.result.confidence || "low"}
          source_kinds={deriveContextSourceKinds(payload.result.sources ?? [])}
          scope_labels={deriveContextScopeLabels(payload, campaign)}
        />
        <ContextResultPanel payload={payload} />
      </section>
    </div>
  );
}
