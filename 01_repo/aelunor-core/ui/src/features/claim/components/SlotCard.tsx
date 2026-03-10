import type { ClaimSlotViewModel } from "../selectors";
import { SlotPresenceChip } from "./SlotPresenceChip";

interface SlotCardProps {
  slot: ClaimSlotViewModel;
  disabled: boolean;
  pending_action: "claim" | "takeover" | "unclaim" | null;
  on_claim: (slot_id: string) => void;
  on_takeover: (slot: ClaimSlotViewModel) => void;
  on_unclaim: (slot_id: string) => void;
}

export function SlotCard({ slot, disabled, pending_action, on_claim, on_takeover, on_unclaim }: SlotCardProps) {
  return (
    <article className={`claim-slot-card${slot.is_mine ? " is-self" : ""}${slot.is_free ? " is-free" : ""}`}>
      <div className="claim-slot-card-head">
        <div>
          <h3>{slot.display_name}</h3>
          <div className="status-muted">{slot.slot_id.toUpperCase()}</div>
        </div>
        <SlotPresenceChip slot_id={slot.slot_id} owner_player_id={slot.claimed_by} />
      </div>
      <div className="claim-slot-status">
        <span className="status-pill">{slot.status_label}</span>
      </div>
      <p className="claim-slot-summary">{slot.summary}</p>
      <p className="status-muted">{slot.readiness_label}</p>
      <div className="claim-slot-actions">
        {slot.can_claim ? (
          <button type="button" onClick={() => on_claim(slot.slot_id)} disabled={disabled}>
            {pending_action === "claim" ? "Claiming..." : "Claim"}
          </button>
        ) : null}
        {slot.can_take_over ? (
          <button type="button" onClick={() => on_takeover(slot)} disabled={disabled}>
            {pending_action === "takeover" ? "Taking over..." : "Take over"}
          </button>
        ) : null}
        {slot.can_unclaim ? (
          <button type="button" onClick={() => on_unclaim(slot.slot_id)} disabled={disabled}>
            {pending_action === "unclaim" ? "Releasing..." : "Unclaim"}
          </button>
        ) : null}
        {!slot.can_claim && !slot.can_take_over && !slot.can_unclaim ? (
          <button type="button" disabled>
            Unavailable
          </button>
        ) : null}
      </div>
    </article>
  );
}
