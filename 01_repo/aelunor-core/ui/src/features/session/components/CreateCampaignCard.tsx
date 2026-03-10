import { useEffect, useState } from "react";

import type { CreateCampaignRequest } from "../../../shared/api/contracts";

interface CreateCampaignCardProps {
  is_pending: boolean;
  error_message: string | null;
  default_display_name?: string | null;
  on_submit: (payload: CreateCampaignRequest) => Promise<void>;
}

export function CreateCampaignCard({ is_pending, error_message, default_display_name = null, on_submit }: CreateCampaignCardProps) {
  const [title, setTitle] = useState("New Aelunor Campaign");
  const [displayName, setDisplayName] = useState(default_display_name ?? "");
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    if (!displayName.trim() && default_display_name) {
      setDisplayName(default_display_name);
    }
  }, [default_display_name, displayName]);

  const submit = async () => {
    const normalizedDisplayName = displayName.trim();
    if (!normalizedDisplayName) {
      setLocalError("Display name is required.");
      return;
    }
    setLocalError(null);
    await on_submit({
      title: title.trim() || "New Aelunor Campaign",
      display_name: normalizedDisplayName,
    });
  };

  return (
    <section className="v1-panel session-card hub-action-card">
      <div className="v1-panel-head">
        <h2>Create Campaign</h2>
        <span>Neue Runde starten</span>
      </div>
      <p className="status-muted">Du wirst Host und landest direkt im passenden Kampagnen-Flow.</p>
      <form
        className="session-card-form"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <label>
          Campaign title
          <input
            value={title}
            onChange={(event) => {
              setTitle(event.target.value);
            }}
            maxLength={120}
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
            placeholder="e.g. Matchek"
          />
        </label>
        <button type="submit" className="hub-secondary-cta" disabled={is_pending}>
          {is_pending ? "Creating..." : "Create campaign"}
        </button>
      </form>
      {localError ? <div className="session-feedback error">{localError}</div> : null}
      {error_message ? <div className="session-feedback error">{error_message}</div> : null}
    </section>
  );
}
