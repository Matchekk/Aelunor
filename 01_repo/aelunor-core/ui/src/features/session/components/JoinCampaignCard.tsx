import { useState } from "react";

import type { JoinCampaignRequest } from "../../../shared/api/contracts";
import { normalizeJoinCode, validateJoinInput } from "../selectors";

interface JoinCampaignCardProps {
  is_pending: boolean;
  error_message: string | null;
  on_submit: (payload: JoinCampaignRequest) => Promise<void>;
}

export function JoinCampaignCard({ is_pending, error_message, on_submit }: JoinCampaignCardProps) {
  const [joinCode, setJoinCode] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  const submit = async () => {
    const normalizedJoinCode = normalizeJoinCode(joinCode);
    const validationError = validateJoinInput(normalizedJoinCode, displayName);
    if (validationError) {
      setLocalError(validationError);
      return;
    }
    setLocalError(null);
    await on_submit({
      join_code: normalizedJoinCode,
      display_name: displayName.trim(),
    });
  };

  return (
    <section className="v1-panel session-card">
      <div className="v1-panel-head">
        <h2>Join Campaign</h2>
      </div>
      <form
        className="session-card-form"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <label>
          Join code / campaign code
          <input
            value={joinCode}
            onChange={(event) => {
              setJoinCode(event.target.value);
              if (localError) {
                setLocalError(null);
              }
            }}
            maxLength={40}
            placeholder="ABC123"
          />
        </label>
        <label>
          Your display name
          <input
            value={displayName}
            onChange={(event) => {
              setDisplayName(event.target.value);
              if (localError) {
                setLocalError(null);
              }
            }}
            maxLength={60}
            placeholder="e.g. Abo"
          />
        </label>
        <button type="submit" disabled={is_pending}>
          {is_pending ? "Joining..." : "Join campaign"}
        </button>
      </form>
      {localError ? <div className="session-feedback error">{localError}</div> : null}
      {error_message ? <div className="session-feedback error">{error_message}</div> : null}
    </section>
  );
}
