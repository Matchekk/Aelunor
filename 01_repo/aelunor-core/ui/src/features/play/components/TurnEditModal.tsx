import { useEffect, useRef, useState } from "react";

import { derivePresenceKindForContext, usePresenceActivityHeartbeat } from "../../../entities/presence/activity";
import { useSurfaceLayer } from "../../../shared/ui/useSurfaceLayer";

interface TurnEditDraft {
  turn_id: string;
  turn_number: number | null;
  actor_display: string;
  input_text_display: string;
  gm_text_display: string;
  slot_id: string | null;
}

interface TurnEditModalProps {
  campaign_id: string;
  open: boolean;
  turn: TurnEditDraft | null;
  pending: boolean;
  error_message: string | null;
  return_focus_element: HTMLElement | null;
  on_close: () => void;
  on_save: (payload: { turn_id: string; input_text_display: string; gm_text_display: string }) => void;
}

export function TurnEditModal({
  campaign_id,
  open,
  turn,
  pending,
  error_message,
  return_focus_element,
  on_close,
  on_save,
}: TurnEditModalProps) {
  const dialogRef = useRef<HTMLElement | null>(null);
  const [inputText, setInputText] = useState("");
  const [gmText, setGmText] = useState("");

  useSurfaceLayer({
    open,
    kind: "modal",
    priority: 46,
    container: dialogRef.current,
    return_focus_element,
    on_close,
  });

  usePresenceActivityHeartbeat({
    active: open && Boolean(turn),
    campaign_id,
    kind: derivePresenceKindForContext("turn_edit"),
    slot_id: turn?.slot_id ?? null,
    target_turn_id: turn?.turn_id ?? null,
  });

  useEffect(() => {
    if (!open || !turn) {
      return;
    }
    setInputText(turn.input_text_display ?? "");
    setGmText(turn.gm_text_display ?? "");
  }, [open, turn]);

  if (!open || !turn) {
    return null;
  }

  return (
    <div className="context-modal-backdrop turn-edit-modal-backdrop" role="presentation" onClick={on_close}>
      <section
        ref={dialogRef}
        className="context-modal turn-edit-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Turn bearbeiten"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="context-modal-header">
          <div>
            <div className="v1-topbar-kicker">Turn-Editor</div>
            <h1>
              Zug {turn.turn_number ?? "?"} • {turn.actor_display}
            </h1>
            <p className="status-muted">
              Passe Spielerbeitrag und GM-Antwort an. Änderungen wirken direkt auf den aktiven Kampagnenverlauf.
            </p>
          </div>
          <button type="button" onClick={on_close} disabled={pending}>
            Schließen
          </button>
        </header>

        <div className="turn-edit-grid">
          <label className="setup-field">
            <span>Spielerbeitrag</span>
            <textarea
              value={inputText}
              onChange={(event) => {
                setInputText(event.target.value);
              }}
              disabled={pending}
            />
          </label>
          <label className="setup-field">
            <span>GM-Antwort</span>
            <textarea
              value={gmText}
              onChange={(event) => {
                setGmText(event.target.value);
              }}
              disabled={pending}
            />
          </label>
        </div>

        {error_message ? <div className="session-feedback error">{error_message}</div> : null}

        <div className="session-inline-actions">
          <button type="button" onClick={on_close} disabled={pending}>
            Abbrechen
          </button>
          <button
            type="button"
            onClick={() => {
              on_save({
                turn_id: turn.turn_id,
                input_text_display: inputText,
                gm_text_display: gmText,
              });
            }}
            disabled={pending}
          >
            {pending ? "Speichere..." : "Änderungen speichern"}
          </button>
        </div>
      </section>
    </div>
  );
}
