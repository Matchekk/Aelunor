# Aelunor Asset Usage

Assets are UI semantics, not just images. Before using a file from `public/brand`, check `aelunor.asset-manifest.json` for its role, allowed usage, forbidden usage, intended component, layer, and accessibility rule.

For new assets or new asset patterns, start with `AELUNOR_ASSET_PRODUCTION_PROTOCOL.md` and fill out `AELUNOR_ASSET_REQUEST_TEMPLATE.md` before adding runtime files.

## Source Of Truth

| Path | Meaning |
| --- | --- |
| `03_brand` | Brand and design source. |
| `ui/public/brand` | React/Vite frontend runtime assets. |
| `app/static/brand` | Legacy/FastAPI runtime assets. |
| `ui/public/icons` | React/Vite semantic navigation icon runtime assets. |
| `app/static/icons` | Legacy/FastAPI mirror for semantic navigation icons. |

## Roles

| Role | Do | Don't |
| --- | --- | --- |
| `background` | Use page-level via `AelunorSceneBackground`. | Do not put wallpapers inside cards, buttons, modals, or sidebars. |
| `texture` | Use as low-opacity decorative layer. | Do not expose as foreground content or clickable layer. |
| `frame` | Use via `AelunorPanelFrame`, approved button classes, or `AelunorIconFrame`. | Do not blindly stretch panel frames with `background-size: 100% 100%` except documented button-frame fallback. |
| `corner` | Use four absolute corner overlays in `AelunorPanelFrame`. | Never use `panel-corner-*.png` as a parent `background-image`. |
| `divider` | Use `AelunorDivider` for visual separation. | Do not render as meaningful content images or with filename alt text. |
| `icon` | Keep semantic icon meaning separate from decorative frames. | Do not encode normal UI labels as images. |
| `logo` | Use real alt text for brand identity, empty alt for decorative marks. | Do not use a logo as generic ornament or UI text replacement. |
| `illustration` | Use only when it is the visible subject or scene content. | Do not use as random texture or control chrome. |

## Layering

Use Aelunor layer tokens instead of random z-index values:

| Token | Meaning |
| --- | --- |
| `--ael-z-background` | Page or scene background. |
| `--ael-z-texture` | Low-opacity texture layer. |
| `--ael-z-surface` | Frame/surface ornament below content. |
| `--ael-z-content` | Real UI content and controls. |
| `--ael-z-ornament` | Corners and decorative overlays above surface. |
| `--ael-z-floating` | Popovers and floating controls. |
| `--ael-z-modal` | Modal backdrops/dialogs. |
| `--ael-z-toast` | Toasts and top notifications. |

Framed panels must use `position: relative` and `isolation: isolate`. Content sits above surface/texture layers. Corner and frame ornaments sit above the surface, do not block interaction, and do not create their own semantic content.

## Accessibility

Decorative assets must use `aria-hidden="true"` or `alt=""`, `pointer-events: none`, and `user-select: none`. Do not encode normal UI text into images. If an icon carries meaning, provide an accessible name on the semantic icon or wrapper; the frame remains decorative.

## HubSidebar Icons

The Campaign Hub sidebar icons live as individual semantic PNG files in `ui/public/icons` and are mirrored under `app/static/icons`. They are registered as `ui-kit` assets with role `icon`, intended component `HubSidebar`, and layer `content`.

Use them only as HubSidebar navigation icons. The sidebar button must keep real text or an accessible name, so the image itself may use `alt=""`. Do not use filenames as alt text, do not use these icons as text replacement, and do not use them as decorative panel frames, button backgrounds, page backgrounds, or standalone brand logos.

`icon-frame-circle.png` remains a separate decorative frame asset. Keep the semantic sidebar icon and the decorative frame separate.

`characters_icon_png.png` is registered at its current runtime path to avoid breaking `/v1/icons/...`; rename candidate: `characters_icon_sidebar.png`.

## Empty-State Illustrations

`empty-chronicle-seal.webp` is a transparent decorative illustration for the Campaign Hub empty state. It lives under `ui/public/brand/illustrations` and is mirrored under `app/static/brand/illustrations`.

Use it only where real surrounding text explains that no chronicle exists yet. Render it with `alt=""` and `aria-hidden="true"`. Do not use it as a navigation icon, frame, button background, page background, text replacement, or brand logo.

## Responsive Rules

Wallpapers cover page or scene viewports and may crop. Frames and dividers use stable dimensions to avoid layout shift. Corners preserve aspect ratio and clamp size against the panel. Text remains real DOM text and must not be hidden inside image assets.

## Correct Examples

```tsx
<AelunorPanelFrame className="v1-panel session-card" variant="card">
  <h2>Kampagne erstellen</h2>
  <AelunorDivider variant="small" />
  <p>Real content stays above the decorative layers.</p>
</AelunorPanelFrame>
```

```tsx
<AelunorIconFrame label="Campaign">
  <CampaignIcon />
</AelunorIconFrame>
```

```tsx
<AelunorSceneBackground wallpaper="tavern" />
```

## Forbidden Examples

```css
.panel {
  background-image: url("/brand/ui-kit/panel-corner-tl.png");
  background-size: 100% 100%;
}
```

```tsx
<img src="/brand/ui-kit/divider-arcane-wide.png" alt="divider-arcane-wide.png" />
```

```css
.card {
  background-image: url("/brand/wallpapers/tavern.png");
}
```

## Check Script

Run this from `01_repo/aelunor-core`:

```powershell
python scripts/check_ui_asset_usage.py
```

The script scans source files, skips build/runtime folders, validates manifest paths/roles, and reports forbidden corner backgrounds, frame stretching, wallpaper-in-card patterns, direct UI-kit references outside approved wrappers, decorative UI-kit images without accessibility markers, and high numeric z-index values in `ui/src`.
