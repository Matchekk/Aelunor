import { useEffect, useMemo, useState, type ReactNode } from "react";

import type { CharacterSheetResponse, CharacterSkillSnapshot } from "../../../shared/api/contracts";
import { CHARACTER_DRAWER_TABS } from "../characterTabs";
import "../styles/legacyCharacterSheet.css";

interface CharacterDrawerProps {
  sheet: CharacterSheetResponse;
  active_tab: string;
  on_tab_change: (tab_id: string) => void;
}

interface AttributeScaleMeta {
  label: string;
  min: number;
  max: number;
}

interface ResourcePair {
  current: number;
  max: number;
}

const AGE_STAGE_LABELS: Record<string, string> = {
  teen: "Jugendlich",
  young: "Jung",
  adult: "Erwachsen",
  older: "Älter",
};

const BUILD_LABELS: Record<string, string> = {
  frail: "Schmächtig",
  lean: "Drahtig",
  neutral: "Ausgeglichen",
  robust: "Robust",
  broad: "Breit gebaut",
};

const AURA_LABELS: Record<string, string> = {
  none: "Keine",
  faint: "Schwach",
  grim: "Düster",
  dark: "Dunkel",
  ominous: "Unheilvoll",
  abyssal: "Abgründig",
};

const ENCUMBRANCE_LABELS: Record<string, string> = {
  normal: "Normal",
  burdened: "Belastet",
  overloaded: "Überladen",
};

const ATTRIBUTE_CHART_ORDER = ["str", "dex", "con", "int", "wis", "cha", "luck"] as const;

function readRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function readArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function readFiniteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function readString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  if (typeof value === "boolean") {
    return value ? "Ja" : "Nein";
  }
  return String(value);
}

function joinList(values: unknown[]): string {
  const list = values
    .map((value) => String(value ?? "").trim())
    .filter((value) => value.length > 0);
  return list.length > 0 ? list.join(", ") : "-";
}

