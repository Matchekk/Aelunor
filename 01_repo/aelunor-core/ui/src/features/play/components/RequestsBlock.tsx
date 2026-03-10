import type { TurnRequest } from "../../../shared/api/contracts";

interface RequestsBlockProps {
  requests: TurnRequest[];
}

export function RequestsBlock({ requests }: RequestsBlockProps) {
  if (requests.length === 0) {
    return null;
  }

  return (
    <section className="requests-block">
      <div className="v1-panel-head">
        <h2>Active Requests</h2>
        <span>{requests.length}</span>
      </div>
      <div className="requests-list">
        {requests.map((request, index) => (
          <article key={`${request.type}-${request.actor || "actor"}-${index}`} className="requests-item">
            <strong>{request.type === "choice" ? "Choice" : request.type === "clarify" ? "Clarify" : "Request"}</strong>
            <p className="status-muted">{request.question || "The GM expects extra input on the next contribution."}</p>
            {request.options && request.options.length > 0 ? (
              <div className="requests-options">
                {request.options.map((option) => (
                  <span key={option} className="status-pill">
                    {option}
                  </span>
                ))}
              </div>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}
