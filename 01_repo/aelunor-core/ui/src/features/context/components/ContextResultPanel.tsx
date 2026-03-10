import type { ContextQueryResponse } from "../../../shared/api/contracts";

interface ContextResultPanelProps {
  payload: ContextQueryResponse;
}

export function ContextResultPanel({ payload }: ContextResultPanelProps) {
  const facts = payload.result.facts ?? [];
  const sources = payload.result.sources ?? [];
  const suggestions = payload.result.suggestions ?? [];

  return (
    <section className="context-result-panel">
      <article className="context-result-block">
        <strong>Answer</strong>
        <p>{payload.answer}</p>
        {payload.result.explanation ? <p className="status-muted">{payload.result.explanation}</p> : null}
      </article>

      {facts.length > 0 ? (
        <article className="context-result-block">
          <strong>Facts</strong>
          <ul className="requests-list">
            {facts.map((fact) => (
              <li key={fact} className="requests-item">
                {fact}
              </li>
            ))}
          </ul>
        </article>
      ) : null}

      {sources.length > 0 ? (
        <article className="context-result-block">
          <strong>Sources</strong>
          <ul className="requests-list">
            {sources.map((source) => (
              <li key={`${source.type}:${source.id}`} className="requests-item">
                <span>{source.label}</span>
                <span className="status-muted">
                  {source.type} • {source.id}
                </span>
              </li>
            ))}
          </ul>
        </article>
      ) : null}

      {suggestions.length > 0 ? (
        <article className="context-result-block">
          <strong>Suggestions</strong>
          <div className="composer-status-pills">
            {suggestions.map((suggestion) => (
              <span key={suggestion} className="status-pill">
                {suggestion}
              </span>
            ))}
          </div>
        </article>
      ) : null}
    </section>
  );
}
