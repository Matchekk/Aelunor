import { useState } from "react";

import type { StoryCardCreateRequest, StoryCardEntry } from "../../../shared/api/contracts";
import { deriveStoryCardSubtitle, formatBoardTimestamp } from "../selectors";
import { StoryCardEditor } from "./StoryCardEditor";

interface StoryCardsPanelProps {
  cards: StoryCardEntry[];
  can_edit: boolean;
  create_pending: boolean;
  patch_pending: boolean;
  error_message: string | null;
  on_create: (payload: StoryCardCreateRequest) => void;
  on_patch: (card_id: string, payload: StoryCardCreateRequest) => void;
}

export function StoryCardsPanel({
  cards,
  can_edit,
  create_pending,
  patch_pending,
  error_message,
  on_create,
  on_patch,
}: StoryCardsPanelProps) {
  const [editing_card_id, setEditingCardId] = useState<string | null>(null);
  const editing_card = cards.find((card) => card.card_id === editing_card_id) ?? null;

  return (
    <section className="boards-panel">
      <div className="v1-panel-head">
        <h2>Story Cards</h2>
        <span>{can_edit ? "Host editable" : "Read-only"}</span>
      </div>
      <p className="status-muted">
        Create and refine high-level story anchors. Delete is still deferred because the current backend flow only
        exposes create and patch operations here.
      </p>
      {can_edit ? (
        <StoryCardEditor
          editing_card={editing_card}
          pending={create_pending || patch_pending}
          error_message={error_message}
          on_cancel={() => setEditingCardId(null)}
          on_submit={(payload) => {
            if (editing_card) {
              on_patch(editing_card.card_id, payload);
              return;
            }
            on_create(payload);
          }}
        />
      ) : null}
      <div className="boards-list">
        {cards.length > 0 ? (
          cards.map((card) => (
            <article key={card.card_id} className="boards-list-item">
              <div className="v1-panel-head">
                <h2>{card.title}</h2>
                <span>{formatBoardTimestamp(card.updated_at)}</span>
              </div>
              <div className="status-muted">{deriveStoryCardSubtitle(card)}</div>
              <p>{card.content}</p>
              {can_edit ? (
                <div className="session-inline-actions">
                  <button type="button" onClick={() => setEditingCardId(card.card_id)}>
                    Edit
                  </button>
                </div>
              ) : null}
            </article>
          ))
        ) : (
          <div className="setup-empty-state">No story cards have been created yet.</div>
        )}
      </div>
    </section>
  );
}
