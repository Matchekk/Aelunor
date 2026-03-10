import { useEffect, useState } from "react";

import type { WorldInfoCreateRequest, WorldInfoEntry } from "../../../shared/api/contracts";

interface WorldInfoEditorProps {
  editing_entry: WorldInfoEntry | null;
  pending: boolean;
  error_message: string | null;
  on_submit: (payload: WorldInfoCreateRequest) => void;
  on_cancel: () => void;
}

export function WorldInfoEditor({
  editing_entry,
  pending,
  error_message,
  on_submit,
  on_cancel,
}: WorldInfoEditorProps) {
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("");
  const [content, setContent] = useState("");
  const [tags, setTags] = useState("");

  useEffect(() => {
    setTitle(editing_entry?.title ?? "");
    setCategory(editing_entry?.category ?? "");
    setContent(editing_entry?.content ?? "");
    setTags((editing_entry?.tags ?? []).join(", "));
  }, [editing_entry]);

  return (
    <section className="boards-editor">
      <div className="v1-panel-head">
        <h2>{editing_entry ? "Edit world info" : "New world info"}</h2>
        {editing_entry ? <button type="button" onClick={on_cancel}>Cancel</button> : null}
      </div>
      <label>
        Title
        <input value={title} onChange={(event) => setTitle(event.target.value)} />
      </label>
      <label>
        Category
        <input value={category} onChange={(event) => setCategory(event.target.value)} />
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
              category: category.trim(),
              content: content.trim(),
              tags: tags
                .split(",")
                .map((tag) => tag.trim())
                .filter(Boolean),
            })
          }
        >
          {pending ? "Saving..." : editing_entry ? "Save world info" : "Create world info"}
        </button>
      </div>
    </section>
  );
}
