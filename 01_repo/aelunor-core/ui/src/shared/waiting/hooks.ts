import { useEffect, useMemo, useState } from "react";

import { pickPrimaryWaiting } from "./escalation";
import { useWaitingStore } from "./store";
import type { WaitingPresentation, WaitingScope, WaitingSignalInput, WaitingSurfaceTarget } from "./model";

interface WaitingSignalHookOptions extends WaitingSignalInput {
  active: boolean;
}

interface WaitingTargetOptions {
  min_scope: WaitingScope;
  max_scope?: WaitingScope;
}

export function useWaitingSignal({
  key,
  active,
  context,
  scope,
  blocking_level,
  surface_target,
  message_override = null,
  detail_override = null,
}: WaitingSignalHookOptions): void {
  const upsertSignal = useWaitingStore((state) => state.upsert_signal);
  const clearSignal = useWaitingStore((state) => state.clear_signal);

  useEffect(() => {
    if (active) {
      upsertSignal({
        key,
        context,
        scope,
        blocking_level,
        surface_target,
        message_override,
        detail_override,
      });
      return () => {
        clearSignal(key);
      };
    }

    clearSignal(key);
    return undefined;
  }, [
    active,
    blocking_level,
    clearSignal,
    context,
    detail_override,
    key,
    message_override,
    scope,
    surface_target,
    upsertSignal,
  ]);
}

export function useWaitingForTarget(
  target: WaitingSurfaceTarget,
  { min_scope, max_scope }: WaitingTargetOptions,
): WaitingPresentation | null {
  const signals = useWaitingStore((state) => state.signals.filter((entry) => entry.surface_target === target));
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (signals.length === 0) {
      return undefined;
    }
    const timer = window.setInterval(() => {
      setNow(Date.now());
    }, 500);
    return () => {
      window.clearInterval(timer);
    };
  }, [signals.length]);

  return useMemo(
    () => pickPrimaryWaiting(signals, now, min_scope, max_scope ?? null),
    [max_scope, min_scope, now, signals],
  );
}
