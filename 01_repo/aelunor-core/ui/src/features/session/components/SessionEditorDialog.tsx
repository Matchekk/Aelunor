import { useEffect, useRef, useState } from "react";

import type { SessionLibraryEntry } from "../../../shared/api/contracts";
import { useSurfaceLayer } from "../../../shared/ui/useSurfaceLayer";

interface SessionEditorDialogProps {
  entry: SessionLibraryEntry | null;
  open: boolean;
  return_focus_element?: HTMLElement | null;
  on_close: () => void;
  on_rename: (campaign_id: string, label: string) => void;
  on_export: (campaign_id: string) => void;
  on_delete: (campaign_id: string) => void;
}

export function SessionEditorDialog(props: SessionEditorDialogProps) {
  const dialogRef = useRef<HTMLElement | null>(null);
  const [label, setLabel] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  useSurfaceLayer({
    open: props.open,
    kind: "modal",
    priority: 45,
    container: dialogRef.current,
    return_focus_element: props.return_focus_element ?? null,
    on_close: props.on_close,
  });

  useEffect(() => {
    setLabel(props.entry?.label ?? "");
    setLocalError(null);
  }, [props.entry]);

  if (!props.open || !props.entry) {
    return null;
  }

  const campaign_id = props.entry.campaign_id;

  return (
    <div className="session-dialog-backdrop" role="presentation" onClick={props.on_close}>
      <section ref={dialogRef} className="session-dialog" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
        <div className="v1-panel-head">
          <h2>Session Editor</h2>
        </div>
        <label>
          Local label
          <input
            value={label}
            onChange={(event) => {
              setLabel(event.target.value);
              if (localError) {
                setLocalError(null);
              }
            }}
            maxLength={120}
          />
        </label>
        <div className="session-dialog-meta status-muted">campaign_id: {props.entry.campaign_id}</div>
        {props.entry.campaign_title ? (
          <div className="session-dialog-meta status-muted">campaign_title: {props.entry.campaign_title}</div>
        ) : null}
        {localError ? <div className="session-feedback error">{localError}</div> : null}
        <div className="session-dialog-actions">
          <button
            type="button"
            onClick={() => {
              if (!label.trim()) {
                setLocalError("Local label is required.");
                return;
              }
              props.on_rename(campaign_id, label);
            }}
          >
            Save label
          </button>
          <button type="button" onClick={() => props.on_export(campaign_id)}>
            Export JSON
          </button>
          <button type="button" onClick={() => props.on_delete(campaign_id)}>
            Delete local entry
          </button>
          <button type="button" onClick={props.on_close}>
            Close
          </button>
        </div>
      </section>
    </div>
  );
}
