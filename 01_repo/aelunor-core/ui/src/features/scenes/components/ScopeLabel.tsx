import type { ScopeLabelDescriptor } from "../scopeLabels";

interface ScopeLabelProps {
  scope: ScopeLabelDescriptor;
}

export function ScopeLabel({ scope }: ScopeLabelProps) {
  return <span className={`scope-label scope-${scope.kind}`}>{scope.label}</span>;
}
