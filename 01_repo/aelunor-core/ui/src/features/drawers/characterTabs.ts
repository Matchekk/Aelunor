export const CHARACTER_DRAWER_TABS = [
  { id: "overview", label: "Übersicht" },
  { id: "class", label: "Klasse" },
  { id: "attributes", label: "Attribute" },
  { id: "skills", label: "Skills" },
  { id: "injuries", label: "Verletzungen" },
  { id: "gear", label: "Ausrüstung" },
] as const;

export type CharacterDrawerTabId = (typeof CHARACTER_DRAWER_TABS)[number]["id"];
