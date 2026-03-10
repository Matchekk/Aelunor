import { useRef } from "react";

import type { ClaimSlotViewModel } from "../selectors";
import { useSurfaceLayer } from "../../../shared/ui/useSurfaceLayer";

interface TakeoverConfirmDialogProps {
  slot: ClaimSlotViewModel | null;
  open: boolean;
  pending: boolean;
  error_message: string | null;
  return_focus_element?: HTMLElement | null;
  on_close: () => void;
  on_confirm: (slot_id: string) => void;
}

export function TakeoverConfirmDialog({
  slot,
  open,
  pending,
  error_message,
  return_focus_element,
  on_close,
  on_confirm,
}: TakeoverConfirmDialogProps) {
  const dialogRef = useRef<HTMLElement | null>(null);
  useSurfaceLayer({
    open,
    kind: "modal",
    priority: 45,
    container: dialogRef.current,
    return_focus_element: return_focus_element ?? null,
    on_close,
  });

  if (!open || !slot) {
    return null;
  }

  return (
    <div className="session-dialog-backdrop" role="presentation" onClick={on_close}>
      <section ref={dialogRef} className="session-dialog" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
        <div className="v1-panel-head">
          <h2>Confirm Takeover</h2>
        </div>
        <p>
          Take over <strong>{slot.display_name}</strong> ({slot.slot_id.toUpperCase()})?
        </p>
        <p className="status-muted">
          This uses the existing backend takeover flow. If you already hold another claim, the backend will switch it.
        </p>
        {error_message ? <div className="session-feedback error">{error_message}</div> : null}
        <div className="session-dialog-actions">
          <button type="button" onClick={() => on_confirm(slot.slot_id)} disabled={pending}>
            {pending ? "Taking over..." : "Confirm takeover"}
          </button>
          <button type="button" onClick={on_close} disabled={pending}>
            Cancel
          </button>
        </div>
      </section>
    </div>
  );
}