function titleizeToken(value: unknown): string {
  const token = String(value ?? "").toLowerCase();
  const map: Record<string, string> = {
    str: "Stärke (STR)",
    dex: "Geschicklichkeit (DEX)",
    con: "Konstitution (CON)",
    int: "Intelligenz (INT)",
    wis: "Weisheit (WIS)",
    cha: "Charisma (CHA)",
    luck: "Glück (LUCK)",
    hp: "HP",
    stamina: "Ausdauer",
    aether: "Ressource",
    stress: "Stress",
    corruption: "Verderbnis",
    physical: "Physisch",
    fire: "Feuer",
    cold: "Kälte",
    lightning: "Blitz",
    poison: "Gift",
    bleed: "Blutung",
    shadow: "Schatten",
    holy: "Heilig",
    curse: "Fluch",
    fear: "Furcht",
    weapon: "Waffe",
    offhand: "Nebenhand",
    head: "Kopf",
    chest: "Brust",
    gloves: "Handschuhe",
    boots: "Stiefel",
    amulet: "Amulett",
    ring_1: "Ring 1",
    ring_2: "Ring 2",
    trinket: "Talisman",
    stealth: "Heimlichkeit",
    perception: "Wahrnehmung",
    survival: "Überleben",
    athletics: "Athletik",
    intimidation: "Einschüchtern",
    persuasion: "Überzeugen",
    lore_occult: "Okkultes Wissen",
    crafting: "Handwerk",
    lockpicking: "Schlösser knacken",
    endurance: "Ausdauer",
    willpower: "Willenskraft",
    tactics: "Taktik",
  };
  if (map[token]) {
    return map[token];
  }
  return String(value ?? "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (match: string) => match.toUpperCase());
}

function ageStageLabel(value: unknown): string {
  const token = String(value ?? "").toLowerCase();
  return AGE_STAGE_LABELS[token] || displayValue(value);
}

function buildLabel(value: unknown): string {
  const token = String(value ?? "").toLowerCase();
  return BUILD_LABELS[token] || displayValue(value);
}

function auraLabel(value: unknown): string {
  const token = String(value ?? "").toLowerCase();
  return AURA_LABELS[token] || displayValue(value);
}

function encumbranceLabel(value: unknown): string {
  const token = String(value ?? "").toLowerCase();
  return ENCUMBRANCE_LABELS[token] || displayValue(value);
}

function skillRankClass(rank: unknown): string {
  return `rank-${String(rank || "f").toLowerCase()}`;
}

function formatSkillCost(cost: unknown): string {
  if (typeof cost === "string") {
    return cost || "-";
  }
  const costRecord = readRecord(cost);
  const resource = readString(costRecord.resource);
  const amount = readFiniteNumber(costRecord.amount);
  if (resource) {
    return `${resource} ${amount ?? 0}`;
  }
  return "-";
}

function skillTagSummary(skill: CharacterSkillSnapshot): string {
  return (skill.tags || []).slice(0, 4).join(", ");
}

function attributeScaleMeta(stats: CharacterSheetResponse["sheet"]["stats"]): AttributeScaleMeta {
  const scale = stats.attribute_scale || {};
  const min = Math.max(0, Number(scale.min || 1));
  const max = Math.max(1, Number(scale.max || 10));
  return {
    label: scale.label || `${min || 1}-${max}`,
    min,
    max,
  };
}

function polarPoint(cx: number, cy: number, radius: number, angleRadians: number): { x: number; y: number } {
  return {
    x: cx + Math.cos(angleRadians) * radius,
    y: cy + Math.sin(angleRadians) * radius,
  };
}

function pointsToSvg(points: Array<{ x: number; y: number }>): string {
  return points.map((point) => `${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(" ");
}

function attributeRadarSvgMarkup(
  attributes: Record<string, number> | undefined,
  scaleMeta: AttributeScaleMeta,
  size = 420,
  gradientId = "attributeRadarFill",
): string {
  const cx = size / 2;
  const cy = size / 2;
  const radius = size * 0.28;
  const labelRadius = radius + 44;
  const entries = ATTRIBUTE_CHART_ORDER.map((key, index) => {
    const angle = -Math.PI / 2 + ((Math.PI * 2 * index) / ATTRIBUTE_CHART_ORDER.length);
    const rawValue = Number(attributes?.[key] ?? 0);
    const clamped = Math.max(0, Math.min(scaleMeta.max, rawValue));
    return {
      key,
      label: titleizeToken(key),
      value: rawValue,
      clamped,
      angle,
    };
  });

  const gridLevels = 5;
  const gridPolygons = Array.from({ length: gridLevels }, (_, levelIndex) => {
    const level = (levelIndex + 1) / gridLevels;
    const points = entries.map((entry) => polarPoint(cx, cy, radius * level, entry.angle));
    return `<polygon class="attribute-radar-grid" points="${pointsToSvg(points)}"></polygon>`;
  }).join("");

  const axes = entries
    .map((entry) => {
      const end = polarPoint(cx, cy, radius, entry.angle);
      return `<line class="attribute-radar-axis" x1="${cx}" y1="${cy}" x2="${end.x.toFixed(2)}" y2="${end.y.toFixed(2)}"></line>`;
    })
    .join("");

  const labels = entries
    .map((entry) => {
      const point = polarPoint(cx, cy, labelRadius, entry.angle);
      const anchor = Math.abs(point.x - cx) < 10 ? "middle" : point.x > cx ? "start" : "end";
      return `<text class="attribute-radar-label" x="${point.x.toFixed(2)}" y="${point.y.toFixed(2)}" text-anchor="${anchor}">
      <tspan x="${point.x.toFixed(2)}" dy="0">${entry.label}</tspan>
      <tspan x="${point.x.toFixed(2)}" dy="14">${entry.clamped}/${scaleMeta.max}</tspan>
    </text>`;
    })
    .join("");

  const areaPoints = entries.map((entry) => polarPoint(cx, cy, radius * (entry.clamped / Math.max(scaleMeta.max, 1)), entry.angle));
  const dataArea = `<polygon class="attribute-radar-area" points="${pointsToSvg(areaPoints)}"></polygon>`;
  const valueDots = areaPoints
    .map((point) => `<circle class="attribute-radar-dot" cx="${point.x.toFixed(2)}" cy="${point.y.toFixed(2)}" r="4"></circle>`)
    .join("");

  const tickLabels = Array.from({ length: gridLevels }, (_, levelIndex) => {
    const value = Math.round((scaleMeta.max / gridLevels) * (levelIndex + 1));
    const y = cy - radius * ((levelIndex + 1) / gridLevels);
    return `<text class="attribute-radar-tick" x="${cx + 10}" y="${y.toFixed(2)}">${value}</text>`;
  }).join("");

  return `
    <svg class="attribute-radar-svg" xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" role="img" aria-label="Attributprofil als Septagon">
      <defs>
        <linearGradient id="${gradientId}" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#f4c26c" stop-opacity="0.58"></stop>
          <stop offset="100%" stop-color="#81b1ff" stop-opacity="0.18"></stop>
        </linearGradient>
      </defs>
      ${gridPolygons}
      ${axes}
      <circle class="attribute-radar-core" cx="${cx}" cy="${cy}" r="4"></circle>
      ${tickLabels}
      ${dataArea}
      ${valueDots}
      ${labels}
    </svg>
  `;
}

function bestSkillSummary(skills: CharacterSkillSnapshot[], limit = 3): string[] {
  return [...skills]
    .sort((left, right) => {
      const rightPower = Number(right.effective_progress_multiplier ?? right.level ?? 0);
      const leftPower = Number(left.effective_progress_multiplier ?? left.level ?? 0);
      if (rightPower !== leftPower) {
        return rightPower - leftPower;
      }
      const rightMastery = Number(right.mastery ?? 0);
      const leftMastery = Number(left.mastery ?? 0);
      return rightMastery - leftMastery;
    })
    .slice(0, limit)
    .map((skill) => skill.name || titleizeToken(skill.id || ""))
    .filter(Boolean);
}

function buildAttributeExportSvgMarkup(characterSheet: CharacterSheetResponse): string {
  const stats = characterSheet.sheet.stats;
  const overview = characterSheet.sheet.overview;
  const classCurrent = characterSheet.sheet.class.current ?? overview.class_current ?? null;
  const skills = characterSheet.sheet.skills || [];
  const scale = attributeScaleMeta(stats);
  const width = 900;
  const height = 720;
  const chartSize = 600;
  const chartMarkup = attributeRadarSvgMarkup(stats.attributes || {}, scale, chartSize, "attributeRadarFillExport").replace(
    '<svg class="attribute-radar-svg" xmlns="http://www.w3.org/2000/svg"',
    '<svg class="attribute-radar-svg" xmlns="http://www.w3.org/2000/svg" x="240" y="60"',
  );
  const classText = classCurrent?.name || "Keine Klasse";
  const topSkills = bestSkillSummary(skills).join(", ") || "-";
  const infoLines = [
    { label: "Name", value: characterSheet.display_name || characterSheet.slot_id || "-" },
    { label: "Klasse", value: classText },
    { label: "Top-Skills", value: topSkills },
  ];
  const infoRows = infoLines
    .map(
      (entry, index) => `
    <text class="attribute-export-copy" x="36" y="${102 + index * 76}">
      <tspan class="attribute-export-label" x="36" dy="0">${entry.label}</tspan>
      <tspan class="attribute-export-value" x="36" dy="22">${entry.value}</tspan>
    </text>
  `,
    )
    .join("");
  return `<?xml version="1.0" encoding="UTF-8"?>
    <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="Attributprofil mit Charakterinfos">
      <defs>
        <linearGradient id="attributeExportBg" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#0f1a28"></stop>
          <stop offset="100%" stop-color="#09111a"></stop>
        </linearGradient>
      </defs>
      <style>
        .attribute-export-panel{fill:rgba(255,255,255,0.04);stroke:rgba(244,194,108,0.24);stroke-width:1.2}
        .attribute-export-kicker{fill:rgba(244,238,228,0.72);font-size:11px;letter-spacing:.22em;text-transform:uppercase;font-family:"Trebuchet MS","Segoe UI",Tahoma,sans-serif}
        .attribute-export-copy{font-family:Georgia,"Times New Roman",serif}
        .attribute-export-label{fill:rgba(244,238,228,0.72);font-size:11px;letter-spacing:.12em;text-transform:uppercase}
        .attribute-export-value{fill:#f4eee4;font-size:18px}
      </style>
      <rect x="0" y="0" width="${width}" height="${height}" fill="url(#attributeExportBg)"></rect>
      <rect class="attribute-export-panel" x="24" y="24" rx="24" ry="24" width="236" height="336"></rect>
      <text class="attribute-export-kicker" x="36" y="52">Charakterprofil</text>
      ${infoRows}
      ${chartMarkup}
    </svg>`;
}

async function exportAttributeChartPng(characterSheet: CharacterSheetResponse): Promise<void> {
  let svgUrl = "";
  try {
    const svgMarkup = buildAttributeExportSvgMarkup(characterSheet);
    const svgBlob = new Blob([svgMarkup], { type: "image/svg+xml;charset=utf-8" });
    svgUrl = URL.createObjectURL(svgBlob);

    const image = await new Promise<HTMLImageElement>((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("Chart konnte nicht gerendert werden."));
      img.src = svgUrl;
    });

    const canvas = document.createElement("canvas");
    canvas.width = 900;
    canvas.height = 720;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      throw new Error("Canvas-Kontext konnte nicht erzeugt werden.");
    }
    ctx.fillStyle = "#0d1621";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);

    const pngBlob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/png"));
    if (!pngBlob) {
      throw new Error("PNG-Export fehlgeschlagen.");
    }

    const url = URL.createObjectURL(pngBlob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(characterSheet.display_name || characterSheet.slot_id || "attribute_chart").replace(/[^\w-]+/g, "_")}_werte.png`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } finally {
    if (svgUrl) {
      URL.revokeObjectURL(svgUrl);
    }
  }
}

function DetailRow({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="small">
      <strong>{label}:</strong> {displayValue(value)}
    </div>
  );
}

function readResourcePair(resources: Record<string, unknown>, key: string, currentKey: string, maxKey: string): ResourcePair {
  const nested = readRecord(resources[key]);
  return {
    current: readFiniteNumber(resources[currentKey]) ?? readFiniteNumber(nested.current) ?? 0,
    max: readFiniteNumber(resources[maxKey]) ?? readFiniteNumber(nested.max) ?? 0,
  };
}

function withCharacterTabs(active_tab: string, on_tab_change: (tab_id: string) => void, content: ReactNode): ReactNode {
  return (
    <>
      <div className="drawer-tabs character-inline-body-tabs" role="tablist" aria-label="Charakterbogen-Reiter">
        {CHARACTER_DRAWER_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={active_tab === tab.id}
            className={active_tab === tab.id ? "drawer-tab active is-active" : "drawer-tab"}
            onClick={() => on_tab_change(tab.id)}
          >
            <span>{tab.label}</span>
          </button>
        ))}
      </div>
      {content}
    </>
  );
}

