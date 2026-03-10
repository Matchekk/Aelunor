import type { ScopeLabelDescriptor } from "../../scenes/scopeLabels";
import { ScopeLabel } from "../../scenes/components/ScopeLabel";

interface ContextMetaBarProps {
  actor_label: string;
  status: string;
  intent: string;
  confidence: string;
  source_kinds: string[];
  scope_labels: ScopeLabelDescriptor[];
}

export function ContextMetaBar({ actor_label, status, intent, confidence, source_kinds, scope_labels }: ContextMetaBarProps) {
  return (
    <div className="context-meta-bar">
      <span className="status-pill">{actor_label}</span>
      <span className="status-pill">{status || "result"}</span>
      <span className="status-pill">{intent || "unknown"}</span>
      <span className="status-pill">{confidence || "low"} confidence</span>
      {source_kinds.map((kind) => (
        <span key={kind} className="status-pill">
          {kind}
        </span>
      ))}
      {scope_labels.map((scope) => (
        <ScopeLabel key={scope.key} scope={scope} />
      ))}
    </div>
  );
}
