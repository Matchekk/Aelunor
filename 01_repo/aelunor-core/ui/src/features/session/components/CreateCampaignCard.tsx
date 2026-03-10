import { useState } from "react";

import type { CreateCampaignRequest } from "../../../shared/api/contracts";

interface CreateCampaignCardProps {
  is_pending: boolean;
  error_message: string | null;
  on_submit: (payload: CreateCampaignRequest) => Promise<void>;
}

export function CreateCampaignCard({ is_pending, error_message, on_submit }: CreateCampaignCardProps) {
  const [title, setTitle] = useState("New Aelunor Campaign");
  const [displayName, setDisplayName] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

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
    <section className="v1-panel session-card">
      <div className="v1-panel-head">
        <h2>Create Campaign</h2>
      </div>
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
        <button type="submit" disabled={is_pending}>
          {is_pending ? "Creating..." : "Create campaign"}
        </button>
      </form>
      {localError ? <div className="session-feedback error">{localError}</div> : null}
      {error_message ? <div className="session-feedback error">{error_message}</div> : null}
    </section>
  );
}
