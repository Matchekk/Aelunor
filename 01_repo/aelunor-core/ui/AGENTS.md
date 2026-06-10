# Aelunor UI Rules

## State Rendering Rules

- Render campaign state in the play HUD through adapters/selectors
  (`src/features/play/partyHudModel.ts`, `actorDockModel.ts`); do not reach
  deep into `campaign.state...` from components.
- Never render `undefined`, `[object Object]`, or invented values; missing
  fields get controlled fallbacks (`Unbenannte Figur`, `Unbekannte Klasse`,
  `Unbekannter Ort`, `Neutral`, `—`).
- Backend state (`CampaignSnapshot`) stays the source of truth; no parallel
  frontend truth for campaign/claim/turn/canon data.
- After UI state slices, update `AELUNOR_HANDOFF.md`; work token-efficiently
  (open only relevant files).

## Asset Rules

- Do not use files from `public/brand/ui-kit` directly unless the asset manifest or an approved wrapper component allows it.
- Use `AelunorPanelFrame` for panel frames and panel corners.
- Use `AelunorDivider` for divider assets.
- Use `AelunorIconFrame` for icon frame assets.
- Use wallpapers only as page-level scene backgrounds.
- Never use `panel-corner-*.png` as a parent `background-image`.
- Never stretch corner assets with `background-size: 100% 100%`.
- Decorative assets must use `aria-hidden`, `pointer-events: none`, and `user-select: none`.
- Framed panels must use `position: relative` and `isolation: isolate`.
- Do not add random `z-index` values. Use Aelunor z-index tokens/classes.
- Do not encode normal UI text into images.
- Do not create new asset patterns without following `src/shared/design/AELUNOR_ASSET_PRODUCTION_PROTOCOL.md` and updating the asset manifest, usage guide, and tests.