export function CharacterDrawer({ sheet, active_tab, on_tab_change }: CharacterDrawerProps) {
  const [exportError, setExportError] = useState<string | null>(null);
  const overview = sheet.sheet.overview || {};
  const stats = sheet.sheet.stats || {};
  const progression = readRecord(sheet.sheet.progression);
  const appearance = readRecord(overview.appearance);
  const ageing = readRecord(overview.ageing);
  const metaInfo = readRecord(sheet.sheet.meta);
  const classInfo = sheet.sheet.class || {};
  const currentClass = classInfo.current ?? overview.class_current ?? null;
  const injuriesScars = sheet.sheet.injuries_scars || { injuries: [], scars: [] };
  const resources = readRecord(overview.resources);
  const resourceLabel = overview.resource_label || readString(progression.resource_name) || sheet.sheet.skill_meta?.resource_name || "Ressource";
  const hp = readResourcePair(resources, "hp", "hp_current", "hp_max");
  const sta = readResourcePair(resources, "stamina", "sta_current", "sta_max");
  const res = {
    current: readFiniteNumber(resources.res_current) ?? readFiniteNumber(readRecord(resources.resource).current) ?? Number(progression.resource_current || 0),
    max: readFiniteNumber(resources.res_max) ?? readFiniteNumber(readRecord(resources.resource).max) ?? Number(progression.resource_max || 0),
  };

  useEffect(() => {
    setExportError(null);
  }, [active_tab]);

  const radarScale = useMemo(() => attributeScaleMeta(stats), [stats]);
  const radarMarkup = useMemo(() => attributeRadarSvgMarkup(stats.attributes || {}, radarScale), [radarScale, stats.attributes]);

  const handleExport = async () => {
    try {
      setExportError(null);
      await exportAttributeChartPng(sheet);
    } catch (error) {
      setExportError(error instanceof Error ? error.message : "PNG-Export fehlgeschlagen.");
    }
  };

  if (active_tab === "class") {
    const ascension = readRecord(currentClass?.ascension);
    const ascensionPlotpoint = readRecord(classInfo.ascension_plotpoint);
    const requirements = readArray(ascensionPlotpoint.requirements).length
      ? joinList(readArray(ascensionPlotpoint.requirements))
      : joinList(readArray(ascension.requirements));

    return withCharacterTabs(
      active_tab,
      on_tab_change,
      <section className="drawer-panel legacy-character-sheet">
        <details className="accordion" open>
          <summary>Klasse</summary>
          <div className="accordion-body sheet-grid">
            <div className="sheet-block">
              <DetailRow label="Name" value={currentClass?.name || "Noch keine Klasse"} />
              <DetailRow label="Rang" value={currentClass?.rank || "-"} />
              <DetailRow label="Stufe" value={currentClass ? `${displayValue(currentClass.level ?? 1)}/${displayValue(currentClass.level_max ?? 10)}` : "-"} />
              <DetailRow label="XP" value={currentClass ? `${displayValue(currentClass.xp ?? 0)}/${displayValue(currentClass.xp_next ?? 100)}` : "-"} />
              <DetailRow label="Affinitäten" value={joinList(currentClass?.affinity_tags || [])} />
            </div>
            <div className="sheet-block">
              <DetailRow label="Beschreibung" value={currentClass?.description || "-"} />
              <DetailRow label="Aufstiegsstatus" value={readString(ascension.status) || "keiner"} />
              <DetailRow label="Aufstiegsquest" value={readString(ascensionPlotpoint.title) || "-"} />
              <DetailRow label="Anforderungen" value={requirements} />
              <DetailRow label="Ergebnishinweis" value={readString(ascension.result_hint) || "-"} />
            </div>
          </div>
        </details>
      </section>,
    );
  }

  if (active_tab === "attributes") {
    return withCharacterTabs(
      active_tab,
      on_tab_change,
      <section className="drawer-panel legacy-character-sheet">
        <details className="accordion" open>
          <summary>Attribute</summary>
          <div className="accordion-body attribute-radar-section">
            <div className="attribute-radar-head">
              <div className="small">
                <strong>Wertebereich:</strong> {radarScale.label}
              </div>
              <button className="btn ghost" id="exportAttributeChartBtn" type="button" onClick={() => void handleExport()}>
                Als PNG exportieren
              </button>
            </div>
            <div className="attribute-radar-wrap" dangerouslySetInnerHTML={{ __html: radarMarkup }} />
            <div className="stat-grid">
              {ATTRIBUTE_CHART_ORDER.map((key) => (
                <div key={key} className="stat-card">
                  <strong>{titleizeToken(key)}</strong>
                  <div>{stats.attributes?.[key] ?? 0}</div>
                </div>
              ))}
            </div>
            {exportError ? <div className="session-feedback error">{exportError}</div> : null}
          </div>
        </details>
      </section>,
    );
  }

  if (active_tab === "skills") {
    const skills = sheet.sheet.skills || [];
    const fusionHints = sheet.sheet.skill_meta?.fusion_hints || [];

    return withCharacterTabs(
      active_tab,
      on_tab_change,
      <section className="drawer-panel legacy-character-sheet">
        <details className="accordion" open>
          <summary>Skills</summary>
          <div className="accordion-body skill-list">
            {skills.length > 0 ? (
              skills.map((skill, index) => {
                const skillName = skill.name || titleizeToken(skill.id || "");
                const skillCost = formatSkillCost(skill.cost);
                const cappedMax = Math.max(Number(skill.next_xp || 0), 1);
                const numericCurrent = Math.max(Number(skill.xp || 0), 0);
                const width = Math.max(0, Math.min(100, Math.round((numericCurrent / cappedMax) * 100)));
                return (
                  <details key={`${skill.id || skill.name || "skill"}-${index}`} className="skill-card">
                    <summary>
                      <div className="skill-card-head">
                        <div>
                          <strong>{skillName}</strong>
                          <div className="small">
                            Stufe {displayValue(skill.level ?? 1)}/{displayValue(skill.level_max ?? 10)} • {skillTagSummary(skill) || "ohne Tags"}
                          </div>
                        </div>
                        <div className="inline-list">
                          <span className={`rank-badge ${skillRankClass(skill.rank)}`}>{skill.rank || "F"}</span>
                          {skill.cost ? <span className="mini-pill">{skillCost}</span> : null}
                        </div>
                      </div>
                    </summary>
                    <div className="accordion-body">
                      <div className="meter">
                        <div className="meter-label">
                          <span>XP</span>
                          <span>
                            {numericCurrent}/{cappedMax}
                          </span>
                        </div>
                        <div className="meter-track">
                          <div className="meter-fill" style={{ width: `${width}%` }} />
                        </div>
                      </div>
                      <div className="sheet-grid skill-meta-grid">
                        <div className="sheet-block">
                          <DetailRow label="Beherrschung" value={`${displayValue(skill.mastery ?? 0)}%`} />
                          <DetailRow label="Freigeschaltet durch" value={skill.unlocked_from || "-"} />
                          <DetailRow label="Kosten" value={skillCost} />
                          <DetailRow label="Preis" value={skill.price || "-"} />
                          <DetailRow label="Klassenpassung" value={skill.class_match ? "Klassenkonform" : "Klassenfremd"} />
                        </div>
                        <div className="sheet-block">
                          <DetailRow label="Abklingzeit" value={skill.cooldown_turns == null ? "-" : `${skill.cooldown_turns} Züge`} />
                          <DetailRow label="Synergie" value={skill.synergy_notes || "-"} />
                          <DetailRow label="Multiplikator" value={skill.effective_progress_multiplier ?? 1} />
                          <DetailRow label="Beschreibung" value={skill.description || "-"} />
                        </div>
                      </div>
                    </div>
                  </details>
                );
              })
            ) : (
              <div className="small">Noch keine gelernten Skills.</div>
            )}
            {fusionHints.length > 0 ? (
              <div className="readonly-note">
                <strong>Fusion möglich:</strong>{" "}
                {fusionHints
                  .map((entry) => `${readString(entry.label) || "Unbekannt"} (${readString(entry.result_rank) || "-"})`)
                  .join(" • ")}
              </div>
            ) : null}
          </div>
        </details>
      </section>,
    );
  }

  if (active_tab === "injuries") {
    return withCharacterTabs(
      active_tab,
      on_tab_change,
      <section className="drawer-panel legacy-character-sheet">
        <details className="accordion" open>
          <summary>Verletzungen</summary>
          <div className="accordion-body inventory-list">
            {injuriesScars.injuries.length > 0 ? (
              injuriesScars.injuries.map((injury, index) => (
                <div key={`${injury.id || injury.title || "injury"}-${index}`} className="inventory-item">
                  <strong>{injury.title || injury.id || "Verletzung"}</strong>
                  <br />
                  <span className="small">
                    {injury.severity || "-"} • {injury.healing_stage || "-"} • {injury.will_scar ? "hinterlässt Narbe" : "ohne Narbe"}
                  </span>
                  <br />
                  <span className="small">{joinList(injury.effects || []) !== "-" ? joinList(injury.effects || []) : injury.notes || "-"}</span>
                </div>
              ))
            ) : (
              <div className="small">Keine aktiven Verletzungen.</div>
            )}
          </div>
        </details>
        <details className="accordion" open>
          <summary>Narben</summary>
          <div className="accordion-body inventory-list">
            {injuriesScars.scars.length > 0 ? (
              injuriesScars.scars.map((scar, index) => (
                <div key={`${scar.id || scar.title || "scar"}-${index}`} className="inventory-item">
                  <strong>{scar.title || scar.id || "Narbe"}</strong>
                  <br />
                  <span className="small">Zug {scar.created_turn ?? 0}</span>
                  <br />
                  <span className="small">{scar.description || "-"}</span>
                </div>
              ))
            ) : (
              <div className="small">Noch keine Narben.</div>
            )}
          </div>
        </details>
      </section>,
    );
  }

  if (active_tab === "gear") {
    const equipment = Object.entries(sheet.sheet.gear_inventory?.equipment || {});
    const inventoryItems = sheet.sheet.gear_inventory?.inventory_items || [];

    return withCharacterTabs(
      active_tab,
      on_tab_change,
      <section className="drawer-panel legacy-character-sheet">
        <details className="accordion" open>
          <summary>Ausrüstung</summary>
          <div className="accordion-body equipment-grid">
            {equipment.map(([slot, item]) => (
              <div key={slot} className="equipment-slot">
                <strong>{titleizeToken(slot)}</strong>
                <br />
                <span className="small">{item.name || "Leer"}</span>
              </div>
            ))}
          </div>
        </details>
        <details className="accordion" open>
          <summary>Inventar</summary>
          <div className="accordion-body">
            <div className="small">
              Traglast {sheet.sheet.gear_inventory?.carry_weight ?? 0}/{sheet.sheet.gear_inventory?.carry_limit ?? 0} •{" "}
              {encumbranceLabel(sheet.sheet.gear_inventory?.encumbrance_state || "normal")}
            </div>
            <div className="inventory-list inventory-list-tight">
              {inventoryItems.length > 0 ? (
                inventoryItems.map((item) => (
                  <div key={item.item_id} className="inventory-item">
                    <strong>{item.name || item.item_id}</strong>
                    <br />
                    <span className="small">
                      x{item.stack} • {item.rarity || "gewöhnlich"} • Gewicht {item.weight ?? 0}
                    </span>
                  </div>
                ))
              ) : (
                <div className="small">Inventar leer.</div>
              )}
            </div>
          </div>
        </details>
      </section>,
    );
  }

  const bio = readRecord(overview.bio);
  const location = readRecord(overview.location);
  const personality = joinList(readArray(bio.personality));
  const backgroundTags = joinList(readArray(bio.background_tags));
  const appearanceScars = readArray(appearance.scars)
    .map((entry) => readString(readRecord(entry).label))
    .filter(Boolean);
  const appearanceModifiers = readArray(appearance.visual_modifiers)
    .map((entry) => readString(readRecord(entry).value))
    .filter(Boolean);
  const factions = readArray(metaInfo.faction_memberships)
    .map((entry) => readRecord(entry))
    .filter((entry) => entry.active !== false)
    .map((entry) => readString(entry.name) || readString(entry.faction_id))
    .filter(Boolean);

  return withCharacterTabs(
    active_tab,
    on_tab_change,
    <section className="drawer-panel legacy-character-sheet">
      <details className="accordion" open>
        <summary>Übersicht</summary>
        <div className="accordion-body sheet-grid">
          <div className="sheet-block">
            <DetailRow label="Name" value={bio.name} />
            <DetailRow label="Geschlecht" value={bio.gender} />
            <DetailRow label="Alter" value={`${displayValue(bio.age_years)} • ${ageStageLabel(bio.age_stage)}`} />
            <DetailRow label="Klasse" value={currentClass?.name ? `${currentClass.name} (${currentClass.rank || "F"})` : "Noch keine Klasse"} />
            <DetailRow label="Ziel" value={bio.goal} />
            <DetailRow label="Isekai-Preis" value={bio.isekai_price} />
          </div>
          <div className="sheet-block">
            <DetailRow label="Ort" value={location.scene_name} />
            <DetailRow label="Leben auf der Erde" value={bio.earth_life} />
            <DetailRow label="Persönlichkeit" value={personality} />
            <DetailRow label="Tags" value={backgroundTags} />
          </div>
        </div>
      </details>

      <details className="accordion" open>
        <summary>Aussehen</summary>
        <div className="accordion-body sheet-grid">
          <div className="sheet-block">
            <DetailRow label="Kurzbeschreibung" value={appearance.summary_short} />
            <DetailRow label="Größe" value={appearance.height} />
            <DetailRow label="Körperbau" value={buildLabel(appearance.build)} />
            <DetailRow label="Muskelgrad" value={appearance.muscle} />
            <DetailRow label="Aura" value={auraLabel(appearance.aura)} />
            <DetailRow label="Stimme" value={appearance.voice_tone} />
          </div>
          <div className="sheet-block">
            <DetailRow label="Augen" value={readString(readRecord(appearance.eyes).current) || readString(readRecord(appearance.eyes).base)} />
            <DetailRow label="Haare" value={readString(readRecord(appearance.hair).current)} />
            <DetailRow label="Hautzeichen" value={joinList(readArray(appearance.skin_marks))} />
            <DetailRow label="Narben" value={joinList(appearanceScars)} />
            <DetailRow label="Visuelle Marker" value={joinList(appearanceModifiers)} />
          </div>
        </div>
      </details>

      <details className="accordion" open>
        <summary>Altern</summary>
        <div className="accordion-body sheet-grid">
          <div className="sheet-block">
            <DetailRow label="Alter in Jahren" value={bio.age_years} />
            <DetailRow label="Altersstufe" value={ageStageLabel(bio.age_stage)} />
            <DetailRow label="Seit Ankunft" value={`${displayValue(ageing.days_since_arrival ?? 0)} Tage`} />
            <DetailRow label="Ankunft an Tag" value={ageing.arrival_absolute_day} />
          </div>
          <div className="sheet-block">
            <DetailRow label="Letzte Alterung" value={ageing.last_aged_absolute_day} />
            <DetailRow label="Alterungsmarker" value={joinList(readArray(ageing.age_effects_applied))} />
          </div>
        </div>
      </details>

      <details className="accordion" open>
        <summary>Ressourcen</summary>
        <div className="accordion-body stat-grid">
          <div className="stat-card">
            <strong>HP</strong>
            <div>
              {hp.current}/{hp.max}
            </div>
          </div>
          <div className="stat-card">
            <strong>STA</strong>
            <div>
              {sta.current}/{sta.max}
            </div>
          </div>
          <div className="stat-card">
            <strong>{resourceLabel}</strong>
            <div>
              {res.current}/{res.max}
            </div>
          </div>
          <div className="stat-card">
            <strong>Traglast</strong>
            <div>
              {sheet.sheet.gear_inventory?.carry_weight ?? 0}/{sheet.sheet.gear_inventory?.carry_limit ?? 0}
            </div>
          </div>
          <div className="stat-card">
            <strong>Verletzungen</strong>
            <div>{overview.injury_count ?? 0}</div>
          </div>
          <div className="stat-card">
            <strong>Narben</strong>
            <div>{overview.scar_count ?? 0}</div>
          </div>
        </div>
      </details>

      <details className="accordion">
        <summary>Fortschritt</summary>
        <div className="accordion-body sheet-grid">
          <div className="sheet-block">
            <DetailRow label="System-Stufe" value={progression.system_level} />
            <DetailRow label="System XP" value={progression.system_xp} />
            <DetailRow label="Ressource" value={resourceLabel} />
            <DetailRow label="Ressourcenpool" value={`${displayValue(progression.resource_current ?? 0)}/${displayValue(progression.resource_max ?? 0)}`} />
          </div>
          <div className="sheet-block">
            <DetailRow label="Klasse" value={currentClass?.name || "Noch keine Klasse"} />
            <DetailRow label="Fraktionen" value={joinList(factions)} />
            <DetailRow label="Fusion möglich" value={sheet.sheet.skill_meta?.fusion_possible ? "Ja" : "Nein"} />
          </div>
        </div>
      </details>
    </section>,
  );
}
