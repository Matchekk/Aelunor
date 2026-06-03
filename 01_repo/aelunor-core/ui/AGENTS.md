# Aelunor UI Asset Rules

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
