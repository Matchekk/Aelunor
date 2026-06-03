# Aelunor UI Asset Rules

- Read `aelunor.asset-manifest.json` and `AELUNOR_ASSET_USAGE.md` before adding brand/UI-kit assets.
- Use `AelunorPanelFrame`, `AelunorDivider`, `AelunorIconFrame`, or `AelunorSceneBackground` instead of direct UI-kit paths.
- Corner assets are absolute overlays only; never use `panel-corner-*.png` as a background.
- Decorative layers must be hidden from assistive tech and must not block clicks.
- Update the manifest and usage guide before introducing a new asset pattern.
