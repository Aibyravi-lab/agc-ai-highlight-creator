"use client";

import { useState, useCallback, useEffect } from "react";
import { getSubscription, upgradeToPro } from "../services/api";
import type { SubscriptionInfo } from "../types/subscription";

export function useSubscription(enabled: boolean = true) {
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null);
  const [loading, setLoading] = useState(enabled);

  const refresh = useCallback(async () => {
    if (!enabled) return;
    setLoading(true);
    try {
      setSubscription(await getSubscription());
    } catch {
      // Ignore transient refresh failures; existing subscription state is kept.
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  useEffect(() => {
    /* eslint-disable react-hooks/set-state-in-effect -- This effect owns subscription hydration and the disabled-state transition. */
    if (enabled) {
      refresh();
    } else {
      setLoading(false);
    }
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [enabled, refresh]);

  const upgrade = useCallback(async () => {
    const updated = await upgradeToPro();
    setSubscription(updated);
    return updated;
  }, []);

  return { subscription, loading, refresh, upgrade };
}
