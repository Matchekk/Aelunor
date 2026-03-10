import { usePresenceStore } from "../../../entities/presence/store";
import { deriveSlotPresenceLabel } from "../selectors";

interface SlotPresenceChipProps {
  slot_id: string;
  owner_player_id: string | null;
}

export function SlotPresenceChip({ slot_id, owner_player_id }: SlotPresenceChipProps) {
  const label = usePresenceStore((state) => deriveSlotPresenceLabel(slot_id, owner_player_id, state.activities));

  if (!label) {
    return <span className="status-pill claim-presence-chip idle">Idle</span>;
  }

  return <span className="status-pill claim-presence-chip">{label}</span>;
}
