"use client";

import { useEffect, useState } from "react";
import { getHealthHistory } from "../services/health";
import type { HealthHistory, HealthHistoryRange } from "../types/health";

export function useHealthHistory(range: HealthHistoryRange) {
  const [history, setHistory] = useState<HealthHistory | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    getHealthHistory(range)
      .then((next) => {
        if (!cancelled) {
          setHistory(next);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load health history.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [range]);

  // Derived, not effect-set: true whenever the loaded history doesn't (yet)
  // match the currently-selected range, incl. on every range switch.
  const loading = history === null || history.range !== range;

  return { history, loading, error };
}
