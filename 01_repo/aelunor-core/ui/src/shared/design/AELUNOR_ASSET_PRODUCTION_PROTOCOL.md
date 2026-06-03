# Aelunor Asset Production Protocol

## Purpose

This protocol defines when new Aelunor assets may be created, how they must be named/exported, and how Codex or other agents must register, document, test, and use them. Assets are UI semantics, not just image files.

## When A New Asset Is Allowed

A new asset is allowed when it improves the story-first play experience, fills a documented UI role, cannot be expressed with existing assets or CSS, and has a clear wrapper/component path. The request must identify the asset role, layer, accessibility behavior, responsive behavior, source path, runtime mirror path, and guardrail/test requirement before production starts.

## When No New Asset May Be Created

Do not create a new asset for normal UI text, one-off decoration, admin-only polish, visual experiments without a target component, or anything that can use an existing role/component. Do not create assets to bypass layout, accessibility, or state problems. Do not add an asset pattern without updating the manifest, usage guide, and tests/checks when the pattern affects implementation rules.

## Asset Roles

| Role | Meaning |
| --- | --- |
| `background` | Page or scene wallpaper, usually via `AelunorSceneBackground`. |
| `texture` | Low-opacity non-interactive surface or scene texture. |
| `frame` | Panel, button, icon, or edge ornament that frames real content. |
| `corner` | Anchored panel corner ornament; absolute overlay only. |
| `divider` | Decorative separator with stable layout. |
| `icon` | Semantic or decorative symbolic mark. |
| `logo` | Brandmark or product identity. |
| `illustration` | Visible subject/scene content, not generic chrome. |
| `unknown` | Temporary classification only; must not be used as an implementation target. |

## Required Manifest Fields

Every new runtime asset needs:

| Field | Requirement |
| --- | --- |
| `id` / name | Lowercase kebab-case semantic id. |
| `role` | One manifest role from this protocol. |
| `intendedComponent` | Wrapper/component that owns the asset. |
| `allowedUsage` | Non-empty list of approved patterns. |
| `forbiddenUsage` | Non-empty list of blocked patterns. |
| `layer` | `background`, `texture`, `surface`, `content`, `ornament`, `floating`, `modal`, or `toast`. |
| `accessibility` | Alt/ARIA rule and whether the asset is decorative. |
| `responsiveBehavior` | Scaling/cropping/repeat constraints. |
| `path` | Frontend runtime path. |
| `mirroredPath` | Legacy/FastAPI runtime path when needed. |

Optional future fields:

| Field | Use |
| --- | --- |
| `sourceFile` | Source-of-truth file when distinct from runtime exports. |
| `exportVariants` | Format/size/runtime variants. |
| `designNotes` | Safe zone, slice edge, opacity, or alignment notes. |
| `agentInstructions` | Short implementation constraints for coding agents. |

## Naming Convention

Use lowercase kebab-case and role prefixes. Examples: `panel-corner-tl`, `panel-edge-top`, `divider-arcane-small`, `texture-arcane-noise`, `wallpaper-tavern`, `icon-frame-circle`. Do not use random names, dates, prompt fragments, file hashes, or ambiguous labels like `new-frame-final`.

## Export Rules

Prefer SVG for icons, corners, dividers, and frame ornaments when the design is vector-safe. Use WebP/AVIF/PNG for wallpapers and textures. Do not encode normal UI text into images except logos/brandmarks. Use transparent backgrounds for overlays where needed. Document safe zones, repeat seams, and slice/cut edges in `designNotes` before runtime use.

## Responsive Rules

Wallpapers may crop at page/scene level. Corners must preserve aspect ratio. Frames must not be blindly stretched across arbitrary panels. Dividers need stable dimensions to avoid layout shift. Repeating or sliced assets must document whether they use `repeat-x`, `repeat-y`, `contain`, or fixed-size overlays.

## Accessibility Rules

Decorative assets must use `aria-hidden="true"` or `alt=""`, `pointer-events: none`, and `user-select: none`. Semantic icons need an accessible name. Normal UI text must remain DOM text. Decorative layers must never block controls, links, or form fields.

## Agent Rules

Codex may classify assets, update the manifest, add wrapper support, add tests/checks, and use approved components. Codex must not use direct UI-kit paths in feature code, invent a new pattern without protocol/manifest/usage updates, use corners or edges as parent backgrounds, place wallpapers inside cards/modals/buttons/sidebars, or add arbitrary z-index numbers. Manifest, usage guide, and guardrail tests must be updated when a new asset pattern changes implementation behavior.

## Panel Edge Asset Class

`panel-edge` is a future asset subrole under manifest role `frame`. It is for panel border ornaments along the top, right, bottom, or left edge.

Expected ids:

- `panel-edge-top`
- `panel-edge-right`
- `panel-edge-bottom`
- `panel-edge-left`

Allowed usage:

- Only through `AelunorPanelFrame`.
- Absolute edge overlays.
- `aria-hidden="true"`.
- `pointer-events: none`.
- `user-select: none`.
- Horizontal edges may use `repeat-x` or `contain`.
- Vertical edges may use `repeat-y` or `contain`.

Forbidden usage:

- Parent `background-image`.
- Wallpaper.
- Content image.
- Blind full-panel stretch.
- Direct feature-code path reference.

Responsive behavior:

Edges must not visually collide with corner overlays. Horizontal and vertical edge sizing must define how corners reserve space. If repeating is used, repeat seams must be documented before merge.

## Review Checklist

- Asset request template is complete.
- Runtime files are mirrored where required.
- Manifest entry has role, allowed usage, forbidden usage, layer, accessibility, and responsive behavior.
- Usage guide and AGENTS rules are updated when a new pattern is introduced.
- Wrapper/component path exists or is explicitly scheduled before runtime use.
- Guardrail script and tests cover forbidden implementation patterns.
- Decorative assets do not block interaction and are hidden from assistive tech.
- No normal UI text is encoded in images.
- No random z-index values were added.
- No runtime data or unrelated UI behavior changed.

## Examples

Good corner asset: `panel-corner-tl.png`, role `corner`, transparent background, anchored as an absolute TL overlay inside `AelunorPanelFrame`, never as a parent background.

Good divider asset: `divider-arcane-small.png`, role `divider`, rendered by `AelunorDivider`, fixed height, `aria-hidden`, no meaningful text in the image.

Good wallpaper: `wallpaper-tavern`, role `background`, page-level scene background via `AelunorSceneBackground`, may crop responsively, not used inside cards.

Bad asset pattern: a full panel image with baked-in title text, stretched with `background-size: 100% 100%`, used directly in a feature component, and missing manifest/guardrail coverage.
