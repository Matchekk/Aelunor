# Asset Animation Pipeline (Motion Canvas)

Lightweight, agent-friendly pipeline that turns existing Aelunor assets and
sprite sheets into runtime UI animations. Animations are authored as
TypeScript code ([Motion Canvas](https://motioncanvas.io/), MIT license),
rendered headlessly to a PNG frame sequence, and packaged with
[sharp](https://sharp.pixelplumbing.com/) into transparent WebP assets.

Explicitly **not** part of this pipeline: ComfyUI, diffusion models, any model
downloads, any GUI interaction.

## Location

```
01_repo/aelunor-core/tools/animation-pipeline/   # prototype (self-contained npm package)
```

Motion Canvas is a regular npm dependency of that package — its source is not
vendored into Aelunor.

## Quick start (one command)

Requirements: Node 18+ with npm. For the Motion Canvas render step, an
installed Edge or Chrome (reused headlessly via `playwright-core` release
channels — no browser download). Without one, the build automatically falls
back to a pure-`sharp` path and still succeeds.

```powershell
cd 01_repo/aelunor-core/tools/animation-pipeline
npm install          # ~15s, no model downloads
npm run build:assets
```

`npm run build:assets` does the following:

1. **Render** (`scripts/render-headless.mjs`): starts the Vite dev server
   programmatically, loads `render.html` in a headless browser, and drives the
   Motion Canvas `Renderer` directly. Motion Canvas has no official CLI render
   mode yet ([motion-canvas#1218](https://github.com/motion-canvas/motion-canvas/issues/1218)),
   so the page in `src/render.ts` calls the renderer itself; the image-sequence
   exporter streams frames over the Vite HMR channel and the Motion Canvas
   vite plugin writes them to `./output/`. No clicking, no visible browser.
2. **Package** (`scripts/package-assets.mjs`): selects the 5 sprite frames
   from the rendered sequence (median of each 0.2s window), then uses sharp to
   produce the runtime assets and mirror them.

## Outputs

| File | What it is |
| --- | --- |
| `ui/public/brand/animations/chronicle-book-opening-animated.webp` | Animated WebP, 512x512, 5 frames @ 190ms, infinite loop, transparent, ~170 KiB |
| `ui/public/brand/animations/chronicle-book-opening-spritesheet-normalized.webp` | Normalized 2560x512 sprite sheet (5 exact 512x512 cells), transparent, ~172 KiB |
| `app/static/brand/animations/…` | Legacy mirror of both files |
| `tools/animation-pipeline/output/` | Intermediate PNG frame sequence (gitignored, not a runtime asset) |

Source asset (single source of truth, never overwritten):
`ui/public/brand/animations/chronicle-book-opening-spritesheet.webp`
(5-frame horizontal sheet, 512x512 per frame, transparent).

## Using the output in the Campaign Hub

- The **normalized sprite sheet** has the same layout as the original sheet,
  so it is a drop-in replacement for the CSS sprite animation used by
  `ChronicleBookOpeningAnimation` (`ui/src/shared/styles/aelunor-animations.css`).
- The **animated WebP** plays by itself — usable as a plain decorative
  `<img aria-hidden="true">` wherever CSS keyframes are not wanted. It loops
  infinitely (intended for ongoing loading states); for play-once semantics
  keep using the CSS sprite approach.
- Both assets are registered in
  `ui/src/shared/design/aelunor.asset-manifest.json` (role `animation`,
  intended component `ChronicleBookOpeningAnimation`).

## All commands

```powershell
cd 01_repo/aelunor-core/tools/animation-pipeline

npm run build:assets   # render + package (falls back to sharp-only if no browser)
npm run render         # headless Motion Canvas render only -> ./output/*.png
npm run package        # package ./output frames -> runtime WebP assets + mirror
npm run package -- --from-spritesheet
                       # no-browser fallback: slice the source sheet with sharp
npm run verify         # sanity-check selected frames against the source sheet
npm run dev            # open the Motion Canvas editor (authoring/preview only)

npm run preview:mp4    # MP4 review video (frames on dark backdrop; H.264 has no alpha)
npm run smooth         # frame interpolation -> smoother animation (see below)
npm run compress -- <files> [options]
                       # standalone asset compression (see below)
npm run sheet -- <animated-file> [columns]
                       # contact-sheet PNG of all frames for quick review

npm run logo           # render + package the logo reveal animation (+ MP4)
npm run animate -- --asset <png> [--preset reveal|idle|pulse|glint] [options]
                       # animate ANY asset without writing scene code (see below)
npm run watch          # keep server+browser alive; re-render on scene changes (~7s/cycle)
npm run refine -- <files> [options]    # edge refinement (see below)
npm run refine:watch   # inbox/ folder watcher: drop cutouts in, get clean PNGs out
npm run publish-asset -- <file> [--kind ...] [--as name] [--dry-run]
                       # copy finished assets into the right runtime folders (see below)
```

`ANIMATION_PIPELINE_BROWSER=<path-to-chromium-exe>` overrides browser
discovery if neither Edge nor Chrome is installed.

## How the scene works

`src/scenes/chronicleBookOpening.tsx` puts the sprite sheet `Img` inside a
clipped 512x512 `Rect` and shifts it by whole frame widths. Because no view
fill is set, the render keeps a fully transparent background. Two
renderer-specific details worth keeping for future scenes:

- **Time-driven state.** The sprite index is computed from `playback.time` on
  every render frame instead of counting `waitFor()` steps. At low fps the
  renderer's generator stepping has off-by-one drift that duplicates/skips
  frames; deriving state from time makes the output independent of stepping.
- **Oversample + median pick.** The scene renders 1s at 30fps (~31 frames);
  packaging picks the median frame of each 0.2s window, so a ±1 frame drift at
  window boundaries can never select a wrong sprite frame.

## Frame interpolation (`npm run smooth`)

Generates in-between frames so the 5-frame animation plays smoothly, keeping
the alpha channel intact and the total duration at 950ms. Two modes:

```powershell
npm run smooth -- --mode blend     # default: alpha-aware crossfade (pure sharp)
npm run smooth -- --mode motion    # real motion interpolation (ffmpeg minterpolate)
npm run smooth -- --mode motion --loop      # also interpolate last->first frame
npm run smooth -- --mode blend --multiply 8 # more in-betweens per source frame
npm run smooth -- --mode motion --runtime   # also copy result to ui/public + mirror
```

- `blend` cross-fades consecutive frames — artifact-free, but large movements
  read as motion blur (ghosting).
- `motion` interpolates color (premultiplied on black) and the alpha matte as
  two separate ffmpeg streams and recombines them per pixel, since video
  filters cannot handle transparency. True in-between motion, occasional smear
  artifacts on hand-drawn content. The final source frame is always appended
  exactly (minterpolate truncates the tail otherwise).

Output: `output/chronicle-book-opening-animated-smooth.webp` (preview artifact;
promote with `--runtime` once reviewed — pair with `npm run compress`, smooth
variants are 0.5–1 MiB at quality 90). Review with `npm run sheet`.

## Compression (`npm run compress`)

Standalone, animation-aware WebP compressor for any asset (frames, timing and
loop metadata are preserved for animated inputs):

```powershell
npm run compress -- <files...> [--quality 82] [--alpha-quality 100] [--effort 6]
                               [--lossless] [--max-width N] [--out dir] [--replace]
```

Writes `<name>.min.webp` next to the input (or to `--out`); `--replace`
overwrites a `.webp` input in place. Prints before/after sizes. Example: the
5-frame animated WebP drops from 170 KiB to 107 KiB at `--quality 70
--alpha-quality 90` with no visible loss at UI sizes.

## Preset animations (`npm run animate`)

Animates any asset inside `aelunor-core` without writing a scene — parameters
flow into `src/scenes/presetScene.tsx` as Motion Canvas project variables:

```powershell
npm run animate -- --asset ../../ui/public/brand/aelunor-icon-512x512.png --preset idle
```

Presets: `reveal` (float-in + glint + glow pulse + hover — the full intro),
`idle` (seamless hover/shimmer loop; first frame == last frame), `pulse`
(seamless glow-breathing loop), `glint` (single light sweep). Options:
`--glow '#rrggbb'`, `--asset-size N`, `--name`, `--mp4`, `--runtime`,
`--open`.

Packaging (also available standalone as `scripts/package-animation.mjs`)
dedups consecutive identical frames into longer per-frame delays and
auto-crops the canvas to the union bounding box of visible pixels
(`--no-crop` to disable, `--quality`/`--effort` to trade size vs. speed).

`npm run watch` keeps the Vite server and headless browser alive and
re-renders + repackages on every change under `src/` (fast preview encode) —
iteration cycles take ~7s instead of a cold start each time.

## Edge refinement (`npm run refine`)

Fixes the rough gray halo that manual background removal (Paint.NET magic
wand etc.) leaves around cutout edges. Built on
[PyMatting](https://github.com/pymatting/pymatting) (MIT, purely numerical —
no ML models, no downloads); evaluated alternatives were PNG-Defringe
(requires a MATLAB runtime) and alpha-bleeding tools (only fix fully
transparent pixels, not the contaminated edge itself).

One-time setup: `pip install -r requirements.txt`

```powershell
npm run refine -- <cutout.png...> [--bg white|auto|"#rrggbb"] [--band N] [--out dir] [--replace]
```

What it does: composites the cutout back onto the removed background color,
derives a trimap from the existing alpha (inside = foreground, outside =
background, ±`--band` px around the edge = unknown), then closed-form alpha
matting recovers smooth anti-aliased alpha and multilevel foreground
estimation removes the background color baked into the edge pixels. Matting
runs only on the bounding box of the edge zone, so large images with small
subjects stay fast. Output is `<name>.clean.png`.

- `--bg auto` estimates the removed background: from colors preserved under
  fully transparent pixels when available, otherwise via least squares over
  the contaminated edge ring. Explicit `white`/`#rrggbb` also works.
- The tool measures the background admixture at the edge (fringe score,
  printed before/after) and automatically retries with a wider band when the
  halo persists (`--no-retry` disables).
- `--compare` writes `<name>.compare.png`: before/after on a dark backdrop
  with an auto-selected zoom on the previously worst edge region.

`npm run refine:watch` watches the `inbox/` folder (created on first run,
gitignored): drop rough cutouts in, and each one is refined with `--bg auto
--compare` automatically. `--once` processes the current content and exits.

## Publishing assets (`npm run publish-asset`)

Moves finished assets into the right runtime folders in one step:

```powershell
npm run publish-asset -- inbox/my-art.clean.png --kind illustrations
```

Copies to `ui/public/brand/<kind>/`, mirrors to `app/static/brand/<kind>/`
(`.clean`/`.min` tool suffixes are stripped from the target name), registers
missing assets in `aelunor.asset-manifest.json` with a review-me note, and
finishes by running `scripts/check_ui_asset_usage.py`. `--kind` defaults to
`animations` for animated files and `illustrations` otherwise; `--as <name>`
renames; `--dry-run` previews the routing. Review the generated manifest
entry (`allowedUsage`, `intendedComponent`) before shipping.

## Adding a new animation

1. Add a scene under `src/scenes/` (use `chronicleBookOpening.tsx` as the
   template) and register it in `src/project.ts`.
2. Preview with `npm run dev` if desired (optional — nothing in the build
   requires the editor).
3. Extend `scripts/package-assets.mjs` with the new output names/timing.
4. Run `npm run build:assets`, then register the new files in
   `aelunor.asset-manifest.json` and run
   `python scripts/check_ui_asset_usage.py` from `aelunor-core`.

## Constraints honored

- No ComfyUI, no diffusion models, no model downloads.
- Setup is `npm install` only (~15s on a normal connection).
- One documented command builds the assets; no browser clicking.
- Output is transparent, UI-safe, and small (~170 KiB per asset).
