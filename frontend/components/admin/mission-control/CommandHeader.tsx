"use client";

import { useEffect, useState } from "react";
import type { ProductionHealth } from "../../../types/missionControl";
import { StatusBadge } from "./primitives";

function useSecondsAgo(lastUpdatedAt: number | null): number | null {
  const [secondsAgo, setSecondsAgo] = useState<number | null>(null);

  useEffect(() => {
    if (lastUpdatedAt === null) return;

    const intervalId = setInterval(() => {
      setSecondsAgo(Math.max(0, Math.round((Date.now() - lastUpdatedAt) / 1000)));
    }, 1000);

    return () => clearInterval(intervalId);
  }, [lastUpdatedAt]);

  return secondsAgo;
}

export function CommandHeader({
  health,
  lastUpdatedAt,
}: {
  health: ProductionHealth;
  lastUpdatedAt: number | null;
}) {
  const secondsAgo = useSecondsAgo(lastUpdatedAt);
  const isHealthy = health.status === "ok";

  return (
    <div className="pb-4 border-b border-[#1a1d2e]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold text-green-400 tracking-[0.2em] uppercase">
            Vedzovi
          </p>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight mt-0.5">
            Founder Command Center
          </h1>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-green-500/30 bg-green-500/10 px-2.5 py-1 text-xs font-medium text-green-400">
            <span className="relative flex w-2 h-2">
              <span className="motion-safe:animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex rounded-full w-2 h-2 bg-green-400" />
            </span>
            LIVE
          </span>
          <StatusBadge
            tone={isHealthy ? "green" : "red"}
            label={isHealthy ? "PRODUCTION HEALTHY" : "PRODUCTION DEGRADED"}
          />
          {health.maintenance_mode && (
            <StatusBadge tone="amber" label="MAINTENANCE ON" />
          )}
        </div>
      </div>

      <p className="text-xs text-gray-600 mt-3">
        {secondsAgo === null ? "Syncing…" : `Updated ${secondsAgo}s ago`} · {health.environment}
      </p>
    </div>
  );
}
