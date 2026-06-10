import { useCallback, useEffect, useRef, useState } from "react";
import type { KeyboardEvent as ReactKeyboardEvent, PointerEvent as ReactPointerEvent, RefObject } from "react";

export const COMPOSER_HEIGHT_STORAGE_KEY = "aelunor.play.composerHeight.v1";
export const COMPOSER_MIN_HEIGHT = 220;
export const COMPOSER_DEFAULT_HEIGHT = 260;
export const COMPOSER_MAX_RATIO = 0.44;
export const JOURNAL_MIN_HEIGHT = 260;
export const RESIZE_HANDLE_HEIGHT = 12;
export const RESIZE_STEP = 16;
export const RESIZE_STEP_LARGE = 64;

export function deriveMaxComposerHeight(available_height: number): number {
  if (!Number.isFinite(available_height) || available_height <= 0) {
    return COMPOSER_DEFAULT_HEIGHT;
  }
  const by_ratio = available_height * COMPOSER_MAX_RATIO;
  const by_journal = available_height - JOURNAL_MIN_HEIGHT - RESIZE_HANDLE_HEIGHT;
  return Math.max(COMPOSER_MIN_HEIGHT, Math.min(by_ratio, by_journal));
}

export function clampComposerHeight(value: unknown, available_height: number): number {
  const numeric = typeof value === "number" ? value : Number.parseFloat(String(value ?? ""));
  const base = Number.isFinite(numeric) ? numeric : COMPOSER_DEFAULT_HEIGHT;
  return Math.round(Math.min(Math.max(base, COMPOSER_MIN_HEIGHT), deriveMaxComposerHeight(available_height)));
}

export function readStoredComposerHeight(storage: Pick<Storage, "getItem"> | null): number | null {
  try {
    const raw = storage?.getItem(COMPOSER_HEIGHT_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const numeric = Number.parseFloat(raw);
    return Number.isFinite(numeric) ? numeric : null;
  } catch {
    return null;
  }
}

export function writeStoredComposerHeight(storage: Pick<Storage, "setItem"> | null, height: number): void {
  try {
    storage?.setItem(COMPOSER_HEIGHT_STORAGE_KEY, String(Math.round(height)));
  } catch {
    // Persistence is best-effort; a blocked storage must never break resizing.
  }
}

function safeLocalStorage(): Storage | null {
  try {
    return typeof window !== "undefined" ? window.localStorage : null;
  } catch {
    return null;
  }
}

export interface ResizableComposerHandleProps {
  role: "separator";
  tabIndex: number;
  "aria-orientation": "horizontal";
  "aria-label": string;
  "aria-valuemin": number;
  "aria-valuemax": number;
  "aria-valuenow": number;
  onPointerDown: (event: ReactPointerEvent<HTMLElement>) => void;
  onKeyDown: (event: ReactKeyboardEvent<HTMLElement>) => void;
  onDoubleClick: () => void;
}

export function useResizableComposerHeight(container_ref: RefObject<HTMLElement | null>): {
  composer_height: number;
  handle_props: ResizableComposerHandleProps;
} {
  const [height, setHeight] = useState(() =>
    clampComposerHeight(
      readStoredComposerHeight(safeLocalStorage()) ?? COMPOSER_DEFAULT_HEIGHT,
      typeof window !== "undefined" ? window.innerHeight : COMPOSER_DEFAULT_HEIGHT * 3,
    ),
  );
  const heightRef = useRef(height);
  heightRef.current = height;

  const availableHeight = useCallback(() => {
    const fromContainer = container_ref.current?.clientHeight ?? 0;
    if (fromContainer > 0) {
      return fromContainer;
    }
    return typeof window !== "undefined" ? window.innerHeight : COMPOSER_DEFAULT_HEIGHT * 3;
  }, [container_ref]);

  const applyHeight = useCallback(
    (next: number) => {
      const clamped = clampComposerHeight(next, availableHeight());
      heightRef.current = clamped;
      setHeight(clamped);
      return clamped;
    },
    [availableHeight],
  );

  const persistCurrent = useCallback(() => {
    writeStoredComposerHeight(safeLocalStorage(), heightRef.current);
  }, []);

  // The initial state can only clamp against the viewport; once the center
  // column is measurable, re-clamp so stored legacy heights respect the
  // current max rules (e.g. old 55%-era values shrink to the 44% cap).
  useEffect(() => {
    const clamped = applyHeight(heightRef.current);
    if (clamped !== readStoredComposerHeight(safeLocalStorage())) {
      writeStoredComposerHeight(safeLocalStorage(), clamped);
    }
  }, [applyHeight]);

  const onPointerDown = useCallback(
    (event: ReactPointerEvent<HTMLElement>) => {
      if (event.button !== 0) {
        return;
      }
      event.preventDefault();
      const startY = event.clientY;
      const startHeight = heightRef.current;
      document.body.classList.add("is-resizing-composer");
      const onMove = (move: PointerEvent) => {
        applyHeight(startHeight + (startY - move.clientY));
      };
      const onUp = () => {
        window.removeEventListener("pointermove", onMove);
        document.body.classList.remove("is-resizing-composer");
        persistCurrent();
      };
      window.addEventListener("pointermove", onMove);
      window.addEventListener("pointerup", onUp, { once: true });
    },
    [applyHeight, persistCurrent],
  );

  const onKeyDown = useCallback(
    (event: ReactKeyboardEvent<HTMLElement>) => {
      const step = event.shiftKey ? RESIZE_STEP_LARGE : RESIZE_STEP;
      if (event.key === "ArrowUp") {
        event.preventDefault();
        applyHeight(heightRef.current + step);
        persistCurrent();
      } else if (event.key === "ArrowDown") {
        event.preventDefault();
        applyHeight(heightRef.current - step);
        persistCurrent();
      } else if (event.key === "Enter") {
        event.preventDefault();
        applyHeight(COMPOSER_DEFAULT_HEIGHT);
        persistCurrent();
      }
    },
    [applyHeight, persistCurrent],
  );

  const onDoubleClick = useCallback(() => {
    applyHeight(COMPOSER_DEFAULT_HEIGHT);
    persistCurrent();
  }, [applyHeight, persistCurrent]);

  return {
    composer_height: height,
    handle_props: {
      role: "separator",
      tabIndex: 0,
      "aria-orientation": "horizontal",
      "aria-label": "Beitragsbereich Größe ändern",
      "aria-valuemin": COMPOSER_MIN_HEIGHT,
      "aria-valuemax": Math.round(deriveMaxComposerHeight(availableHeight())),
      "aria-valuenow": height,
      onPointerDown,
      onKeyDown,
      onDoubleClick,
    },
  };
}
