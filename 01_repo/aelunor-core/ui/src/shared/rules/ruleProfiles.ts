export type RuleProfileId = "cinematic_ai" | "simple_d6" | "d20_fantasy" | "five_e_inspired" | "custom";

export type ResolutionMode = "ai_judgement" | "dice_check" | "hybrid";

export type DiceFormula = "1d6" | "1d20";

export interface RuleProfileDefinition {
  id: RuleProfileId;
  label: string;
  short_label: string;
  description: string;
  resolution_mode: ResolutionMode;
  dice_formula: DiceFormula | null;
  player_visible_rolls: boolean;
  recommended_for: string[];
  setup_hint: string;
  mvp_ready: boolean;
}

export interface RuleProfileRuntimeState {
  profile_id: RuleProfileId;
  resolution_mode: ResolutionMode;
  dice_formula: DiceFormula | null;
  player_visible_rolls: boolean;
  custom_label?: string;
}

export const RULE_PROFILE_DEFINITIONS: readonly RuleProfileDefinition[] = [
  {
    id: "cinematic_ai",
    label: "Cinematic AI",
    short_label: "KI entscheidet",
    description:
      "Keine sichtbaren Würfel. Erfolg, Teilerfolg oder Fehlschlag werden anhand von Szene, Risiko, Vorbereitung, Charakterzustand und Dramaturgie entschieden.",
    resolution_mode: "ai_judgement",
    dice_formula: null,
    player_visible_rolls: false,
    recommended_for: ["Story-first", "Solo", "schneller Einstieg"],
    setup_hint: "Gut, wenn die Kampagne wie ein erzählerisches RPG laufen soll und Regeln im Hintergrund bleiben dürfen.",
    mvp_ready: true,
  },
  {
    id: "simple_d6",
    label: "Simple d6",
    short_label: "W6-System",
    description:
      "Ein einfacher W6 entscheidet riskante Aktionen. Schnell, verständlich und deutlich leichter als klassische Pen-&-Paper-Regelwerke.",
    resolution_mode: "dice_check",
    dice_formula: "1d6",
    player_visible_rolls: true,
    recommended_for: ["Casual", "schnelle Runden", "leichte Regeln"],
    setup_hint: "Gut, wenn Spieler klare Zufallsentscheidungen wollen, aber keine komplexen Regeln.",
    mvp_ready: true,
  },
  {
    id: "d20_fantasy",
    label: "d20 Fantasy",
    short_label: "W20-System",
    description:
      "Ein W20 entscheidet Checks gegen Schwierigkeitswerte. Das erzeugt klassisches Fantasy-RPG-Gefühl ohne vollständige 5e-Komplexität.",
    resolution_mode: "dice_check",
    dice_formula: "1d20",
    player_visible_rolls: true,
    recommended_for: ["Fantasy-RPG", "TTRPG-Gefühl", "sichtbare Checks"],
    setup_hint: "Gut, wenn Aelunor sich würfelbasiert anfühlen soll, ohne direkt ein volles 5e-System zu erzwingen.",
    mvp_ready: true,
  },
  {
    id: "five_e_inspired",
    label: "5e Inspired",
    short_label: "5e-inspiriert",
    description:
      "Ein späteres, stärker regelgebundenes Profil mit d20-Checks, Attributen, Rettungswürfen, Ressourcen und 5e-ähnlicher Fantasy-Logik.",
    resolution_mode: "hybrid",
    dice_formula: "1d20",
    player_visible_rolls: true,
    recommended_for: ["TTRPG-Veteranen", "regelnahe Kampagnen", "klassische Fantasy"],
    setup_hint: "Nicht als erster MVP-Kern behandeln. Dieses Profil braucht eigene Validierung, Balancing und UI-Erklärungen.",
    mvp_ready: false,
  },
  {
    id: "custom",
    label: "Custom",
    short_label: "Eigenes Profil",
    description:
      "Ein frei konfigurierbares Regelprofil für spätere Poweruser. Im MVP nur als Zielbild vorbereiten, nicht als komplexer Editor bauen.",
    resolution_mode: "hybrid",
    dice_formula: null,
    player_visible_rolls: true,
    recommended_for: ["Poweruser", "Homebrew", "Experimente"],
    setup_hint: "Später sinnvoll, sobald die festen Profile stabil sind.",
    mvp_ready: false,
  },
] as const;

export const DEFAULT_RULE_PROFILE_ID: RuleProfileId = "cinematic_ai";

export function findRuleProfileDefinition(profile_id: string | null | undefined): RuleProfileDefinition {
  return (
    RULE_PROFILE_DEFINITIONS.find((definition) => definition.id === profile_id) ??
    RULE_PROFILE_DEFINITIONS[0]
  );
}

export function buildRuleProfileRuntimeState(profile_id: string | null | undefined): RuleProfileRuntimeState {
  const definition = findRuleProfileDefinition(profile_id);
  return {
    profile_id: definition.id,
    resolution_mode: definition.resolution_mode,
    dice_formula: definition.dice_formula,
    player_visible_rolls: definition.player_visible_rolls,
  };
}

export function describeRuleProfileForSetup(profile_id: string | null | undefined): string {
  const definition = findRuleProfileDefinition(profile_id);
  const dicePart = definition.dice_formula ? `Würfel: ${definition.dice_formula}.` : "Keine sichtbaren Würfel.";
  return `${definition.label}: ${definition.description} ${dicePart}`;
}

export function listMvpRuleProfiles(): RuleProfileDefinition[] {
  return RULE_PROFILE_DEFINITIONS.filter((definition) => definition.mvp_ready);
}
