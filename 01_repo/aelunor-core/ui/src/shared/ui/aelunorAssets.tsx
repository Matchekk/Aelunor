import type { HTMLAttributes, ReactNode } from "react";

import "../styles/aelunor-ui-assets.css";

type PanelFrameVariant = "card" | "hero" | "modal" | "compact";
type PanelFrameElement = "section" | "article" | "div" | "aside";

interface AelunorPanelFrameProps extends HTMLAttributes<HTMLElement> {
  as?: PanelFrameElement;
  variant?: PanelFrameVariant;
  corners?: boolean;
  texture?: boolean;
  children: ReactNode;
}

const CORNER_CLASSES = ["tl", "tr", "bl", "br"] as const;

function joinClassNames(...classNames: Array<string | false | null | undefined>): string {
  return classNames.filter(Boolean).join(" ");
}

export function AelunorPanelFrame({
  as: Element = "section",
  variant = "card",
  corners = true,
  texture = false,
  className,
  children,
  ...props
}: AelunorPanelFrameProps) {
  return (
    <Element className={joinClassNames("aelunor-frame-host", `is-${variant}`, className)} {...props}>
      {texture ? <span className="aelunor-arcane-texture-layer" aria-hidden="true" /> : null}
      <span className={joinClassNames("aelunor-frame-overlay", `is-${variant}`)} aria-hidden="true" />
      {corners
        ? CORNER_CLASSES.map((corner) => (
            <span key={corner} className={joinClassNames("aelunor-corner", `aelunor-corner-${corner}`)} aria-hidden="true" />
          ))
        : null}
      <div className="aelunor-panel-content">{children}</div>
    </Element>
  );
}

interface AelunorDividerProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: "small" | "wide";
  centered?: boolean;
}

export function AelunorDivider({ variant = "wide", centered = false, className, ...props }: AelunorDividerProps) {
  return (
    <span
      className={joinClassNames("aelunor-divider", variant === "small" && "is-small", centered && "is-centered", className)}
      aria-hidden="true"
      {...props}
    />
  );
}

interface AelunorIconFrameProps extends HTMLAttributes<HTMLSpanElement> {
  label?: string;
  decorative?: boolean;
  children: ReactNode;
}

export function AelunorIconFrame({ label, decorative = false, className, children, ...props }: AelunorIconFrameProps) {
  const accessibilityProps = decorative ? { "aria-hidden": true } : { "aria-label": label };

  return (
    <span className={joinClassNames("aelunor-icon-frame", className)} role={decorative ? undefined : "img"} {...accessibilityProps} {...props}>
      <span className="aelunor-icon-frame-content">{children}</span>
    </span>
  );
}

interface AelunorSceneBackgroundProps extends HTMLAttributes<HTMLDivElement> {
  wallpaper?: "aelunor-hybrid" | "hub-reference" | "nachtblau" | "tavern" | "waldlichtung";
  texture?: boolean;
}

export function AelunorSceneBackground({ wallpaper = "hub-reference", texture = true, className, ...props }: AelunorSceneBackgroundProps) {
  return (
    <div
      className={joinClassNames("aelunor-scene-background", `is-${wallpaper}`, texture && "has-texture", className)}
      aria-hidden="true"
      {...props}
    />
  );
}
