# UI Asset Kit Notes

Last updated: 2026-04-29

## Location

The Aelunor Hub UI kit lives under:

`01_repo/aelunor-core/ui/public/brand/ui-kit/`

The cropped runtime assets used by the FastAPI-served Hub are mirrored under:

`01_repo/aelunor-core/app/static/brand/ui-kit/`

The CSS resolves those runtime files from `/static/brand/ui-kit/...`. The full sheet remains only in the UI public kit as the local crop source. Buttons, panels, inputs, links, and text remain real HTML/CSS UI.

## Assets

| Asset | Purpose | Approx. size |
| --- | --- | ---: |
| `aelunor-ui-asset-sheet.png` | Source sheet for the local UI-kit crops | ~1.62 MB |
| `frame-hero.png` | Large campaign-card frame overlay for the Hub hero | ~217 KB |
| `frame-card.png` | Reusable panel/card frame overlay | ~150 KB |
| `frame-button-primary.png` | Primary button ornament overlay | ~31 KB |
| `frame-button-secondary.png` | Secondary button ornament overlay | ~24 KB |
| `divider-arcane-wide.png` | Wide section divider | ~54 KB |
| `divider-arcane-small.png` | Compact section divider | ~27 KB |
| `icon-frame-circle.png` | Active sidebar/icon HUD frame | ~86 KB |
| `panel-corner-*.png` | Corner ornaments for future panel variants | ~45 KB each |
| `texture-arcane-noise.webp` | Subtle non-transparent arcane texture | ~12 KB |

## Usage

The central CSS utilities are defined in:

`01_repo/aelunor-core/ui/src/shared/styles/aelunor-ui-assets.css`

Current Hub usage:

- `HubHero` uses `frame-hero`, `texture-arcane-noise`, compact divider, and ornate buttons.
- `HubContinuationPanel`, `CreateCampaignCard`, `JoinCampaignCard`, `SessionLibraryPanel`, `HubFeatureCards`, and `HubContextRail` use card frame overlays and section dividers.
- The Sidebar active icon state uses `icon-frame-circle`.
- Empty states use `divider-arcane-small`.

## Rules For Future Assets

- Keep decorative overlays transparent PNGs and small.
- Use WebP only for non-transparent textures.
- Do not turn dynamic UI into fixed image panels.
- Keep sidebar or small HUD icons at 256px or 512px maximum.
- Avoid duplicating these UI-kit assets into `app/static` unless the legacy static UI needs them.
- The current FastAPI Hub shell needs small runtime copies in `app/static/brand/ui-kit`; do not copy the full source sheet there.
- Decorative layers must keep `pointer-events: none` so they cannot block inputs, buttons, or links.
