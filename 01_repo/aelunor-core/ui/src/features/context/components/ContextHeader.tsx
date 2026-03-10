interface ContextHeaderProps {
  title: string;
  question: string;
  on_close: () => void;
}

export function ContextHeader({ title, question, on_close }: ContextHeaderProps) {
  return (
    <header className="context-modal-header">
      <div>
        <div className="v1-topbar-kicker">Context Query</div>
        <h1>{title}</h1>
        <p className="status-muted">{question ? `Question: ${question}` : "Read-only canon lookup"}</p>
      </div>
      <div className="session-inline-actions">
        <button type="button" onClick={on_close}>
          Close
        </button>
      </div>
    </header>
  );
}
