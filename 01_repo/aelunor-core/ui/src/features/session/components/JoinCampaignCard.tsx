import { useEffect, useState } from "react";

import type { JoinCampaignRequest } from "../../../shared/api/contracts";
import { WaitingInline, WaitingSurface } from "../../../shared/waiting/components";
import { normalizeJoinCode, validateJoinInput } from "../selectors";

interface JoinCampaignCardProps {
  is_pending: boolean;
  error_message: string | null;
  default_display_name?: string | null;
  on_submit: (payload: JoinCampaignRequest) => Promise<void>;
}

export function JoinCampaignCard({ is_pending, error_message, default_display_name = null, on_submit }: JoinCampaignCardProps) {
  const [joinCode, setJoinCode] = useState("");
  const [displayName, setDisplayName] = useState(default_display_name ?? "");
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    if (!displayName.trim() && default_display_name) {
      setDisplayName(default_display_name);
    }
  }, [default_display_name, displayName]);

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
    <section className="v1-panel session-card hub-action-card aelunor-frame-host">
      <span className="aelunor-frame-overlay is-card" aria-hidden="true" />
      <WaitingSurface target="hub_join" />
      <div className="v1-panel-head">
        <h2>Kampagne beitreten</h2>
        <span>Code eingeben</span>
      </div>
      <span className="aelunor-divider is-small" aria-hidden="true" />
      <WaitingInline target="hub_join" className="hub-waiting-inline" />
      <p className="status-muted">Schneller Einstieg in einen bestehenden Raum über Join-Code.</p>
      <form
        className="session-card-form"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <label>
          <span>Join-Code / Kampagnen-Code</span>
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
          <span>Dein Name</span>
          <input
            value={displayName}
            onChange={(event) => {
              setDisplayName(event.target.value);
              if (localError) {
                setLocalError(null);
              }
            }}
            maxLength={60}
            placeholder="z.B. Abo"
          />
        </label>
        <button type="submit" className="hub-primary-cta aelunor-button-ornate" disabled={is_pending}>
          {is_pending ? "Trete bei..." : "Kampagne beitreten"}
        </button>
      </form>
      {localError ? <div className="session-feedback error">{localError}</div> : null}
      {error_message ? <div className="session-feedback error">{error_message}</div> : null}
    </section>
  );
}
