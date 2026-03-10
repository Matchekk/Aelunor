import type { CharacterSheetResponse } from "../../../shared/api/contracts";

interface CharacterDrawerProps {
  sheet: CharacterSheetResponse;
  active_tab: string;
}

function readNumber(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value) ? String(value) : "-";
}

export function CharacterDrawer({ sheet, active_tab }: CharacterDrawerProps) {
  const overview = sheet.sheet.overview;
  const resources = overview.resources;
  const stats = sheet.sheet.stats;
  const gear = sheet.sheet.gear_inventory;
  const injuries = sheet.sheet.injuries_scars;

  if (active_tab === "class") {
    return (
      <section className="drawer-panel">
        <div className="drawer-grid">
          <article className="drawer-card">
            <strong>{sheet.sheet.class.current?.name || "No class unlocked"}</strong>
            <p>
              Rank {sheet.sheet.class.current?.rank || "?"} • Level {readNumber(sheet.sheet.class.current?.level)} /
              {readNumber(sheet.sheet.class.current?.level_max)}
            </p>
            <p>{sheet.sheet.class.current?.description || "No class description available."}</p>
          </article>
        </div>
      </section>
    );
  }

  if (active_tab === "attributes") {
    return (
      <section className="drawer-panel">
        <div className="drawer-grid">
          <article className="drawer-card">
            <strong>Attributes</strong>
            <dl className="meta-list">
              {Object.entries(stats.attributes ?? {}).map(([key, value]) => (
                <div key={key}>
                  <dt>{key}</dt>
                  <dd>{readNumber(value)}</dd>
                </div>
              ))}
            </dl>
          </article>
          <article className="drawer-card">
            <strong>Derived</strong>
            <dl className="meta-list">
              {Object.entries(stats.modifier_summary ?? {}).map(([key, value]) => (
                <div key={key}>
                  <dt>{key}</dt>
                  <dd>{readNumber(value)}</dd>
                </div>
              ))}
            </dl>
          </article>
        </div>
      </section>
    );
  }

  if (active_tab === "skills") {
    return (
      <section className="drawer-panel drawer-list">
        {sheet.sheet.skills.length > 0 ? (
          sheet.sheet.skills.map((skill) => (
            <article key={skill.id || skill.name} className="drawer-card">
              <strong>{skill.name || skill.id || "Unknown skill"}</strong>
              <p>
                Rank {skill.rank || "?"} • Level {readNumber(skill.level)} / {readNumber(skill.level_max)}
              </p>
              <p>{skill.description || skill.synergy_notes || "No extra skill notes."}</p>
            </article>
          ))
        ) : (
          <div className="setup-empty-state">No learned skills yet.</div>
        )}
      </section>
    );
  }

  if (active_tab === "injuries") {
    return (
      <section className="drawer-panel drawer-grid">
        <article className="drawer-card">
          <strong>Injuries</strong>
          {(injuries.injuries ?? []).length > 0 ? (
            <ul className="rail-list">
              {injuries.injuries.map((entry, index) => (
                <li key={`${entry.id || entry.title || "injury"}-${index}`} className="rail-list-item">
                  <strong>{entry.title || entry.id || "Injury"}</strong>
                  <span className="status-muted">{entry.severity || "Unknown severity"}</span>
                  <span className="status-muted">{entry.description || entry.notes || "-"}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="status-muted">No active injuries.</p>
          )}
        </article>
        <article className="drawer-card">
          <strong>Scars</strong>
          {(injuries.scars ?? []).length > 0 ? (
            <ul className="rail-list">
              {injuries.scars.map((entry, index) => (
                <li key={`${entry.id || entry.title || "scar"}-${index}`} className="rail-list-item">
                  <strong>{entry.title || entry.id || "Scar"}</strong>
                  <span className="status-muted">{entry.description || "-"}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="status-muted">No scars yet.</p>
          )}
        </article>
      </section>
    );
  }

  if (active_tab === "gear") {
    return (
      <section className="drawer-panel drawer-grid">
        <article className="drawer-card">
          <strong>Equipment</strong>
          <ul className="rail-list">
            {Object.entries(gear.equipment ?? {}).map(([slot, item]) => (
              <li key={slot} className="rail-list-item">
                <strong>{slot}</strong>
                <span className="status-muted">{item.name || "Empty"}</span>
              </li>
            ))}
          </ul>
        </article>
        <article className="drawer-card">
          <strong>Inventory</strong>
          {(gear.inventory_items ?? []).length > 0 ? (
            <ul className="rail-list">
              {gear.inventory_items.map((item) => (
                <li key={item.item_id} className="rail-list-item">
                  <strong>{item.name}</strong>
                  <span className="status-muted">
                    x{item.stack} • {item.rarity || "common"} • weight {readNumber(item.weight)}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="status-muted">Inventory is empty.</p>
          )}
        </article>
      </section>
    );
  }

  return (
    <section className="drawer-panel drawer-grid">
      <article className="drawer-card">
        <strong>{sheet.display_name}</strong>
        <p>{sheet.scene_name || sheet.scene_id || "Unknown scene"}</p>
        <p>{sheet.sheet.class.current?.name || "No active class"}</p>
      </article>
      <article className="drawer-card">
        <strong>Resources</strong>
        <dl className="meta-list">
          <div>
            <dt>HP</dt>
            <dd>
              {readNumber(resources?.hp_current)} / {readNumber(resources?.hp_max)}
            </dd>
          </div>
          <div>
            <dt>STA</dt>
            <dd>
              {readNumber(resources?.sta_current)} / {readNumber(resources?.sta_max)}
            </dd>
          </div>
          <div>
            <dt>{resources?.resource_name || "RES"}</dt>
            <dd>
              {readNumber(resources?.res_current)} / {readNumber(resources?.res_max)}
            </dd>
          </div>
        </dl>
      </article>
    </section>
  );
}
