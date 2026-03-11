import { useUserSettingsStore } from "../../../entities/settings/store";

interface WaitingMotifProps {
  stage: 0 | 1 | 2 | 3;
  size?: "sm" | "md" | "lg";
}

function deriveMotifKind(theme: string): "hybrid" | "glade" | "arcane" {
  if (theme === "hybrid") {
    return "hybrid";
  }
  if (theme === "glade") {
    return "glade";
  }
  return "arcane";
}

export function WaitingMotif({ stage, size = "md" }: WaitingMotifProps) {
  const theme = useUserSettingsStore((state) => state.appearance.theme);
  const motif = deriveMotifKind(theme);

  if (motif === "hybrid") {
    return (
      <span className={`waiting-motif waiting-motif-${size} waiting-motif-hybrid stage-${stage}`} aria-hidden="true">
        <span className="motif-flame-core" />
        <span className="motif-flame-halo" />
      </span>
    );
  }

  if (motif === "glade") {
    return (
      <span className={`waiting-motif waiting-motif-${size} waiting-motif-glade stage-${stage}`} aria-hidden="true">
        <span className="motif-leaf motif-leaf-a" />
        <span className="motif-leaf motif-leaf-b" />
        <span className="motif-leaf motif-leaf-c" />
      </span>
    );
  }

  return (
    <span className={`waiting-motif waiting-motif-${size} waiting-motif-arcane stage-${stage}`} aria-hidden="true">
      <span className="motif-ring motif-ring-a" />
      <span className="motif-ring motif-ring-b" />
      <span className="motif-core" />
    </span>
  );
}
