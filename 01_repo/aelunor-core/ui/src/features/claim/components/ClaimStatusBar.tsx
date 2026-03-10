import type { ClaimGateState } from "../selectors";

interface ClaimStatusBarProps {
  gate: ClaimGateState;
  ready_summary: string;
  message: string;
  mutation_error: string | null;
  blocking_hint: string | null;
  has_slots: boolean;
}

export function ClaimStatusBar({
  gate,
  ready_summary,
  message,
  mutation_error,
  blocking_hint,
  has_slots,
}: ClaimStatusBarProps) {
  return (
    <section className="v1-panel claim-status-bar">
      <div className="claim-status-pills">
        <span className="status-pill">{gate.phase_display}</span>
        <span className="status-pill">{ready_summary}</span>
        {gate.current_slot_id ? <span className="status-pill">Claimed {gate.current_slot_id}</span> : null}
      </div>
      <p className="status-muted">{message}</p>
      {!has_slots ? <div className="session-feedback error">No slots are currently available for this campaign.</div> : null}
      {blocking_hint ? <div className="session-feedback error">{blocking_hint}</div> : null}
      {mutation_error ? <div className="session-feedback error">{mutation_error}</div> : null}
    </section>
  );
}
