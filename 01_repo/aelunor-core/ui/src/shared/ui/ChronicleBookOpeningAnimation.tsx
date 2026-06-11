import type { CSSProperties } from "react";

import "../styles/aelunor-animations.css";

interface ChronicleBookOpeningAnimationProps {
  className?: string;
  /** Square edge length; numbers are treated as px. Default 192px. */
  size?: number | string;
  /** Loop the opening sequence for ongoing loading states. */
  looping?: boolean;
}

export function ChronicleBookOpeningAnimation({ className, size = 192, looping = false }: ChronicleBookOpeningAnimationProps) {
  const classes = ["chronicle-book-opening-animation", looping ? "is-looping" : null, className]
    .filter(Boolean)
    .join(" ");
  const style = {
    "--chronicle-book-size": typeof size === "number" ? `${size}px` : size,
  } as CSSProperties;

  return <span className={classes} style={style} aria-hidden="true" />;
}
