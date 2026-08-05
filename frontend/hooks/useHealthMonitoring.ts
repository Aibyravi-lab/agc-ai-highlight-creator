"use client";

import { useEffect, useState } from "react";
import { getHealthSummary } from "../services/health";
import type { HealthSummary } from "../types/health";

const POLL_INTERVAL_MS = 15000;

export function useHealthMonitoring() {
  const [summary, setSummary] = useState<HealthSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const next = await getHealthSummary();
        if (!cancelled) {
          setSummary(next);
          setError(null);
          setLastUpdatedAt(Date.now());
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load health data.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    const intervalId = setInterval(load, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(intervalId);
    };
  }, []);

  return { summary, loading, error, lastUpdatedAt };
}
