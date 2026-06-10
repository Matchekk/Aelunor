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
          <h2>Sitzung bearbeiten</h2>
        </div>
        <label>
          Bezeichnung
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
        {props.entry.campaign_title ? (
          <div className="session-dialog-meta status-muted">Kampagne: {props.entry.campaign_title}</div>
        ) : null}
        {localError ? <div className="session-feedback error">{localError}</div> : null}
        <div className="session-dialog-actions">
          <button
            type="button"
            onClick={() => {
              if (!label.trim()) {
                setLocalError("Bitte eine Bezeichnung eingeben.");
                return;
              }
              props.on_rename(campaign_id, label);
            }}
          >
            Bezeichnung speichern
          </button>
          <button type="button" onClick={() => props.on_export(campaign_id)}>
            JSON exportieren
          </button>
          <button type="button" onClick={() => props.on_delete(campaign_id)}>
            Lokalen Eintrag entfernen
          </button>
          <button type="button" onClick={props.on_close}>
            Schließen
          </button>
        </div>
      </section>
    </div>
  );
}
