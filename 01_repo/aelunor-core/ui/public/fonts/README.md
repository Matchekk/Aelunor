# Aelunor self-hosted fonts

This directory is reserved for local WOFF2 font assets used by the v1 UI.
Do not load fonts from external CDNs.

Current CSS uses font-family names with system fallbacks only, so missing files
do not create 404s or console errors. When font files are added, define
`@font-face` rules in `src/shared/styles/tokens/fonts.css` and point them to
`/v1/fonts/<family>/<file>.woff2`.

Expected families for the configured presets:

- Inter
- Spectral
- Cinzel
- EB Garamond
- Cormorant Garamond
- Atkinson Hyperlegible
- Alegreya
- Noto Sans
- Noto Serif
