import { useEffect, useState } from "react";

import type { StoryCardCreateRequest, StoryCardEntry } from "../../../shared/api/contracts";

interface StoryCardEditorProps {
  editing_card: StoryCardEntry | null;
  pending: boolean;
  error_message: string | null;
  on_submit: (payload: StoryCardCreateRequest) => void;
  on_cancel: () => void;
}

const STORY_CARD_KINDS: StoryCardEntry["kind"][] = ["npc", "location", "faction", "item", "hook", "rule"];

export function StoryCardEditor({
  editing_card,
  pending,
  error_message,
  on_submit,
  on_cancel,
}: StoryCardEditorProps) {
  const [title, setTitle] = useState("");
  const [kind, setKind] = useState<StoryCardEntry["kind"]>("npc");
  const [content, setContent] = useState("");
  const [tags, setTags] = useState("");

  useEffect(() => {
    setTitle(editing_card?.title ?? "");
    setKind(editing_card?.kind ?? "npc");
    setContent(editing_card?.content ?? "");
    setTags((editing_card?.tags ?? []).join(", "));
  }, [editing_card]);

  return (
    <section className="boards-editor">
      <div className="v1-panel-head">
        <h2>{editing_card ? "Edit story card" : "New story card"}</h2>
        {editing_card ? <button type="button" onClick={on_cancel}>Cancel</button> : null}
      </div>
      <label>
        Title
        <input value={title} onChange={(event) => setTitle(event.target.value)} />
      </label>
      <label>
        Kind
        <select value={kind} onChange={(event) => setKind(event.target.value as StoryCardEntry["kind"])}>
          {STORY_CARD_KINDS.map((entry) => (
            <option key={entry} value={entry}>
              {entry}
            </option>
          ))}
        </select>
      </label>
      <label>
        Content
        <textarea value={content} onChange={(event) => setContent(event.target.value)} />
      </label>
      <label>
        Tags
        <input value={tags} onChange={(event) => setTags(event.target.value)} placeholder="comma, separated, tags" />
      </label>
      {error_message ? <div className="session-feedback error">{error_message}</div> : null}
      <div className="session-inline-actions">
        <button
          type="button"
          disabled={pending}
          onClick={() =>
            on_submit({
              title: title.trim(),
              kind,
              content: content.trim(),
              tags: tags
                .split(",")
                .map((tag) => tag.trim())
                .filter(Boolean),
            })
          }
        >
          {pending ? "Saving..." : editing_card ? "Save story card" : "Create story card"}
        </button>
      </div>
    </section>
  );
}
