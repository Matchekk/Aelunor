# Aelunor Asset Request Template

Use this template before creating or importing a new Aelunor asset.

## Asset Name

`role-specific-kebab-name`

## Why Do We Need This Asset?

Describe the user-facing or story-first reason. Explain why existing assets/components are not enough.

## Role

One of: `background`, `texture`, `frame`, `corner`, `divider`, `icon`, `logo`, `illustration`, `unknown`.

## UI Context

Where the asset appears and which workflow it supports.

## Intended Component

Preferred wrapper/component, for example `AelunorPanelFrame`, `AelunorDivider`, `AelunorIconFrame`, or `AelunorSceneBackground`.

## Allowed Usage

- 

## Forbidden Usage

- 

## Layer

`background` / `texture` / `surface` / `content` / `ornament` / `floating` / `modal` / `toast`

## Accessibility

State whether the asset is decorative or semantic. Include required `alt`, `aria-hidden`, accessible name, pointer, and selection behavior.

## Responsive Behavior

Describe cropping, contain/repeat behavior, aspect ratio, safe zones, and layout-stability constraints.

## Format

SVG / PNG / WebP / AVIF / other.

## Export Sizes

- Source:
- Runtime:
- High-DPI or alternate variants:

## Source-Of-Truth Path

`03_brand/...`

## Runtime Paths

- Frontend: `ui/public/brand/...`
- Legacy/FastAPI: `app/static/brand/...`

## Acceptance Criteria

- Manifest entry is added or updated.
- Usage guide and AGENTS rules are updated if this introduces a new pattern.
- Wrapper/component path is approved.
- Decorative/accessibility behavior is verified.
- Responsive behavior is verified.
- No runtime data is touched.

## Guardrail/Test Requirement

List the static check and unit test that should fail if this asset is misused.
